"""Unit tests for client module"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.client import (
    BrokerClient,
    ZerodhaClient,
    AngelClient,
    ClientFactory,
    ClientManager
)


class TestBrokerClient:
    """Test BrokerClient abstract base class"""

    def test_broker_client_is_abstract(self):
        """Test that BrokerClient cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BrokerClient('zerodha', 'test_account', {})

    def test_broker_client_subclass_can_be_instantiated(self):
        """Test that subclass can be instantiated"""

        class TestClient(BrokerClient):
            def login(self):
                self._authenticated = True
                return True

            def logout(self):
                self._authenticated = False
                return True

            def get_profile(self):
                return {'user_id': 'TEST123'}

        client = TestClient('zerodha', 'test_account', {})
        assert client.broker == 'zerodha'
        assert client.account_name == 'test_account'

    def test_is_authenticated(self):
        """Test is_authenticated method"""

        class TestClient(BrokerClient):
            def login(self):
                self._authenticated = True
                return True

            def logout(self):
                self._authenticated = False
                return True

            def get_profile(self):
                return {'user_id': 'TEST123'}

        client = TestClient('zerodha', 'test_account', {})
        assert client.is_authenticated() is False

        client._authenticated = True
        assert client.is_authenticated() is True


class TestZerodhaClient:
    """Test ZerodhaClient class"""

    @pytest.fixture
    def zerodha_credentials(self):
        """Zerodha credentials"""
        return {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'totp_key': 'test_totp_key',
            'totp_enabled': True,
            'pin': '123456'
        }

    def test_zerodha_client_initialization(self, zerodha_credentials):
        """Test ZerodhaClient initialization"""
        client = ZerodhaClient('test_account', zerodha_credentials)

        assert client.broker == 'zerodha'
        assert client.account_name == 'test_account'
        assert client.credentials == zerodha_credentials

    @patch('core.client.pyotp.TOTP')
    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_login_success(self, mock_zerodha_class, mock_totp_class, zerodha_credentials):
        """Test successful Zerodha login"""
        # Setup mocks
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.return_value = None
        mock_zerodha_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User',
            'email': 'test@example.com'
        }
        mock_zerodha_instance.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha_class.return_value = mock_zerodha_instance

        mock_totp_instance = Mock()
        mock_totp_instance.now.return_value = '123456'
        mock_totp_class.return_value = mock_totp_instance

        client = ZerodhaClient('test_account', zerodha_credentials)
        result = client.login()

        assert result is True
        assert client.is_authenticated() is True

    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_login_failure(self, mock_zerodha_class, zerodha_credentials):
        """Test failed Zerodha login"""
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.side_effect = Exception("Login failed")
        mock_zerodha_class.return_value = mock_zerodha_instance

        client = ZerodhaClient('test_account', zerodha_credentials)

        with pytest.raises(Exception):
            client.login()

    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_logout(self, mock_zerodha_class, zerodha_credentials):
        """Test Zerodha logout"""
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.return_value = None
        mock_zerodha_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User'
        }
        mock_zerodha_instance.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha_class.return_value = mock_zerodha_instance

        client = ZerodhaClient('test_account', zerodha_credentials)
        client.login()
        result = client.logout()

        assert result is True
        assert client.is_authenticated() is False

    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_get_profile(self, mock_zerodha_class, zerodha_credentials):
        """Test getting Zerodha profile"""
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.return_value = None
        mock_zerodha_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User',
            'email': 'test@example.com'
        }
        mock_zerodha_instance.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha_class.return_value = mock_zerodha_instance

        client = ZerodhaClient('test_account', zerodha_credentials)
        client.login()
        profile = client.get_profile()

        assert profile['user_id'] == 'TEST123'

    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_check_funds(self, mock_zerodha_class, zerodha_credentials):
        """Test checking Zerodha funds"""
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.return_value = None
        mock_zerodha_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User'
        }
        mock_zerodha_instance.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha_class.return_value = mock_zerodha_instance

        client = ZerodhaClient('test_account', zerodha_credentials)
        client.login()
        funds = client.check_funds()

        assert funds['equity'] == 100000
        assert funds['commodity'] == 50000

    @patch('core.client.jugaad_trader.Zerodha')
    def test_zerodha_api_property(self, mock_zerodha_class, zerodha_credentials):
        """Test accessing api property"""
        mock_zerodha_instance = Mock()
        mock_zerodha_instance.login.return_value = None
        mock_zerodha_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User'
        }
        mock_zerodha_instance.margins.return_value = {
            'equity': {'available': {'live_balance': 100000}},
            'commodity': {'available': {'live_balance': 50000}}
        }
        mock_zerodha_class.return_value = mock_zerodha_instance

        client = ZerodhaClient('test_account', zerodha_credentials)
        client.login()
        assert client.api is not None


