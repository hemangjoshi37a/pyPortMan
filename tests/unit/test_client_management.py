"""
Unit tests for client management
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pyportman import (
    BrokerClient,
    ZerodhaClient,
    AngelClient,
    ClientFactory,
    ClientManager,
    AuthenticationError,
    ConfigurationError
)


class TestZerodhaClient:
    """Test cases for ZerodhaClient"""

    @pytest.fixture
    def zerodha_client(self):
        """Create ZerodhaClient instance"""
        credentials = {
            'user_id': 'TEST_USER',
            'password': 'TEST_PASS',
            'totp_key': 'TEST_TOTP',
            'totp_enabled': True
        }
        return ZerodhaClient('test_account', credentials)

    def test_zerodha_client_initialization(self, zerodha_client):
        """Test ZerodhaClient initialization"""
        assert zerodha_client.broker == 'zerodha'
        assert zerodha_client.account_name == 'test_account'
        assert zerodha_client.credentials['user_id'] == 'TEST_USER'
        assert zerodha_client._authenticated is False

    @patch('pyotp.TOTP')
    @patch('jugaad_trader.Zerodha')
    def test_zerodha_login_success(self, mock_zerodha, mock_totp, zerodha_client):
        """Test successful Zerodha login"""
        # Setup mocks
        mock_totp_instance = Mock()
        mock_totp_instance.now.return_value = '123456'
        mock_totp.return_value = mock_totp_instance

        mock_api = Mock()
        mock_api.login.return_value = None
        mock_api.profile.return_value = {
            'user_name': 'Test User',
            'email': 'test@example.com'
        }
        mock_zerodha.return_value = mock_api

        # Login
        result = zerodha_client.login()

        assert result is True
        assert zerodha_client._authenticated is True
        assert zerodha_client._last_login is not None

    def test_zerodha_login_missing_credentials(self, zerodha_client):
        """Test Zerodha login with missing credentials"""
        zerodha_client.credentials = {'user_id': 'TEST'}

        with pytest.raises(AuthenticationError):
            zerodha_client.login()

    @patch('jugaad_trader.Zerodha')
    def test_zerodha_logout(self, mock_zerodha, zerodha_client):
        """Test Zerodha logout"""
        mock_api = Mock()
        mock_zerodha.return_value = mock_api

        zerodha_client._zerodha_user = mock_api
        zerodha_client._authenticated = True

        result = zerodha_client.logout()

        assert result is True
        assert zerodha_client._authenticated is False

    @patch('jugaad_trader.Zerodha')
    def test_zerodha_get_profile(self, mock_zerodha, zerodha_client):
        """Test getting Zerodha profile"""
        mock_api = Mock()
        mock_api.profile.return_value = {
            'user_id': 'TEST_USER',
            'user_name': 'Test User',
            'email': 'test@example.com'
        }
        mock_zerodha.return_value = mock_api

        zerodha_client._zerodha_user = mock_api
        zerodha_client._authenticated = True

        profile = zerodha_client.get_profile()

        assert profile['user_id'] == 'TEST_USER'
        assert profile['user_name'] == 'Test User'
        assert profile['broker'] == 'zerodha'

    def test_zerodha_get_profile_not_authenticated(self, zerodha_client):
        """Test getting profile when not authenticated"""
        zerodha_client._authenticated = False

        with pytest.raises(AuthenticationError):
            zerodha_client.get_profile()

    @patch('jugaad_trader.Zerodha')
    def test_zerodha_check_funds(self, mock_zerodha, zerodha_client):
        """Test checking Zerodha funds"""
        mock_api = Mock()
        mock_api.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha.return_value = mock_api

        zerodha_client._zerodha_user = mock_api
        zerodha_client._authenticated = True

        funds = zerodha_client.check_funds()

        assert funds['equity'] == 100000.0
        assert funds['commodity'] == 50000.0
        assert funds['total'] == 150000.0

    @patch('jugaad_trader.Zerodha')
    def test_zerodha_api_property(self, mock_zerodha, zerodha_client):
        """Test Zerodha API property"""
        mock_api = Mock()
        mock_zerodha.return_value = mock_api

        zerodha_client._zerodha_user = mock_api
        zerodha_client._authenticated = True

        api = zerodha_client.api
        assert api == mock_api

    def test_zerodha_api_property_not_authenticated(self, zerodha_client):
        """Test API property when not authenticated"""
        zerodha_client._authenticated = False

        with pytest.raises(AuthenticationError):
            _ = zerodha_client.api


class TestAngelClient:
    """Test cases for AngelClient"""

    @pytest.fixture
    def angel_client(self):
        """Create AngelClient instance"""
        credentials = {
            'api_key': 'TEST_API_KEY',
            'user_id': 'TEST_USER',
            'password': 'TEST_PASS'
        }
        return AngelClient('test_account', credentials)

    def test_angel_client_initialization(self, angel_client):
        """Test AngelClient initialization"""
        assert angel_client.broker == 'angel'
        assert angel_client.account_name == 'test_account'
        assert angel_client.credentials['api_key'] == 'TEST_API_KEY'
        assert angel_client._authenticated is False

    @patch('smartapi.SmartConnect')
    def test_angel_login_success(self, mock_smartapi, angel_client):
        """Test successful Angel login"""
        mock_api = Mock()
        mock_api.generateSession.return_value = {
            'data': {
                'refreshToken': 'test_refresh_token'
            }
        }
        mock_api.getfeedToken.return_value = 'test_feed_token'
        mock_api.getProfile.return_value = {
            'data': {
                'name': 'Test User'
            }
        }
        mock_smartapi.return_value = mock_api

        result = angel_client.login()

        assert result is True
        assert angel_client._authenticated is True
        assert angel_client._refresh_token == 'test_refresh_token'

    def test_angel_login_missing_credentials(self, angel_client):
        """Test Angel login with missing credentials"""
        angel_client.credentials = {'api_key': 'TEST'}

        with pytest.raises(AuthenticationError):
            angel_client.login()

    @patch('smartapi.SmartConnect')
    def test_angel_logout(self, mock_smartapi, angel_client):
        """Test Angel logout"""
        mock_api = Mock()
        mock_smartapi.return_value = mock_api

        angel_client._angel_user = mock_api
        angel_client._refresh_token = 'test_token'
        angel_client._authenticated = True

        result = angel_client.logout()

        assert result is True
        assert angel_client._authenticated is False

    @patch('smartapi.SmartConnect')
    def test_angel_get_profile(self, mock_smartapi, angel_client):
        """Test getting Angel profile"""
        mock_api = Mock()
        mock_api.getProfile.return_value = {
            'data': {
                'name': 'Test User'
            }
        }
        mock_smartapi.return_value = mock_api

        angel_client._angel_user = mock_api
        angel_client._refresh_token = 'test_token'
        angel_client._authenticated = True

        profile = angel_client.get_profile()

        assert profile['user_id'] == 'TEST_USER'
        assert profile['user_name'] == 'Test User'
        assert profile['broker'] == 'angel'

    @patch('smartapi.SmartConnect')
    def test_angel_check_funds(self, mock_smartapi, angel_client):
        """Test checking Angel funds"""
        mock_api = Mock()
        mock_api.rmsLimit.return_value = {
            'data': {
                'availablecash': 100000
            }
        }
        mock_smartapi.return_value = mock_api

        angel_client._angel_user = mock_api
        angel_client._authenticated = True

        funds = angel_client.check_funds()

        assert funds['equity'] == 100000.0
        assert funds['commodity'] == 100000.0
        assert funds['total'] == 200000.0


class TestClientFactory:
    """Test cases for ClientFactory"""

    def test_create_zerodha_client(self):
        """Test creating Zerodha client"""
        credentials = {
            'user_id': 'TEST',
            'password': 'TEST',
            'totp_key': 'TEST',
            'totp_enabled': True
        }

        client = ClientFactory.create_client('zerodha', 'test_account', credentials)

        assert isinstance(client, ZerodhaClient)
        assert client.account_name == 'test_account'

    def test_create_angel_client(self):
        """Test creating Angel client"""
        credentials = {
            'api_key': 'TEST',
            'user_id': 'TEST',
            'password': 'TEST'
        }

        client = ClientFactory.create_client('angel', 'test_account', credentials)

        assert isinstance(client, AngelClient)
        assert client.account_name == 'test_account'

    def test_create_angelbroking_client(self):
        """Test creating Angel Broking client (alias)"""
        credentials = {
            'api_key': 'TEST',
            'user_id': 'TEST',
            'password': 'TEST'
        }

        client = ClientFactory.create_client('angelbroking', 'test_account', credentials)

        assert isinstance(client, AngelClient)

    def test_create_unsupported_broker(self):
        """Test creating client for unsupported broker"""
        credentials = {}

        with pytest.raises(ConfigurationError):
            ClientFactory.create_client('unsupported', 'test_account', credentials)

    def test_get_supported_brokers(self):
        """Test getting list of supported brokers"""
        brokers = ClientFactory.get_supported_brokers()

        assert 'zerodha' in brokers
        assert 'angel' in brokers
        assert 'angelbroking' in brokers

    def test_register_client(self):
        """Test registering a new client class"""
        class CustomClient(BrokerClient):
            def login(self):
                return True

            def logout(self):
                return True

            def get_profile(self):
                return {}

        ClientFactory.register_client('custom', CustomClient)

        brokers = ClientFactory.get_supported_brokers()
        assert 'custom' in brokers

    def test_register_invalid_client(self):
        """Test registering invalid client class"""
        class InvalidClient:
            pass

        with pytest.raises(ConfigurationError):
            ClientFactory.register_client('invalid', InvalidClient)


class TestClientManager:
    """Test cases for ClientManager"""

    @pytest.fixture
    def client_manager(self):
        """Create ClientManager instance"""
        return ClientManager()

    def test_client_manager_initialization(self, client_manager):
        """Test ClientManager initialization"""
        assert client_manager.clients == {}
        assert client_manager.credential_manager is not None

    @patch('pyportman.client.CredentialManager')
    def test_add_client(self, mock_cred_manager, client_manager):
        """Test adding a client"""
        mock_cred_instance = Mock()
        mock_cred_instance.get_broker_credentials.return_value = {
            'user_id': 'TEST',
            'password': 'TEST'
        }
        mock_cred_manager.return_value = mock_cred_instance

        client_manager.credential_manager = mock_cred_instance

        client = client_manager.add_client('zerodha', 'test_account')

        assert client is not None
        assert 'zerodha_test_account' in client_manager.clients

    def test_add_client_with_credentials(self, client_manager):
        """Test adding client with explicit credentials"""
        credentials = {
            'user_id': 'TEST',
            'password': 'TEST'
        }

        with patch('pyportman.client.ClientFactory.create_client') as mock_create:
            mock_client = Mock()
            mock_create.return_value = mock_client

            client = client_manager.add_client('zerodha', 'test_account', credentials)

            assert client == mock_client

    def test_get_client(self, client_manager):
        """Test getting existing client"""
        mock_client = Mock()
        client_manager.clients['zerodha_test_account'] = mock_client

        result = client_manager.get_client('zerodha', 'test_account')

        assert result == mock_client

    def test_get_client_not_found(self, client_manager):
        """Test getting non-existent client"""
        result = client_manager.get_client('zerodha', 'nonexistent')

        assert result is None

    def test_remove_client(self, client_manager):
        """Test removing a client"""
        mock_client = Mock()
        mock_client.logout.return_value = True
        client_manager.clients['zerodha_test_account'] = mock_client

        result = client_manager.remove_client('zerodha', 'test_account')

        assert result is True
        assert 'zerodha_test_account' not in client_manager.clients

    def test_remove_client_not_found(self, client_manager):
        """Test removing non-existent client"""
        result = client_manager.remove_client('zerodha', 'nonexistent')

        assert result is False

    def test_login_all(self, client_manager):
        """Test logging in all clients"""
        mock_client1 = Mock()
        mock_client1.login.return_value = True

        mock_client2 = Mock()
        mock_client2.login.return_value = False

        client_manager.clients = {
            'zerodha_test1': mock_client1,
            'angel_test2': mock_client2
        }

        results = client_manager.login_all()

        assert results['zerodha_test1'] is True
        assert results['angel_test2'] is False

    def test_logout_all(self, client_manager):
        """Test logging out all clients"""
        mock_client1 = Mock()
        mock_client1.logout.return_value = True

        mock_client2 = Mock()
        mock_client2.logout.return_value = True

        client_manager.clients = {
            'zerodha_test1': mock_client1,
            'angel_test2': mock_client2
        }

        results = client_manager.logout_all()

        assert results['zerodha_test1'] is True
        assert results['angel_test2'] is True

    def test_get_all_clients(self, client_manager):
        """Test getting all clients"""
        mock_client1 = Mock()
        mock_client2 = Mock()

        client_manager.clients = {
            'zerodha_test1': mock_client1,
            'angel_test2': mock_client2
        }

        clients = client_manager.get_all_clients()

        assert len(clients) == 2
        assert mock_client1 in clients
        assert mock_client2 in clients

    def test_get_authenticated_clients(self, client_manager):
        """Test getting authenticated clients"""
        mock_client1 = Mock()
        mock_client1.is_authenticated.return_value = True

        mock_client2 = Mock()
        mock_client2.is_authenticated.return_value = False

        client_manager.clients = {
            'zerodha_test1': mock_client1,
            'angel_test2': mock_client2
        }

        auth_clients = client_manager.get_authenticated_clients()

        assert len(auth_clients) == 1
        assert mock_client1 in auth_clients
        assert mock_client2 not in auth_clients


class TestBrokerClient:
    """Test cases for BrokerClient base class"""

    def test_broker_client_is_authenticated(self):
        """Test is_authenticated method"""
        client = BrokerClient('test', 'test_account', {})
        assert client.is_authenticated() is False

        client._authenticated = True
        assert client.is_authenticated() is True

    def test_broker_client_refresh_session_not_authenticated(self):
        """Test refresh session when not authenticated"""
        client = BrokerClient('test', 'test_account', {})

        with patch.object(client, 'login', return_value=True):
            result = client.refresh_session()
            assert result is True

    def test_broker_client_refresh_session_authenticated(self):
        """Test refresh session when authenticated"""
        client = BrokerClient('test', 'test_account', {})
        client._authenticated = True
        client._last_login = datetime.now()

        result = client.refresh_session()
        assert result is True

    def test_broker_client_refresh_session_expired(self):
        """Test refresh session when expired"""
        client = BrokerClient('test', 'test_account', {})
        client._authenticated = True
        # Set last login to 25 hours ago
        client._last_login = datetime.now() - datetime.timedelta(hours=25)

        with patch.object(client, 'login', return_value=True):
            result = client.refresh_session()
            assert result is True
