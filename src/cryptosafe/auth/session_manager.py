"""User authentication session manager."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class UserSession:
    session_id: str
    user_id: int
    username: str
    created_at: datetime

class SessionManager:
    """Manages active user session lifecycle."""

    def __init__(self):
        self._current_session: UserSession | None = None

    def create_session(self, user_id: int, username: str) -> UserSession:
        """Establish a new authenticated user session."""
        session = UserSession(
            session_id=secrets.token_hex(24),
            user_id=user_id,
            username=username,
            created_at=datetime.now(timezone.utc),
        )
        self._current_session = session
        return session

    def get_current_session(self) -> UserSession | None:
        """Retrieve the active session if one exists."""
        return self._current_session

    def terminate_session(self) -> None:
        """Destroy the active session and clear in-memory credentials."""
        self._current_session = None

    def is_authenticated(self) -> bool:
        """Return True if an active authenticated session exists."""
        return self._current_session is not None

