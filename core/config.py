"""
Configuration Management Module
Provides centralized configuration management with environment-specific configs
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from .error_handler import ConfigurationError
from .logging_config import get_logger

logger = get_logger('pyportman.config')


class Environment(Enum):
    """Environment enumeration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class BrokerConfig:
    """Broker-specific configuration"""
    enabled: bool = True
    rate_limit: int = 50  # API calls per minute
    timeout: int = 30  # Request timeout in seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_cache: bool = True
    cache_duration: int = 300  # Cache duration in seconds


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "logs"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_key: Optional[str] = None
    enable_totp: bool = True
    session_timeout: int = 3600  # Session timeout in seconds
    max_login_attempts: int = 3
    password_min_length: int = 8


@dataclass
class AlertConfig:
    """Alert configuration"""
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_enabled: bool = False
    discord_webhook_url: Optional[str] = None
    email_enabled: bool = False
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None


@dataclass
class PyPortManConfig:
    """Main configuration class"""
    environment: str = "development"
    debug: bool = False

    # Broker configurations
    zerodha: BrokerConfig = field(default_factory=BrokerConfig)
    angel: BrokerConfig = field(default_factory=BrokerConfig)

    # Other configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    # General settings
    workspace_dir: str = "."
    data_dir: str = "data"
    enable_async: bool = False
    max_concurrent_requests: int = 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PyPortManConfig':
        """Create configuration from dictionary"""
        # Handle nested configs
        broker_configs = {
            'zerodha': BrokerConfig(**data.get('zerodha', {})),
            'angel': BrokerConfig(**data.get('angel', {}))
        }

        return cls(
            environment=data.get('environment', 'development'),
            debug=data.get('debug', False),
            zerodha=broker_configs.get('zerodha', BrokerConfig()),
            angel=broker_configs.get('angel', BrokerConfig()),
            logging=LoggingConfig(**data.get('logging', {})),
            security=SecurityConfig(**data.get('security', {})),
            alerts=AlertConfig(**data.get('alerts', {})),
            workspace_dir=data.get('workspace_dir', '.'),
            data_dir=data.get('data_dir', 'data'),
            enable_async=data.get('enable_async', False),
            max_concurrent_requests=data.get('max_concurrent_requests', 10)
        )


class ConfigManager:
    """
    Configuration manager for pyPortMan
    Handles loading, saving, and managing configuration
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Directory for configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config: Optional[PyPortManConfig] = None
        self._environment = self._detect_environment()

    def _get_default_config_dir(self) -> Path:
        """Get default configuration directory"""
        # Try common locations
        possible_dirs = [
            Path.cwd() / 'config',
            Path.cwd() / '.pyportman',
            Path.home() / '.pyportman'
        ]

        for dir_path in possible_dirs:
            if dir_path.exists():
                return dir_path

        # Create default in home directory
        default_dir = Path.home() / '.pyportman'
        default_dir.mkdir(exist_ok=True)
        return default_dir

    def _detect_environment(self) -> str:
        """Detect current environment"""
        env = os.getenv('PYPORTMAN_ENV', os.getenv('ENVIRONMENT', 'development'))
        return env.lower()

    def get_config_file_path(self, environment: Optional[str] = None) -> Path:
        """
        Get configuration file path for environment

        Args:
            environment: Environment name (default: detected environment)

        Returns:
            Path to configuration file
        """
        env = environment or self._environment
        return self.config_dir / f'config.{env}.json'

    def load_config(self, environment: Optional[str] = None) -> PyPortManConfig:
        """
        Load configuration from file

        Args:
            environment: Environment name (default: detected environment)

        Returns:
            PyPortManConfig instance
        """
        config_file = self.get_config_file_path(environment)

        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            return self._get_default_config()

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)

            self._config = PyPortManConfig.from_dict(data)
            logger.info(f"Loaded configuration from {config_file}")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
            return self._get_default_config()

    def save_config(self, config: PyPortManConfig, environment: Optional[str] = None) -> None:
        """
        Save configuration to file

        Args:
            config: Configuration to save
            environment: Environment name (default: detected environment)
        """
        config_file = self.get_config_file_path(environment)

        try:
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)

            # Set restrictive permissions
            os.chmod(config_file, 0o600)
            logger.info(f"Configuration saved to {config_file}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save config: {e}")

    def get_config(self) -> PyPortManConfig:
        """
        Get current configuration (lazy load)

        Returns:
            PyPortManConfig instance
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload_config(self) -> PyPortManConfig:
        """
        Reload configuration from file

        Returns:
            PyPortManConfig instance
        """
        self._config = None
        return self.get_config()

    def _get_default_config(self) -> PyPortManConfig:
        """Get default configuration"""
        return PyPortManConfig(
            environment=self._environment,
            debug=self._environment == 'development'
        )

    def get_broker_config(self, broker: str) -> BrokerConfig:
        """
        Get broker-specific configuration

        Args:
            broker: Broker name (zerodha, angel, etc.)

        Returns:
            BrokerConfig instance
        """
        config = self.get_config()
        broker_lower = broker.lower()

        if broker_lower == 'zerodha':
            return config.zerodha
        elif broker_lower == 'angel':
            return config.angel
        else:
            return BrokerConfig()

    def update_broker_config(self, broker: str, **kwargs) -> None:
        """
        Update broker-specific configuration

        Args:
            broker: Broker name
            **kwargs: Configuration parameters to update
        """
        config = self.get_config()
        broker_lower = broker.lower()

        if broker_lower == 'zerodha':
            for key, value in kwargs.items():
                setattr(config.zerodha, key, value)
        elif broker_lower == 'angel':
            for key, value in kwargs.items():
                setattr(config.angel, key, value)

        self.save_config(config)

    def create_example_configs(self) -> None:
        """Create example configuration files for all environments"""
        for env in Environment:
            config = PyPortManConfig(
                environment=env.value,
                debug=env.value == 'development'
            )

            config_file = self.get_config_file_path(env.value)
            self.save_config(config, env.value)
            logger.info(f"Created example config: {config_file}")


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """
    Get global configuration manager instance

    Args:
        config_dir: Optional configuration directory

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        config_dir = config_dir or os.getenv('PYPORTMAN_CONFIG_DIR')
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_config() -> PyPortManConfig:
    """
    Get current configuration

    Returns:
        PyPortManConfig instance
    """
    return get_config_manager().get_config()


def reload_config() -> PyPortManConfig:
    """
    Reload configuration from file

    Returns:
        PyPortManConfig instance
    """
    return get_config_manager().reload_config()


if __name__ == "__main__":
    # Test configuration management
    manager = ConfigManager()
    manager.create_example_configs()

    # Load and display configuration
    config = manager.get_config()
    print(f"Environment: {config.environment}")
    print(f"Debug: {config.debug}")
    print(f"Zerodha rate limit: {config.zerodha.rate_limit}")
    print(f"Angel rate limit: {config.angel.rate_limit}")
