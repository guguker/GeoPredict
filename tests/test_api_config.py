import os
import unittest
from unittest.mock import patch

from api.analyze import DEFAULT_CORS_ORIGINS, get_cors_origins


class ApiConfigTest(unittest.TestCase):
    def test_default_cors_origins_include_local_frontend(self):
        with patch.dict(os.environ, {}, clear=True):
            origins = get_cors_origins()

        self.assertEqual(origins, list(DEFAULT_CORS_ORIGINS))
        self.assertIn("http://localhost:3000", origins)

    def test_cors_origins_can_be_configured_from_env(self):
        with patch.dict(
            os.environ,
            {"GEOPREDICT_CORS_ORIGINS": "http://localhost:8080, https://example.com "},
        ):
            origins = get_cors_origins()

        self.assertEqual(origins, ["http://localhost:8080", "https://example.com"])


if __name__ == "__main__":
    unittest.main()
