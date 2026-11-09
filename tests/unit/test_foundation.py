import unittest
import sys
import tempfile
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe import __version__
from cryptosafe.config import APP_NAME, APP_MODE, BASE_DIR
from cryptosafe.common.errors import CryptoSafeError, AuthenticationError, CryptoOperationError, ValidationError
from cryptosafe.common.logging_config import setup_logging
from cryptosafe.app import init_app

class TestM0Foundation(unittest.TestCase):
    def test_version_and_metadata(self):
        self.assertEqual(__version__, "0.1.0")
        self.assertEqual(APP_NAME, "CRYPTOSAFE")
        self.assertEqual(APP_MODE, "DEMO")
        self.assertTrue(BASE_DIR.exists())

    def test_custom_exceptions_hierarchy(self):
        self.assertTrue(issubclass(AuthenticationError, CryptoSafeError))
        self.assertTrue(issubclass(CryptoOperationError, CryptoSafeError))
        self.assertTrue(issubclass(ValidationError, CryptoSafeError))

    def test_logging_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_log_file = Path(temp_dir) / "test.log"
            logger = setup_logging(log_file=temp_log_file, force=True)
            self.assertIsNotNone(logger)
            logger.info("Test message")
            self.assertTrue(temp_log_file.exists())
            with open(temp_log_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Test message", content)
            # Clean up handlers so tempdir can be deleted on Windows
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

    def test_app_init(self):
        exit_code = init_app()
        self.assertEqual(exit_code, 0)

if __name__ == "__main__":
    unittest.main()