class TestAngelClient:
    """Test AngelClient class"""

    @pytest.fixture
    def angel_credentials(self):
        """Angel credentials"""
        return {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'client_id': 'TEST123'
        }

    def test_angel_client_initialization(self, angel_credentials):
        """Test AngelClient initialization"""
        client = AngelClient('test_account', angel_credentials)

        assert client.broker == 'angel'
        assert client.account_name == 'test_account'
        assert client.credentials == angel_credentials

    @patch('core.client.smartapi.SmartConnect')
    def test_angel_login_success(self, mock_smartapi_class, angel_credentials):
        """Test successful Angel login"""
        mock_smartapi_instance = Mock()
        mock_smartapi_instance.generateSession.return_value = {
            'data': {
                'jwtToken': 'test_token',
                'refreshToken': 'test_refresh_token'
            }
        }
        mock_smartapi_instance.getProfile.return_value = {
            'clientcode': 'TEST123',
            'name': 'Test User'
        }
        mock_smartapi_instance.rmsLimit.return_value = {
            'net': {'availablecash': 100000}
        }
        mock_smartapi_class.return_value = mock_smartapi_instance

        client = AngelClient('test_account', angel_credentials)
        result = client.login()

        assert result is True
        assert client.is_authenticated() is True

    @patch('core.client.smartapi.SmartConnect')
    def test_angel_login_failure(self, mock_smartapi_class, angel_credentials):
        """Test failed Angel login"""
        mock_smartapi_instance = Mock()
        mock_smartapi_instance.generateSession.return_value = None
        mock_smartapi_class.return_value = mock_smartapi_instance

        client = AngelClient('test_account', angel_credentials)

        with pytest.raises(Exception):
            client.login()

    @patch('core.client.smartapi.SmartConnect')
    def test_angel_logout(self, mock_smartapi_class, angel_credentials):
        """Test Angel logout"""
        mock_smartapi_instance = Mock()
        mock_smartapi_instance.generateSession.return_value = {
            'data': {
                'jwtToken': 'test_token',
                'refreshToken': 'test_refresh_token'
            }
        }
        mock_smartapi_instance.getProfile.return_value = {
            'clientcode': 'TEST123',
            'name': 'Test User'
        }
        mock_smartapi_instance.rmsLimit.return_value = {
            'net': {'availablecash': 100000}
        }
        mock_smartapi_instance.terminateSession.return_value = True
        mock_smartapi_class.return_value = mock_smartapi_instance

        client = AngelClient('test_account', angel_credentials)
        client.login()
        result = client.logout()

        assert result is True
        assert client.is_authenticated() is False

    @patch('core.client.smartapi.SmartConnect')
    def test_angel_get_profile(self, mock_smartapi_class, angel_credentials):
        """Test getting Angel profile"""
        mock_smartapi_instance = Mock()
        mock_smartapi_instance.generateSession.return_value = {
            'data': {
                'jwtToken': 'test_token',
                'refreshToken': 'test_refresh_token'
            }
        }
        mock_smartapi_instance.getProfile.return_value = {
            'clientcode': 'TEST123',
            'name': 'Test User',
            'email': 'test@example.com'
        }
        mock_smartapi_instance.rmsLimit.return_value = {
            'net': {'availablecash': 100000}
        }
        mock_smartapi_class.return_value = mock_smartapi_instance

        client = AngelClient('test_account', angel_credentials)
        client.login()
        profile = client.get_profile()

        assert profile['clientcode'] == 'TEST123'

    @patch('core.client.smartapi.SmartConnect')
    def test_angel_check_funds(self, mock_smartapi_class, angel_credentials):
        """Test checking Angel funds"""
        mock_smartapi_instance = Mock()
        mock_smartapi_instance.generateSession.return_value = {
            'data': {
                'jwtToken': 'test_token',
                'refreshToken': 'test_refresh_token'
            }
        }
        mock_smartapi_instance.getProfile.return_value = {
            'clientcode': 'TEST123',
            'name': 'Test User'
        }
        mock_smartapi_instance.rmsLimit.return_value = {
            'net': {'availablecash': 100000}
        }
        mock_smartapi_class.return_value = mock_smartapi_instance

        client = AngelClient('test_account', angel_credentials)
        client.login()
        funds = client.check_funds()

        assert funds == 100000


