import uuid
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from app.config import settings


class PostgreSQLStore:
    """
    Kalıcı analiz saklama sistemi.
    memory_store.py ile aynı arayüz — main.py değişmez.
    """

    def __init__(self):
        self._engine = create_engine(settings.database_url)
        self._create_table()

    def _create_table(self):
        """Tablo yoksa oluştur."""
        with self._engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id          VARCHAR(36) PRIMARY KEY,
                    created_at  TIMESTAMP NOT NULL,
                    result      JSONB NOT NULL
                )
            """))
            conn.commit()

    def save(self, result: dict) -> str:
        analysis_id = str(uuid.uuid4())
        created_at  = datetime.utcnow()

        with self._engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO analyses (id, created_at, result)
                    VALUES (:id, :created_at, :result)
                """),
                {
                    "id":         analysis_id,
                    "created_at": created_at,
                    "result":     json.dumps(result),
                }
            )
            conn.commit()

        return analysis_id

    def get(self, analysis_id: str) -> Optional[dict]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT result FROM analyses WHERE id = :id"),
                {"id": analysis_id}
            ).fetchone()

        if not row:
            return None

        data = row[0]
        return data if isinstance(data, dict) else json.loads(data)

    def list(self, limit: int = 10) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, created_at, result FROM analyses ORDER BY created_at DESC LIMIT :limit"),
                {"limit": limit}
            ).fetchall()

        results = []
        for row in rows:
            data = row[2]
            if isinstance(data, str):
                data = json.loads(data)
            results.append({
                "id":         row[0],
                "created_at": row[1].isoformat(),
                **data,
            })
        return results

    def delete(self, analysis_id: str) -> bool:
        with self._engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM analyses WHERE id = :id"),
                {"id": analysis_id}
            )
            conn.commit()
        return result.rowcount > 0

    def clear(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(text("DELETE FROM analyses"))
            conn.commit()

    def count(self) -> int:
        with self._engine.connect() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM analyses")).fetchone()
        return row[0] if row else 0