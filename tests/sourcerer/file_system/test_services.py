import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from sourcerer.infrastructure.file_system.services import FileSystemService
from sourcerer.infrastructure.file_system.exceptions import (
    FileSystemGrepException,
    ReadFileException,
    ListDirException,
    CreateFileException,
    CreateDirException,
    DeleteFileException,
    DeleteDirException,
    MoveFileException,
)


class TestFileSystemService(unittest.TestCase):
    """Test cases for FileSystemService."""

    def setUp(self):
        """Set up test fixtures."""
        self.work_dir = Path("/test/work/dir")
        self.service = FileSystemService(self.work_dir)

    @patch("sourcerer.infrastructure.file_system.services.Path.exists")
    @patch("sourcerer.infrastructure.file_system.services.Path.read_text")
    def test_read(self, mock_read_text, mock_exists):
        """Test read method."""
        # Arrange
        test_path = self.work_dir / "test.txt"
        mock_exists.return_value = True
        mock_read_text.return_value = 'test content'

        
        # Act
        content = self.service.read(test_path)
        
        # Assert
        mock_read_text.assert_called_once()
        self.assertEqual(content, "test content")

    @patch("builtins.open")
    def test_read_error(self, mock_file):
        """Test read method with error."""
        # Arrange
        test_path = self.work_dir / "test.txt"
        mock_file.side_effect = Exception("File not found")
        
        # Act & Assert
        with self.assertRaises(ReadFileException):
            self.service.read(test_path)

    @patch("sourcerer.infrastructure.file_system.services.Path.is_dir")
    @patch("sourcerer.infrastructure.file_system.services.Path.exists")
    @patch("sourcerer.infrastructure.file_system.services.Path.iterdir")
    def test_list_dir(self, mock_iterdir, mock_exists, mock_is_dir):
        """Test list_dir method."""
        # Arrange
        test_path = self.work_dir / "test_dir"
        mock_is_dir.return_value = True
        mock_exists.return_value = True

        file1 = MagicMock()
        file1.is_file.return_value = True
        file1.is_dir.return_value = False
        file1.name = "file1.txt"
        
        dir1 = MagicMock()
        dir1.is_file.return_value = False
        dir1.is_dir.return_value = True
        dir1.name = "dir1"
        
        mock_iterdir.return_value = [file1, dir1]
        
        # Act
        result = self.service.list_dir(test_path)
        
        # Assert
        mock_iterdir.assert_called_once()
        self.assertEqual(len(result.directories), 1)
        self.assertEqual(len(result.files), 1)
        self.assertEqual(result.directories[0].name, "dir1")  # Directories should come first
        self.assertEqual(result.files[0].name, "file1.txt")

    @patch("sourcerer.infrastructure.file_system.services.Path.is_dir")
    def test_list_dir_error(self, mock_is_dir):
        """Test list_dir method with error."""
        # Arrange
        test_path = self.work_dir / "test_dir"
        mock_is_dir.side_effect = Exception("Directory not found")
        
        # Act & Assert
        with self.assertRaises(ListDirException):
            self.service.list_dir(test_path)


if __name__ == "__main__":
    unittest.main()