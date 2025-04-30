import unittest
from unittest.mock import MagicMock, patch

from sourcerer.domain.access_credentials.services import BaseAccessCredentialsService
from sourcerer.infrastructure.access_credentials.registry import (
    AccessCredentialsRegistry,
    AccessCredentialsMethod,
    access_credentials_method,
    access_credential_method_registry
)


class TestAccessCredentialsRegistry(unittest.TestCase):
    """Test cases for AccessCredentialsRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset the registry singleton for each test
        AccessCredentialsRegistry._instance = None
        self.registry = AccessCredentialsRegistry()
        
        # Create a mock service class
        self.mock_service_class = MagicMock(spec=BaseAccessCredentialsService)
        
        # Create a test method descriptor
        self.test_method = AccessCredentialsMethod(
            provider="test-provider",
            name="test-method"
        )

    def test_singleton_pattern(self):
        """Test that the registry follows the singleton pattern."""
        # Create two instances
        registry1 = AccessCredentialsRegistry()
        registry2 = AccessCredentialsRegistry()
        
        # They should be the same object
        self.assertIs(registry1, registry2)
        
        # They should be the same as the instance created in setUp
        self.assertIs(self.registry, registry1)

    def test_register_and_get(self):
        """Test registering and retrieving a service class."""
        # Register a service class
        self.registry.register(self.test_method, self.mock_service_class)
        
        # Get all registered services
        all_services = self.registry.get()
        
        # Verify the service was registered
        self.assertIn(self.test_method.provider, all_services)
        self.assertIn(self.test_method.name, all_services[self.test_method.provider])
        self.assertEqual(all_services[self.test_method.provider][self.test_method.name], self.mock_service_class)

    def test_get_by_provider(self):
        """Test retrieving services by provider."""
        # Register a service class
        self.registry.register(self.test_method, self.mock_service_class)
        
        # Get services for the provider
        provider_services = self.registry.get_by_provider(self.test_method.provider)
        
        # Verify the service was retrieved
        self.assertIn(self.test_method.name, provider_services)
        self.assertEqual(provider_services[self.test_method.name], self.mock_service_class)
        
        # Test with a non-existent provider
        non_existent_provider = self.registry.get_by_provider("non-existent")
        self.assertIsNone(non_existent_provider)

    def test_get_by_provider_and_name(self):
        """Test retrieving a service by provider and name."""
        # Register a service class
        self.registry.register(self.test_method, self.mock_service_class)
        
        # Get the service by provider and name
        service = self.registry.get_by_provider_and_name(
            self.test_method.provider,
            self.test_method.name
        )
        
        # Verify the service was retrieved
        self.assertEqual(service, self.mock_service_class)
        
        # Test with a non-existent provider
        non_existent_service = self.registry.get_by_provider_and_name(
            "non-existent",
            self.test_method.name
        )
        self.assertIsNone(non_existent_service)
        
        # Test with a non-existent name
        non_existent_service = self.registry.get_by_provider_and_name(
            self.test_method.provider,
            "non-existent"
        )
        self.assertIsNone(non_existent_service)

    def test_decorator(self):
        """Test the access_credentials_method decorator."""
        # Define a test class
        class TestService(BaseAccessCredentialsService):
            pass
        
        # Apply the decorator
        decorated_class = access_credentials_method(self.test_method)(TestService)
        
        # Verify the class was registered
        service = access_credential_method_registry.get_by_provider_and_name(
            self.test_method.provider,
            self.test_method.name
        )
        
        self.assertEqual(service, TestService)


if __name__ == "__main__":
    unittest.main()