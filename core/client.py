"""
Client Management Module
Handles broker client initialization, authentication, and session management
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import pyotp

from .error_handler import (
    AuthenticationError, NetworkError, ConfigurationError,
    retry_on_failure, with_error_handling, RateLimiter
)
from .logging_config import get_logger
from .security import CredentialManager, mask_sensitive_data

logger = get_logger('pyportman.client')


class BrokerClient(ABC):
    """
    Abstract base class for broker clients
    """

    def __init__(self, broker: str, account_name: str, credentials: Dict[str, Any]):
        """
        Initialize broker client

        Args:
            broker: Broker name (zerodha, angel, etc.)
            account_name: Account name/identifier
            credentials: Dictionary of credentials
        """
        self.broker = broker.lower()
        self.account_name = account_name
        self.credentials = credentials

        # Session state
        self._authenticated = False
        self._session_data = {}
        self._last_login = None

        # Rate limiting
        self.rate_limiter = RateLimiter(max_calls=10, period=60)

        # Funds
        self.funds_equity = 0.0
        self.funds_commodity = 0.0

        logger.info(f"Initialized {broker} client for account: {account_name}")

    @abstractmethod
    def login(self) -> bool:
        """
        Authenticate with broker API

        Returns:
            True if login successful
        """
        pass

    @abstractmethod
    def logout(self) -> bool:
        """
        Logout from broker API

        Returns:
            True if logout successful
        """
        pass

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information

        Returns:
            Dictionary with profile data
        """
        pass

    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._authenticated

    def check_funds(self) -> Dict[str, float]:
        """
        Check available funds

        Returns:
            Dictionary with equity and commodity funds
        """
        raise NotImplementedError("Subclasses must implement check_funds")

    def refresh_session(self) -> bool:
        """
        Refresh authentication session if needed

        Returns:
            True if refresh successful
        """
        if not self._authenticated:
            return self.login()

        # Check if session needs refresh (e.g., after 24 hours)
        if self._last_login:
            hours_since_login = (datetime.now() - self._last_login).total_seconds() / 3600
            if hours_since_login > 23:
                logger.info(f"Session for {self.account_name} expired, re-authenticating")
                return self.login()

        return True


