import unittest
from unittest.mock import MagicMock, patch

from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.storage_provider.registry import (
    StorageProviderRegistry,
    storage_provider,
    storage_provider_registry
)


class TestStorageProviderRegistry(unittest.TestCase):
    """Test cases for StorageProviderRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset the registry singleton for each test
        StorageProviderRegistry._instance = None
        self.registry = StorageProviderRegistry()
        
        # Create a mock service class
        self.mock_service_class = MagicMock(spec=BaseStorageProviderService)
        
        # Test provider identifier
        self.test_provider = "test-provider"

    def test_singleton_pattern(self):
        """Test that the registry follows the singleton pattern."""
        # Create two instances
        registry1 = StorageProviderRegistry()
        registry2 = StorageProviderRegistry()
        
        # They should be the same object
        self.assertIs(registry1, registry2)
        
        # They should be the same as the instance created in setUp
        self.assertIs(self.registry, registry1)

    def test_register_and_get(self):
        """Test registering and retrieving a service class."""
        # Register a service class
        self.registry.register(self.test_provider, self.mock_service_class)
        
        # Get all registered services
        all_services = self.registry.get()
        
        # Verify the service was registered
        self.assertIn(self.test_provider, all_services)
        self.assertEqual(all_services[self.test_provider], self.mock_service_class)

    def test_get_by_provider(self):
        """Test retrieving a service by provider."""
        # Register a service class
        self.registry.register(self.test_provider, self.mock_service_class)
        
        # Get the service by provider
        service = self.registry.get_by_provider(self.test_provider)
        
        # Verify the service was retrieved
        self.assertEqual(service, self.mock_service_class)
        
        # Test with a non-existent provider
        non_existent_service = self.registry.get_by_provider("non-existent")
        self.assertIsNone(non_existent_service)

    def test_decorator(self):
        """Test the storage_provider decorator."""
        # Define a test class
        class TestService(BaseStorageProviderService):
            pass
        
        # Apply the decorator
        decorated_class = storage_provider(self.test_provider)(TestService)
        
        # Verify the class was registered
        service = storage_provider_registry.get_by_provider(self.test_provider)
        
        self.assertEqual(service, TestService)


if __name__ == "__main__":
    unittest.main()