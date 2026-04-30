"""
Async Support Module
Provides async/await support for concurrent API calls
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

from .error_handler import (
    PyPortManError, NetworkError, RateLimitError,
    retry_on_failure, with_error_handling
)
from .logging_config import get_logger
from .config import get_config

logger = get_logger('pyportman.async')


@dataclass
class AsyncRequest:
    """Async request data class"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    json_data: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 0


@dataclass
class AsyncResponse:
    """Async response data class"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    elapsed: float
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            'status_code': self.status_code,
            'data': self.data,
            'headers': self.headers,
            'elapsed': self.elapsed,
            'success': self.success,
            'error': self.error
        }


class AsyncRateLimiter:
    """
    Async rate limiter for API calls
    """

    def __init__(self, max_calls: int = 10, period: float = 60.0):
        """
        Initialize async rate limiter

        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: List[datetime] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
        async with self._lock:
            now = datetime.now()

            # Remove calls older than the period
            self.calls = [call_time for call_time in self.calls
                         if (now - call_time).total_seconds() < self.period]

            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = self.calls[0]
                wait_time = (oldest_call.timestamp() + self.period - now.timestamp()).total_seconds()

                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)

            # Record this call
            self.calls.append(now)

    def get_remaining_calls(self) -> int:
        """Get number of remaining calls in current period"""
        now = datetime.now()
        self.calls = [call_time for call_time in self.calls
                     if (now - call_time).total_seconds() < self.period]
        return self.max_calls - len(self.calls)


class AsyncHTTPClient:
    """
    Async HTTP client for making concurrent API calls
    """

    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        timeout: int = 30,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize async HTTP client

        Args:
            max_concurrent: Maximum concurrent requests
            timeout: Request timeout in seconds
            enable_rate_limiting: Enable rate limiting
        """
        config = get_config()
        self.max_concurrent = max_concurrent or config.max_concurrent_requests
        self.timeout = timeout
        self.enable_rate_limiting = enable_rate_limiting

        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._rate_limiter = AsyncRateLimiter(
            max_calls=config.zerodha.rate_limit,
            period=60.0
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self) -> None:
        """Start the HTTP client session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Async HTTP client started")

    async def close(self) -> None:
        """Close the HTTP client session"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Async HTTP client closed")

    async def request(self, request: AsyncRequest) -> AsyncResponse:
        """
        Make an async HTTP request

        Args:
            request: AsyncRequest object

        Returns:
            AsyncResponse object
        """
        if self._session is None or self._session.closed:
            await self.start()

        async with self._semaphore:
            if self.enable_rate_limiting:
                await self._rate_limiter.wait_if_needed()

            start_time = datetime.now()

            try:
                async with self._session.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    params=request.params,
                    data=request.data if request.data else None,
                    json=request.json_data if request.json_data else None
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()

                    try:
                        data = await response.json()
                    except:
                        data = await response.text()

                    return AsyncResponse(
                        status_code=response.status,
                        data=data,
                        headers=dict(response.headers),
                        elapsed=elapsed,
                        success=response.status < 400
                    )

            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start_time).total_seconds()
                return AsyncResponse(
                    status_code=408,
                    data=None,
                    headers={},
                    elapsed=elapsed,
                    success=False,
                    error="Request timeout"
                )

            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                return AsyncResponse(
                    status_code=500,
                    data=None,
                    headers={},
                    elapsed=elapsed,
                    success=False,
                    error=str(e)
                )

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncResponse:
        """
        Make a GET request

        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers

        Returns:
            AsyncResponse object
        """
        request = AsyncRequest(
            url=url,
            method="GET",
            params=params or {},
            headers=headers or {}
        )
        return await self.request(request)

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncResponse:
        """
        Make a POST request

        Args:
            url: Request URL
            data: Form data
            json_data: JSON data
            headers: Request headers

        Returns:
            AsyncResponse object
        """
        request = AsyncRequest(
            url=url,
            method="POST",
            data=data or {},
            json_data=json_data or {},
            headers=headers or {}
        )
        return await self.request(request)

    async def batch_request(
        self,
        requests: List[AsyncRequest]
    ) -> List[AsyncResponse]:
        """
        Make multiple requests concurrently

        Args:
            requests: List of AsyncRequest objects

        Returns:
            List of AsyncResponse objects
        """
        tasks = [self.request(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)


class AsyncBatchProcessor:
    """
    Batch processor for concurrent operations
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize batch processor

        Args:
            max_concurrent: Maximum concurrent operations
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Process items concurrently

        Args:
            items: List of items to process
            processor: Async function to process each item
            progress_callback: Optional callback for progress updates

        Returns:
            List of processed results
        """
        results = []
        completed = 0
        total = len(items)

        async def process_with_semaphore(item):
            async with self._semaphore:
                result = await processor(item)
                nonlocal completed
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                return result

        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def process_map(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]]
    ) -> Dict[Any, Any]:
        """
        Process items and return as dictionary

        Args:
            items: List of items to process
            processor: Async function to process each item

        Returns:
            Dictionary mapping items to results
        """
        results = {}

        async def process_item(item):
            result = await processor(item)
            return item, result

        tasks = [process_item(item) for item in items]
        processed = await asyncio.gather(*tasks, return_exceptions=True)

        for item, result in processed:
            results[item] = result

        return results


async def run_async(coro: Awaitable[Any]) -> Any:
    """
    Run an async coroutine from sync code

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def run_async_sync(coro: Awaitable[Any]) -> Any:
    """
    Synchronous wrapper for async functions

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    return asyncio.run(coro)


if __name__ == "__main__":
    # Test async functionality
    async def test_async_client():
        async with AsyncHTTPClient(max_concurrent=5) as client:
            # Test single request
            response = await client.get("https://httpbin.org/get")
            print(f"Single request: {response.status_code}, {response.success}")

            # Test batch requests
            requests = [
                AsyncRequest(url=f"https://httpbin.org/delay/{i}")
                for i in range(1, 4)
            ]
            responses = await client.batch_request(requests)
            print(f"Batch requests: {len(responses)} responses")

    asyncio.run(test_async_client())
