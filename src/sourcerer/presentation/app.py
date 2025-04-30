"""Main application module for the Sourcerer application.

This module initializes the dependency injection container, sets up the database,
and runs the main application window.
"""

from sourcerer.infrastructure.access_credentials.registry import (
    access_credential_method_registry,
)
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.main.main import Sourcerer


def main():
    """Initialize and run the Sourcerer application.

    This function:
    1. Creates and configures the dependency injection container
    2. Sets up the access credential method registry
    3. Prepares the database
    4. Creates and runs the main application window
    """
    di_container = DiContainer()
    di_container.config.access_credential_method_registry.from_value(
        access_credential_method_registry
    )
    di_container.wire(packages=["sourcerer"])

    DiContainer.db().prepare_db()

    app = Sourcerer()
    app.run()


if __name__ == "__main__":
    main()
