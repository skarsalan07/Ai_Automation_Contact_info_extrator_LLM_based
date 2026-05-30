"""In-memory store (SQLite removed per user request)."""
from datetime import datetime
from typing import List

from backend.schemas.company import CompanyProfileStored


class _MemoryStore:
    def __init__(self):
        self._rows: List[CompanyProfileStored] = []
        self._next_id = 1

    def add(self, profile_dict: dict, source_url: str) -> CompanyProfileStored:
        row = CompanyProfileStored(
            id=self._next_id,
            source_url=source_url,
            created_at=datetime.utcnow(),
            **profile_dict,
        )
        self._next_id += 1
        self._rows.append(row)
        return row

    def list(self, limit: int = 100, offset: int = 0) -> List[CompanyProfileStored]:
        return list(reversed(self._rows))[offset : offset + limit]


store = _MemoryStore()


def init_db() -> None:
    """No-op kept for compatibility with main.py lifespan."""
    return None
