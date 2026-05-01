"""
Unit tests for configuration management
"""

import pytest
import json
import os
from pathlib import Path
from pyportman import (
    ConfigManager,
    PyPortManConfig,
    BrokerConfig,
    LoggingConfig,
    SecurityConfig,
    AlertConfig,
    Environment,
    ConfigurationError
)


class TestConfigManager:
    """Test cases for ConfigManager"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigManager instance"""
        return ConfigManager(str(temp_config_dir))

    def test_config_manager_initialization(self, config_manager):
        """Test ConfigManager initialization"""
        assert config_manager.config_dir.exists()
        assert config_manager._environment in ['development', 'staging', 'production', 'test']

    def test_get_default_config(self, config_manager):
        """Test getting default configuration"""
        config = config_manager._get_default_config()
        assert isinstance(config, PyPortManConfig)
        assert config.environment == config_manager._environment

    def test_save_and_load_config(self, config_manager):
        """Test saving and loading configuration"""
        config = PyPortManConfig(
            environment='test',
            debug=True,
            zerodha=BrokerConfig(rate_limit=100),
            logging=LoggingConfig(level='DEBUG')
        )

        config_manager.save_config(config)
        loaded_config = config_manager.load_config()

        assert loaded_config.environment == 'test'
        assert loaded_config.debug is True
        assert loaded_config.zerodha.rate_limit == 100
        assert loaded_config.logging.level == 'DEBUG'

    def test_get_config_file_path(self, config_manager):
        """Test getting config file path"""
        path = config_manager.get_config_file_path('development')
        assert path.name == 'config.development.json'
        assert path.parent == config_manager.config_dir

    def test_get_broker_config(self, config_manager):
        """Test getting broker-specific configuration"""
        config = PyPortManConfig(
            zerodha=BrokerConfig(rate_limit=100),
            angel=BrokerConfig(rate_limit=50)
        )
        config_manager._config = config

        zerodha_config = config_manager.get_broker_config('zerodha')
        assert zerodha_config.rate_limit == 100

        angel_config = config_manager.get_broker_config('angel')
        assert angel_config.rate_limit == 50

    def test_update_broker_config(self, config_manager):
        """Test updating broker configuration"""
        config = PyPortManConfig()
        config_manager._config = config

        config_manager.update_broker_config('zerodha', rate_limit=200, timeout=60)

        assert config.zerodha.rate_limit == 200
        assert config.zerodha.timeout == 60

    def test_create_example_configs(self, config_manager):
        """Test creating example configuration files"""
        config_manager.create_example_configs()

        for env in Environment:
            config_file = config_manager.get_config_file_path(env.value)
            assert config_file.exists()

            # Verify it's valid JSON
            with open(config_file, 'r') as f:
                data = json.load(f)
                assert data['environment'] == env.value

    def test_config_to_dict(self):
        """Test converting configuration to dictionary"""
        config = PyPortManConfig(
            environment='test',
            debug=True,
            zerodha=BrokerConfig(rate_limit=100)
        )

        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict['environment'] == 'test'
        assert config_dict['debug'] is True
        assert config_dict['zerodha']['rate_limit'] == 100

    def test_config_from_dict(self):
        """Test creating configuration from dictionary"""
        data = {
            'environment': 'test',
            'debug': True,
            'zerodha': {'rate_limit': 100},
            'angel': {'rate_limit': 50},
            'logging': {'level': 'DEBUG'},
            'security': {'enable_totp': True},
            'alerts': {'telegram_enabled': False}
        }

        config = PyPortManConfig.from_dict(data)
        assert config.environment == 'test'
        assert config.debug is True
        assert config.zerodha.rate_limit == 100
        assert config.angel.rate_limit == 50
        assert config.logging.level == 'DEBUG'
        assert config.security.enable_totp is True
        assert config.alerts.telegram_enabled is False

    def test_reload_config(self, config_manager):
        """Test reloading configuration"""
        config = PyPortManConfig(environment='test')
        config_manager.save_config(config)

        # Modify config
        config_manager._config.debug = True

        # Reload
        reloaded = config_manager.reload_config()
        assert reloaded.debug is False  # Should be False from saved config


class TestBrokerConfig:
    """Test cases for BrokerConfig"""

    def test_broker_config_defaults(self):
        """Test BrokerConfig default values"""
        config = BrokerConfig()
        assert config.enabled is True
        assert config.rate_limit == 50
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.enable_cache is True
        assert config.cache_duration == 300

    def test_broker_config_custom(self):
        """Test BrokerConfig with custom values"""
        config = BrokerConfig(
            enabled=False,
            rate_limit=100,
            timeout=60,
            retry_attempts=5,
            retry_delay=2.0,
            enable_cache=False,
            cache_duration=600
        )
        assert config.enabled is False
        assert config.rate_limit == 100
        assert config.timeout == 60
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0
        assert config.enable_cache is False
        assert config.cache_duration == 600