class ZerodhaClient(BrokerClient):
    """
    Zerodha broker client implementation
    """

    def __init__(self, account_name: str, credentials: Dict[str, Any]):
        super().__init__('zerodha', account_name, credentials)
        self._zerodha_user = None

    @retry_on_failure(max_retries=3, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def login(self) -> bool:
        """Login to Zerodha"""
        try:
            from jugaad_trader import Zerodha

            user_id = self.credentials.get('user_id')
            password = self.credentials.get('password')
            totp_key = self.credentials.get('totp_key')
            totp_enabled = self.credentials.get('totp_enabled', False)

            if not user_id or not password:
                raise AuthenticationError("Missing user_id or password for Zerodha")

            # Generate TOTP if enabled
            twofa = None
            if totp_enabled and totp_key:
                totp = pyotp.TOTP(totp_key)
                twofa = int(totp.now())
                logger.debug(f"Generated TOTP for {mask_sensitive_data(user_id)}")
            elif 'pin' in self.credentials:
                twofa = int(self.credentials['pin'])

            if not twofa:
                raise AuthenticationError("Missing PIN or TOTP for Zerodha")

            # Create Zerodha instance
            self._zerodha_user = Zerodha(
                user_id=user_id,
                password=password,
                twofa=twofa
            )

            # Perform login
            self._zerodha_user.login()
            profile = self._zerodha_user.profile()

            self._authenticated = True
            self._last_login = datetime.now()
            self._session_data = {
                'user_id': user_id,
                'user_name': profile.get('user_name', ''),
                'email': profile.get('email', '')
            }

            logger.info(f"Zerodha login successful for {mask_sensitive_data(user_id)}")
            return True

        except Exception as e:
            self._authenticated = False
            raise AuthenticationError(f"Zerodha login failed: {str(e)}")

    def logout(self) -> bool:
        """Logout from Zerodha"""
        try:
            if self._zerodha_user:
                # Zerodha doesn't have explicit logout, just clear session
                self._zerodha_user = None
            self._authenticated = False
            logger.info(f"Zerodha logout for {self.account_name}")
            return True
        except Exception as e:
            logger.error(f"Zerodha logout error: {e}")
            return False

    def get_profile(self) -> Dict[str, Any]:
        """Get Zerodha user profile"""
        if not self._authenticated or not self._zerodha_user:
            raise AuthenticationError("Not authenticated with Zerodha")

        try:
            profile = self._zerodha_user.profile()
            return {
                'user_id': profile.get('user_id'),
                'user_name': profile.get('user_name'),
                'email': profile.get('email'),
                'broker': 'zerodha'
            }
        except Exception as e:
            raise NetworkError(f"Failed to get Zerodha profile: {e}")

    def check_funds(self) -> Dict[str, float]:
        """Check available funds"""
        if not self._authenticated or not self._zerodha_user:
            raise AuthenticationError("Not authenticated with Zerodha")

        try:
            margins = self._zerodha_user.margins()
            self.funds_equity = float(margins.get('equity', {}).get('available', {}).get('live_balance', 0))
            self.funds_commodity = float(margins.get('commodity', {}).get('available', {}).get('live_balance', 0))

            return {
                'equity': self.funds_equity,
                'commodity': self.funds_commodity,
                'total': self.funds_equity + self.funds_commodity
            }
        except Exception as e:
            raise NetworkError(f"Failed to get Zerodha funds: {e}")

    @property
    def api(self):
        """Get underlying Zerodha API instance"""
        if not self._authenticated or not self._zerodha_user:
            raise AuthenticationError("Not authenticated with Zerodha")
        return self._zerodha_user


class AngelClient(BrokerClient):
    """
    Angel Broking broker client implementation
    """

    def __init__(self, account_name: str, credentials: Dict[str, Any]):
        super().__init__('angel', account_name, credentials)
        self._angel_user = None
        self._refresh_token = None
        self._feed_token = None

    @retry_on_failure(max_retries=3, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def login(self) -> bool:
        """Login to Angel Broking"""
        try:
            from smartapi import SmartConnect

            api_key = self.credentials.get('api_key')
            user_id = self.credentials.get('user_id')
            password = self.credentials.get('password')

            if not api_key or not user_id or not password:
                raise AuthenticationError("Missing api_key, user_id, or password for Angel")

            # Create Angel instance
            self._angel_user = SmartConnect(api_key=api_key)

            # Generate session
            session_data = self._angel_user.generateSession(user_id, password)

            if not session_data or 'data' not in session_data:
                raise AuthenticationError("Failed to generate Angel session")

            self._refresh_token = session_data['data'].get('refreshToken')
            self._feed_token = self._angel_user.getfeedToken()

            # Get profile
            profile = self._angel_user.getProfile(self._refresh_token)

            self._authenticated = True
            self._last_login = datetime.now()
            self._session_data = {
                'user_id': user_id,
                'user_name': profile.get('data', {}).get('name', ''),
                'refresh_token': self._refresh_token
            }

            logger.info(f"Angel login successful for {mask_sensitive_data(user_id)}")
            return True

        except Exception as e:
            self._authenticated = False
            raise AuthenticationError(f"Angel login failed: {str(e)}")

    def logout(self) -> bool:
        """Logout from Angel Broking"""
        try:
            if self._angel_user:
                self._angel_user.terminateSession(self._refresh_token)
                self._angel_user = None
            self._authenticated = False
            logger.info(f"Angel logout for {self.account_name}")
            return True
        except Exception as e:
            logger.error(f"Angel logout error: {e}")
            return False

    def get_profile(self) -> Dict[str, Any]:
        """Get Angel user profile"""
        if not self._authenticated or not self._angel_user:
            raise AuthenticationError("Not authenticated with Angel")

        try:
            profile = self._angel_user.getProfile(self._refresh_token)
            return {
                'user_id': self.credentials.get('user_id'),
                'user_name': profile.get('data', {}).get('name', ''),
                'broker': 'angel'
            }
        except Exception as e:
            raise NetworkError(f"Failed to get Angel profile: {e}")

    def check_funds(self) -> Dict[str, float]:
        """Check available funds"""
        if not self._authenticated or not self._angel_user:
            raise AuthenticationError("Not authenticated with Angel")

        try:
            limits = self._angel_user.rmsLimit()
            available_cash = float(limits.get('data', {}).get('availablecash', 0))

            self.funds_equity = available_cash
            self.funds_commodity = available_cash  # Angel doesn't separate

            return {
                'equity': self.funds_equity,
                'commodity': self.funds_commodity,
                'total': self.funds_equity + self.funds_commodity
            }
        except Exception as e:
            raise NetworkError(f"Failed to get Angel funds: {e}")

    @property
    def api(self):
        """Get underlying Angel API instance"""
        if not self._authenticated or not self._angel_user:
            raise AuthenticationError("Not authenticated with Angel")
        return self._angel_user


class ClientFactory:
    """
    Factory for creating broker clients
    """

    _client_classes = {
        'zerodha': ZerodhaClient,
        'angel': AngelClient,
        'angelbroking': AngelClient,
    }

    @classmethod
    def create_client(cls, broker: str, account_name: str, credentials: Dict[str, Any]) -> BrokerClient:
        """
        Create a broker client instance

        Args:
            broker: Broker name
            account_name: Account name
            credentials: Credentials dictionary

        Returns:
            BrokerClient instance

        Raises:
            ConfigurationError: If broker is not supported
        """
        broker_lower = broker.lower()

        if broker_lower not in cls._client_classes:
            supported = ', '.join(cls._client_classes.keys())
            raise ConfigurationError(
                f"Unsupported broker: {broker}. Supported brokers: {supported}"
            )

        client_class = cls._client_classes[broker_lower]
        return client_class(account_name, credentials)

    @classmethod
    def register_client(cls, broker: str, client_class: type) -> None:
        """
        Register a new broker client class

        Args:
            broker: Broker name
            client_class: Client class (must inherit from BrokerClient)
        """
        if not issubclass(client_class, BrokerClient):
            raise ConfigurationError("Client class must inherit from BrokerClient")

        cls._client_classes[broker.lower()] = client_class
        logger.info(f"Registered client for broker: {broker}")

    @classmethod
    def get_supported_brokers(cls) -> List[str]:
        """Get list of supported brokers"""
        return list(cls._client_classes.keys())


class ClientManager:
    """
    Manages multiple broker clients
    """

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Initialize client manager

        Args:
            credential_manager: Optional credential manager instance
        """
        self.credential_manager = credential_manager or CredentialManager()
        self.clients: Dict[str, BrokerClient] = {}

    def add_client(self, broker: str, account_name: str, credentials: Optional[Dict] = None) -> BrokerClient:
        """
        Add a client to the manager

        Args:
            broker: Broker name
            account_name: Account name
            credentials: Optional credentials (will fetch from env if not provided)

        Returns:
            BrokerClient instance
        """
        client_key = f"{broker.lower()}_{account_name}"

        if client_key in self.clients:
            logger.warning(f"Client {client_key} already exists, returning existing instance")
            return self.clients[client_key]

        # Get credentials if not provided
        if credentials is None:
            credentials = self.credential_manager.get_broker_credentials(broker, account_name)

        # Create client
        client = ClientFactory.create_client(broker, account_name, credentials)
        self.clients[client_key] = client

        logger.info(f"Added client: {client_key}")
        return client

    def get_client(self, broker: str, account_name: str) -> Optional[BrokerClient]:
        """
        Get a client by broker and account name

        Args:
            broker: Broker name
            account_name: Account name

        Returns:
            BrokerClient instance or None
        """
        client_key = f"{broker.lower()}_{account_name}"
        return self.clients.get(client_key)

    def remove_client(self, broker: str, account_name: str) -> bool:
        """
        Remove a client from the manager

        Args:
            broker: Broker name
            account_name: Account name

        Returns:
            True if client was removed
        """
        client_key = f"{broker.lower()}_{account_name}"

        if client_key in self.clients:
            client = self.clients[client_key]
            try:
                client.logout()
            except Exception as e:
                logger.error(f"Error logging out client {client_key}: {e}")

            del self.clients[client_key]
            logger.info(f"Removed client: {client_key}")
            return True

        return False

    def login_all(self) -> Dict[str, bool]:
        """
        Login all clients

        Returns:
            Dictionary of client_key -> login_success
        """
        results = {}

        for client_key, client in self.clients.items():
            try:
                results[client_key] = client.login()
            except Exception as e:
                logger.error(f"Failed to login {client_key}: {e}")
                results[client_key] = False

        return results

    def logout_all(self) -> Dict[str, bool]:
        """
        Logout all clients

        Returns:
            Dictionary of client_key -> logout_success
        """
        results = {}

        for client_key, client in self.clients.items():
            try:
                results[client_key] = client.logout()
            except Exception as e:
                logger.error(f"Failed to logout {client_key}: {e}")
                results[client_key] = False

        return results

    def get_all_clients(self) -> List[BrokerClient]:
        """Get all registered clients"""
        return list(self.clients.values())

    def get_authenticated_clients(self) -> List[BrokerClient]:
        """Get all authenticated clients"""
        return [client for client in self.clients.values() if client.is_authenticated()]
