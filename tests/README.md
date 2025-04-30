# Unit Tests for Sourcerer

This directory contains unit tests for the Sourcerer project, focusing on the infrastructure layer.

## Test Structure

The test directory structure mirrors the structure of the `src/sourcerer/infrastructure` directory:

```
tests/
├── infrastructure/
│   ├── access_credentials/
│   │   ├── test_registry.py
│   │   └── test_repositories.py
│   ├── db/
│   │   └── test_models.py
│   ├── file_system/
│   │   └── test_services.py
│   └── storage_provider/
│       └── test_registry.py
```


This will make the `sourcerer` package importable in your Python environment.

## Running Tests

To run coverage:

```bash
coverage run -m unittest discover
```

To export coverage report:

```bash
coverage html && open htmlcov/index.html
```


## Mocking Strategy

The tests use the `unittest.mock` library to mock external dependencies:

- Database sessions are mocked to avoid actual database operations
- File system operations are mocked to avoid actual file system changes
- Datetime functions are mocked for deterministic timestamp testing

## Adding New Tests

When adding new tests:

1. Follow the existing directory structure
2. Use the `unittest` framework
3. Follow the Arrange-Act-Assert pattern
4. Mock external dependencies
5. Include both success and error cases
