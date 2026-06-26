"""SqlPrompts: PromptSource backed by a SQL table via SQLAlchemy. Requires pip install pypromptr[sql]."""

from __future__ import annotations

import json
from typing import Any

from pypromptr._parsing import _MinimalMetadata
from pypromptr.prompts import MessagesPrompt, SimplePrompt, SimplePromptTemplate


def _import_sqlalchemy():
    try:
        from sqlalchemy import create_engine, text
        return create_engine, text
    except ImportError as e:
        raise ImportError("Install SQL support with: pip install pypromptr[sql]") from e


class SqlPrompts:
    """PromptSource that queries prompts from a SQL table via SQLAlchemy (lazy)."""

    def __init__(
        self,
        url: str | None = None,
        *,
        engine: Any = None,
        table: str = "prompts",
        key_column: str = "key",
        content_column: str = "content",
        metadata_column: str = "metadata",
        where: dict[str, Any] | None = None,
    ) -> None:
        if engine is not None:
            self._engine = engine
        elif url is not None:
            create_engine, _ = _import_sqlalchemy()
            self._engine = create_engine(url, future=True)
        else:
            raise ValueError("Either url or engine must be provided")
        self._table = table
        self._key_column = key_column
        self._content_column = content_column
        self._metadata_column = metadata_column
        self._where = where  # dict of column → value for simple equality filters

    def _build_where_clause(self) -> str:
        """Build a WHERE clause from the where dict (equality conditions only)."""
        if not self._where:
            return ""
        conditions = " AND ".join(f"{col} = :{col}" for col in self._where)
        return f" WHERE {conditions}"

    def _where_params(self) -> dict[str, Any]:
        return dict(self._where) if self._where else {}

    def keys(self) -> list[str]:
        """Return all prompt keys matching the where filter."""
        _, text = _import_sqlalchemy()
        where_clause = self._build_where_clause()
        sql = text(f"SELECT {self._key_column} FROM {self._table}{where_clause}")
        params = self._where_params()
        with self._engine.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [row[0] for row in rows]

    def get_prompt(self, key: str) -> SimplePrompt | SimplePromptTemplate | MessagesPrompt:
        """Fetch and parse the prompt for key. Raises KeyError if no row found."""
        _, text = _import_sqlalchemy()
        where_clause = self._build_where_clause()
        key_condition = f"{self._key_column} = :__key"
        if where_clause:
            full_where = f"{where_clause} AND {key_condition}"
        else:
            full_where = f" WHERE {key_condition}"
        sql = text(
            f"SELECT {self._content_column}, {self._metadata_column} "
            f"FROM {self._table}{full_where}"
        )
        params = {**self._where_params(), "__key": key}
        with self._engine.connect() as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None:
            raise KeyError(key)
        content, metadata_json = row[0], row[1]
        # Parse metadata from JSON column
        if metadata_json:
            try:
                meta_dict = json.loads(metadata_json)
            except (json.JSONDecodeError, TypeError):
                meta_dict = {}
        else:
            meta_dict = {}
        metadata = _MinimalMetadata.model_validate(meta_dict)
        # Detect template by presence of {{ placeholder syntax
        if "{{" in content:
            return SimplePromptTemplate(metadata=metadata, content=content)
        return SimplePrompt(metadata=metadata, content=content)
