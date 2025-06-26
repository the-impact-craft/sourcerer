import unittest
from unittest.mock import Mock, patch

from sourcerer.infrastructure.package_meta.services import PackageMetaService


class TestPackageMetaService(unittest.TestCase):
    def test_get_package_meta(self):
        expected_results = [
            ("1.0.0", {"version": "1.0.0"}, False),
            ("1.0.0", {"version": "2.0.0"}, True),
            ("2.0.0", {"version": "1.0.0"}, False),
        ]
        for (
            current_version,
            last_version_response,
            has_available_update,
        ) in expected_results:
            with (
                patch(
                    "sourcerer.utils.requests.get"
                ) as get_last_package_version_request_mock,
                patch(
                    "sourcerer.infrastructure.package_meta.services.__version__",
                    current_version,
                ),
            ):
                mock_response = Mock()
                get_last_package_version_request_mock.return_value = mock_response
                mock_response.json.return_value = {"info": last_version_response}

                service = PackageMetaService()
                meta = service.get_package_meta()
                self.assertEqual(meta.version, current_version)
                self.assertEqual(
                    meta.latest_version, last_version_response.get("version")
                )
                self.assertEqual(meta.has_available_update, has_available_update)