class TestLoggingConfig:
    """Test cases for LoggingConfig"""

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.log_to_file is True
        assert config.log_dir == "logs"
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.backup_count == 5

    def test_logging_config_custom(self):
        """Test LoggingConfig with custom values"""
        config = LoggingConfig(
            level="DEBUG",
            log_to_file=False,
            log_dir="/var/log",
            max_file_size=20 * 1024 * 1024,
            backup_count=10
        )
        assert config.level == "DEBUG"
        assert config.log_to_file is False
        assert config.log_dir == "/var/log"
        assert config.max_file_size == 20 * 1024 * 1024
        assert config.backup_count == 10


class TestSecurityConfig:
    """Test cases for SecurityConfig"""

    def test_security_config_defaults(self):
        """Test SecurityConfig default values"""
        config = SecurityConfig()
        assert config.encryption_key is None
        assert config.enable_totp is True
        assert config.session_timeout == 3600
        assert config.max_login_attempts == 3
        assert config.password_min_length == 8

    def test_security_config_custom(self):
        """Test SecurityConfig with custom values"""
        config = SecurityConfig(
            encryption_key="test_key",
            enable_totp=False,
            session_timeout=7200,
            max_login_attempts=5,
            password_min_length=12
        )
        assert config.encryption_key == "test_key"
        assert config.enable_totp is False
        assert config.session_timeout == 7200
        assert config.max_login_attempts == 5
        assert config.password_min_length == 12


class TestAlertConfig:
    """Test cases for AlertConfig"""

    def test_alert_config_defaults(self):
        """Test AlertConfig default values"""
        config = AlertConfig()
        assert config.telegram_enabled is False
        assert config.telegram_bot_token is None
        assert config.telegram_chat_id is None
        assert config.discord_enabled is False
        assert config.discord_webhook_url is None
        assert config.email_enabled is False
        assert config.email_smtp_port == 587

    def test_alert_config_custom(self):
        """Test AlertConfig with custom values"""
        config = AlertConfig(
            telegram_enabled=True,
            telegram_bot_token="test_token",
            telegram_chat_id="test_chat",
            discord_enabled=True,
            discord_webhook_url="https://discord.com/webhook",
            email_enabled=True,
            email_smtp_server="smtp.example.com",
            email_smtp_port=465,
            email_username="user@example.com",
            email_password="password",
            email_from="noreply@example.com",
            email_to="user@example.com"
        )
        assert config.telegram_enabled is True
        assert config.telegram_bot_token == "test_token"
        assert config.telegram_chat_id == "test_chat"
        assert config.discord_enabled is True
        assert config.discord_webhook_url == "https://discord.com/webhook"
        assert config.email_enabled is True
        assert config.email_smtp_server == "smtp.example.com"
        assert config.email_smtp_port == 465


class TestPyPortManConfig:
    """Test cases for PyPortManConfig"""

    def test_pyportman_config_defaults(self):
        """Test PyPortManConfig default values"""
        config = PyPortManConfig()
        assert config.environment == "development"
        assert config.debug is False
        assert config.workspace_dir == "."
        assert config.data_dir == "data"
        assert config.enable_async is False
        assert config.max_concurrent_requests == 10

    def test_pyportman_config_custom(self):
        """Test PyPortManConfig with custom values"""
        config = PyPortManConfig(
            environment="production",
            debug=True,
            workspace_dir="/workspace",
            data_dir="/data",
            enable_async=True,
            max_concurrent_requests=20
        )
        assert config.environment == "production"
        assert config.debug is True
        assert config.workspace_dir == "/workspace"
        assert config.data_dir == "/data"
        assert config.enable_async is True
        assert config.max_concurrent_requests == 20

    def test_total_value_property(self):
        """Test PortfolioSummary total_value property"""
        from pyportman import PortfolioSummary
        from datetime import datetime

        summary = PortfolioSummary(
            account_name="test",
            broker="zerodha",
            funds_equity=100000,
            funds_commodity=50000,
            total_funds=150000,
            holdings_count=5,
            holdings_value=200000,
            holdings_pnl=10000,
            positions_count=2,
            positions_value=50000,
            positions_pnl=5000,
            total_pnl=15000,
            pending_orders=3,
            timestamp=datetime.now()
        )

        assert summary.total_value == 400000  # funds + holdings + positions


class TestEnvironment:
    """Test cases for Environment enum"""

    def test_environment_values(self):
        """Test Environment enum values"""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TEST.value == "test"

    def test_environment_iteration(self):
        """Test iterating over Environment enum"""
        environments = list(Environment)
        assert len(environments) == 4
        assert Environment.DEVELOPMENT in environments
        assert Environment.STAGING in environments
        assert Environment.PRODUCTION in environments
        assert Environment.TEST in environments