class TestClientFactory:
    """Test ClientFactory class"""

    def test_create_zerodha_client(self):
        """Test creating Zerodha client"""
        credentials = {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'totp_key': 'test_totp_key',
            'totp_enabled': True,
            'pin': '123456'
        }

        client = ClientFactory.create_client('zerodha', 'test_account', credentials)

        assert client.broker == 'zerodha'
        assert isinstance(client, ZerodhaClient)

    def test_create_angel_client(self):
        """Test creating Angel client"""
        credentials = {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'client_id': 'TEST123'
        }

        client = ClientFactory.create_client('angel', 'test_account', credentials)

        assert client.broker == 'angel'
        assert isinstance(client, AngelClient)

    def test_create_angelbroking_client(self):
        """Test creating AngelBroking client (alias for Angel)"""
        credentials = {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'client_id': 'TEST123'
        }

        client = ClientFactory.create_client('angelbroking', 'test_account', credentials)

        assert client.broker == 'angel'
        assert isinstance(client, AngelClient)

    def test_create_invalid_broker(self):
        """Test creating client for invalid broker"""
        with pytest.raises(ValueError):
            ClientFactory.create_client('invalid_broker', 'test_account', {})

    def test_register_client(self):
        """Test registering a custom client"""

        class CustomClient(BrokerClient):
            def login(self):
                self._authenticated = True
                return True

            def logout(self):
                self._authenticated = False
                return True

            def get_profile(self):
                return {'user_id': 'TEST123'}

        ClientFactory.register_client('custom', CustomClient)

        client = ClientFactory.create_client('custom', 'test_account', {})

        assert isinstance(client, CustomClient)

    def test_get_supported_brokers(self):
        """Test getting supported brokers"""
        brokers = ClientFactory.get_supported_brokers()

        assert 'zerodha' in brokers
        assert 'angel' in brokers
        assert 'angelbroking' in brokers


class TestClientManager:
    """Test ClientManager class"""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients"""
        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'
        client1._authenticated = False

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'
        client2._authenticated = False

        return [client1, client2]

    def test_client_manager_initialization(self):
        """Test ClientManager initialization"""
        manager = ClientManager()
        assert manager.clients == {}
        assert manager.credential_manager is not None

    def test_add_client(self):
        """Test adding a client"""
        manager = ClientManager()
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'

        manager.add_client('zerodha', 'test_account', client)

        assert 'zerodha_test_account' in manager.clients

    def test_get_client(self):
        """Test getting a client"""
        manager = ClientManager()
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'

        manager.add_client('zerodha', 'test_account', client)

        retrieved = manager.get_client('zerodha', 'test_account')

        assert retrieved is client

    def test_get_client_not_found(self):
        """Test getting non-existent client"""
        manager = ClientManager()

        retrieved = manager.get_client('zerodha', 'nonexistent')

        assert retrieved is None

    def test_remove_client(self):
        """Test removing a client"""
        manager = ClientManager()
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'

        manager.add_client('zerodha', 'test_account', client)
        manager.remove_client('zerodha', 'test_account')

        assert 'zerodha_test_account' not in manager.clients

    def test_login_all(self, mock_clients):
        """Test logging in all clients"""
        manager = ClientManager()

        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'
        client1.login.return_value = True

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'
        client2.login.return_value = True

        manager.add_client('zerodha', 'account1', client1)
        manager.add_client('zerodha', 'account2', client2)

        results = manager.login_all()

        assert len(results) == 2
        assert all(results.values())

    def test_logout_all(self, mock_clients):
        """Test logging out all clients"""
        manager = ClientManager()

        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'
        client1.logout.return_value = True

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'
        client2.logout.return_value = True

        manager.add_client('zerodha', 'account1', client1)
        manager.add_client('zerodha', 'account2', client2)

        results = manager.logout_all()

        assert len(results) == 2
        assert all(results.values())

    def test_get_all_clients(self):
        """Test getting all clients"""
        manager = ClientManager()

        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'

        manager.add_client('zerodha', 'account1', client1)
        manager.add_client('zerodha', 'account2', client2)

        all_clients = manager.get_all_clients()

        assert len(all_clients) == 2

    def test_get_authenticated_clients(self):
        """Test getting authenticated clients"""
        manager = ClientManager()

        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'
        client1.is_authenticated.return_value = True

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'
        client2.is_authenticated.return_value = False

        manager.add_client('zerodha', 'account1', client1)
        manager.add_client('zerodha', 'account2', client2)

        authenticated = manager.get_authenticated_clients()

        assert len(authenticated) == 1
        assert authenticated[0] is client1
