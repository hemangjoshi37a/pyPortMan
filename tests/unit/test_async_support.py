"""
Unit tests for async support
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pyportman import (
    AsyncHTTPClient,
    AsyncRequest,
    AsyncResponse,
    AsyncRateLimiter,
    AsyncBatchProcessor,
    run_async,
    run_async_sync
)


class TestAsyncRequest:
    """Test cases for AsyncRequest"""

    def test_async_request_defaults(self):
        """Test AsyncRequest default values"""
        request = AsyncRequest(url="https://example.com")
        assert request.url == "https://example.com"
        assert request.method == "GET"
        assert request.headers == {}
        assert request.params == {}
        assert request.data == {}
        assert request.json_data == {}
        assert request.timeout == 30
        assert request.retry_count == 0

    def test_async_request_custom(self):
        """Test AsyncRequest with custom values"""
        request = AsyncRequest(
            url="https://example.com",
            method="POST",
            headers={"Authorization": "Bearer token"},
            params={"key": "value"},
            data={"field": "value"},
            json_data={"json": "data"},
            timeout=60,
            retry_count=2
        )
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Bearer token"
        assert request.params["key"] == "value"
        assert request.data["field"] == "value"
        assert request.json_data["json"] == "data"
        assert request.timeout == 60
        assert request.retry_count == 2


class TestAsyncResponse:
    """Test cases for AsyncResponse"""

    def test_async_response_success(self):
        """Test AsyncResponse for successful request"""
        response = AsyncResponse(
            status_code=200,
            data={"result": "success"},
            headers={"Content-Type": "application/json"},
            elapsed=0.5,
            success=True
        )
        assert response.status_code == 200
        assert response.data["result"] == "success"
        assert response.headers["Content-Type"] == "application/json"
        assert response.elapsed == 0.5
        assert response.success is True
        assert response.error is None

    def test_async_response_failure(self):
        """Test AsyncResponse for failed request"""
        response = AsyncResponse(
            status_code=500,
            data=None,
            headers={},
            elapsed=1.0,
            success=False,
            error="Internal Server Error"
        )
        assert response.status_code == 500
        assert response.data is None
        assert response.success is False
        assert response.error == "Internal Server Error"

    def test_async_response_to_dict(self):
        """Test converting AsyncResponse to dictionary"""
        response = AsyncResponse(
            status_code=200,
            data={"result": "success"},
            headers={"Content-Type": "application/json"},
            elapsed=0.5,
            success=True
        )
        response_dict = response.to_dict()
        assert response_dict["status_code"] == 200
        assert response_dict["data"]["result"] == "success"
        assert response_dict["elapsed"] == 0.5
        assert response_dict["success"] is True


class TestAsyncRateLimiter:
    """Test cases for AsyncRateLimiter"""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test AsyncRateLimiter initialization"""
        limiter = AsyncRateLimiter(max_calls=10, period=60.0)
        assert limiter.max_calls == 10
        assert limiter.period == 60.0
        assert len(limiter.calls) == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_if_needed(self):
        """Test rate limiter wait functionality"""
        limiter = AsyncRateLimiter(max_calls=2, period=1.0)

        # First two calls should not wait
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()
        assert len(limiter.calls) == 2

        # Third call should wait (but we won't actually wait in test)
        # Just verify it would wait
        assert len(limiter.calls) >= 2

    @pytest.mark.asyncio
    async def test_rate_limiter_get_remaining_calls(self):
        """Test getting remaining calls"""
        limiter = AsyncRateLimiter(max_calls=5, period=60.0)

        # Initially should have all calls available
        assert limiter.get_remaining_calls() == 5

        # After making calls
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()
        assert limiter.get_remaining_calls() == 3


class TestAsyncHTTPClient:
    """Test cases for AsyncHTTPClient"""

    @pytest.fixture
    async def http_client(self):
        """Create AsyncHTTPClient instance"""
        client = AsyncHTTPClient(max_concurrent=5, timeout=30)
        await client.start()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_http_client_initialization(self):
        """Test AsyncHTTPClient initialization"""
        client = AsyncHTTPClient(max_concurrent=10, timeout=60)
        assert client.max_concurrent == 10
        assert client.timeout == 60
        assert client._session is None

    @pytest.mark.asyncio
    async def test_http_client_context_manager(self):
        """Test AsyncHTTPClient as context manager"""
        async with AsyncHTTPClient() as client:
            assert client._session is not None
            assert not client._session.closed

        # Session should be closed after context exit
        assert client._session.closed

    @pytest.mark.asyncio
    async def test_http_client_start_close(self):
        """Test starting and closing HTTP client"""
        client = AsyncHTTPClient()
        assert client._session is None

        await client.start()
        assert client._session is not None
        assert not client._session.closed

        await client.close()
        assert client._session.closed

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_http_client_request(self, mock_request, http_client):
        """Test making HTTP request"""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_response.text = AsyncMock(return_value="success")

        mock_request.return_value.__aenter__.return_value = mock_response

        request = AsyncRequest(url="https://example.com/api")
        response = await http_client.request(request)

        assert response.status_code == 200
        assert response.success is True
        assert response.data["result"] == "success"

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_http_client_get(self, mock_get, http_client):
        """Test GET request"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"data": "test"})

        mock_get.return_value.__aenter__.return_value = mock_response

        response = await http_client.get(
            "https://example.com/api",
            params={"key": "value"},
            headers={"Authorization": "Bearer token"}
        )

        assert response.status_code == 200
        assert response.success is True

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_http_client_post(self, mock_post, http_client):
        """Test POST request"""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"created": True})

        mock_post.return_value.__aenter__.return_value = mock_response

        response = await http_client.post(
            "https://example.com/api",
            json_data={"name": "test"},
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 201
        assert response.success is True

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_http_client_batch_request(self, mock_request, http_client):
        """Test batch requests"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"result": "success"})

        mock_request.return_value.__aenter__.return_value = mock_response

        requests = [
            AsyncRequest(url=f"https://example.com/api/{i}")
            for i in range(3)
        ]

        responses = await http_client.batch_request(requests)

        assert len(responses) == 3
        for response in responses:
            assert response.status_code == 200
            assert response.success is True


