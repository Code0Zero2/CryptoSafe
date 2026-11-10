"""Application domain and infrastructure exceptions."""

class CryptoSafeError(Exception):
    """Base exception for all CRYPTOSAFE application errors."""
    pass

class AuthenticationError(CryptoSafeError):
    """Raised when authentication fails."""
    pass

class AuthenticationCancelledError(CryptoSafeError):
    """Raised when an interactive authentication step is cancelled by user."""
    pass

class CryptoOperationError(CryptoSafeError):
    """Raised when encryption, decryption, or verification fails."""
    pass

class ValidationError(CryptoSafeError):
    """Raised when user or data input validation fails."""
    pass

