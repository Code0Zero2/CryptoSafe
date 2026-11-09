"""Face biometric profiles repository using SQLite."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class FaceProfile:
    id: int
    user_id: int
    encrypted_template: str
    model_name: str
    model_version: str
    created_at: str
    consent_recorded_at: str
    revoked_at: str | None

class FaceRepository:
    """Repository handling persistence of encrypted face templates."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_profile(
        self,
        user_id: int,
        encrypted_template: str,
        model_name: str,
        model_version: str,
        consent_recorded_at: str,
    ) -> FaceProfile:
        """Store a new face profile for a user, revoking any prior active profile."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                "UPDATE face_profiles SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso, user_id)
            )
            cursor = self._conn.execute(
                """
                INSERT INTO face_profiles (
                    user_id, encrypted_template, model_name, model_version,
                    created_at, consent_recorded_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (user_id, encrypted_template, model_name, model_version, now_iso, consent_recorded_at)
            )
            profile_id = cursor.lastrowid
            return FaceProfile(
                id=profile_id,
                user_id=user_id,
                encrypted_template=encrypted_template,
                model_name=model_name,
                model_version=model_version,
                created_at=now_iso,
                consent_recorded_at=consent_recorded_at,
                revoked_at=None,
            )

    def get_active_by_user_id(self, user_id: int) -> FaceProfile | None:
        """Retrieve active face profile for a user."""
        cursor = self._conn.execute(
            """
            SELECT id, user_id, encrypted_template, model_name, model_version,
                   created_at, consent_recorded_at, revoked_at
            FROM face_profiles
            WHERE user_id = ? AND revoked_at IS NULL
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return FaceProfile(
            id=row["id"],
            user_id=row["user_id"],
            encrypted_template=row["encrypted_template"],
            model_name=row["model_name"],
            model_version=row["model_version"],
            created_at=row["created_at"],
            consent_recorded_at=row["consent_recorded_at"],
            revoked_at=row["revoked_at"],
        )

    def revoke_by_user_id(self, user_id: int) -> bool:
        """Revoke active face profile for user."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE face_profiles SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso, user_id)
            )
            return cursor.rowcount > 0