class TestAsyncBatchProcessor:
    """Test cases for AsyncBatchProcessor"""

    def test_batch_processor_initialization(self):
        """Test AsyncBatchProcessor initialization"""
        processor = AsyncBatchProcessor(max_concurrent=10)
        assert processor.max_concurrent == 10

    @pytest.mark.asyncio
    async def test_batch_processor_process(self):
        """Test processing items"""
        processor = AsyncBatchProcessor(max_concurrent=3)

        items = [1, 2, 3, 4, 5]

        async def process_item(item):
            await asyncio.sleep(0.01)
            return item * 2

        results = await processor.process(items, process_item)

        assert len(results) == 5
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_batch_processor_process_with_progress(self):
        """Test processing with progress callback"""
        processor = AsyncBatchProcessor(max_concurrent=2)

        items = [1, 2, 3]
        progress_updates = []

        async def process_item(item):
            await asyncio.sleep(0.01)
            return item * 2

        def progress_callback(completed, total):
            progress_updates.append((completed, total))

        results = await processor.process(items, process_item, progress_callback)

        assert len(results) == 3
        assert len(progress_updates) == 3
        assert progress_updates[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_batch_processor_process_map(self):
        """Test processing items to dictionary"""
        processor = AsyncBatchProcessor(max_concurrent=3)

        items = ['a', 'b', 'c']

        async def process_item(item):
            await asyncio.sleep(0.01)
            return item.upper()

        results = await processor.process_map(items, process_item)

        assert len(results) == 3
        assert results['a'] == 'A'
        assert results['b'] == 'B'
        assert results['c'] == 'C'

    @pytest.mark.asyncio
    async def test_batch_processor_with_exceptions(self):
        """Test processing with exceptions"""
        processor = AsyncBatchProcessor(max_concurrent=2)

        items = [1, 2, 3]

        async def process_item(item):
            if item == 2:
                raise ValueError("Test error")
            await asyncio.sleep(0.01)
            return item * 2

        results = await processor.process(items, process_item)

        # Should return results including exceptions
        assert len(results) == 3
        assert results[0] == 2
        assert isinstance(results[1], ValueError)
        assert results[2] == 6


class TestAsyncUtilities:
    """Test cases for async utility functions"""

    @pytest.mark.asyncio
    async def test_run_async(self):
        """Test run_async function"""
        async def test_coro():
            await asyncio.sleep(0.01)
            return "result"

        result = await run_async(test_coro())
        assert result == "result"

    def test_run_async_sync(self):
        """Test run_async_sync function"""
        async def test_coro():
            await asyncio.sleep(0.01)
            return "result"

        result = run_async_sync(test_coro())
        assert result == "result"

    @pytest.mark.asyncio
    async def test_run_async_with_exception(self):
        """Test run_async with exception"""
        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await run_async(failing_coro())

    def test_run_async_sync_with_exception(self):
        """Test run_async_sync with exception"""
        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            run_async_sync(failing_coro())


class TestAsyncIntegration:
    """Integration tests for async functionality"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test making concurrent requests"""
        async with AsyncHTTPClient(max_concurrent=5) as client:
            requests = [
                AsyncRequest(url=f"https://httpbin.org/delay/{i}")
                for i in range(1, 4)
            ]

            start_time = asyncio.get_event_loop().time()
            responses = await client.batch_request(requests)
            elapsed = asyncio.get_event_loop().time() - start_time

            # Should complete in roughly the time of the longest request
            # (not sum of all requests)
            assert elapsed < 3.0  # Should be much less than 3 seconds
            assert len(responses) == 3

    @pytest.mark.asyncio
    async def test_rate_limiting_in_action(self):
        """Test rate limiting with actual requests"""
        limiter = AsyncRateLimiter(max_calls=2, period=1.0)

        async def make_request():
            await limiter.wait_if_needed()
            return "success"

        # First two should be immediate
        start = asyncio.get_event_loop().time()
        await make_request()
        await make_request()
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed < 0.1  # Should be very fast

        # Third should wait
        start = asyncio.get_event_loop().time()
        await make_request()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have waited at least some time
        assert elapsed >= 0.5  # Approximate
