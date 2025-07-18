import unittest
from unittest.mock import patch

from sourcerer.infrastructure.utils import generate_unique_name


class TestGenerateUniqueName(unittest.TestCase):
    def test_returns_non_empty_string(self):
        result = generate_unique_name()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_format_adjective_name(self):
        result = generate_unique_name()
        self.assertRegex(result, r"^[a-z]+_[a-z]+$")

    @patch("sourcerer.infrastructure.utils.secrets.choice")
    def test_deterministic_output_with_mock(self, mock_choice):
        mock_choice.side_effect = ["mighty", "phoenix"]
        result = generate_unique_name()
        self.assertEqual(result, "mighty_phoenix")
