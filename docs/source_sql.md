# Design: SqlPrompts

## Motivation

Teams already running a relational database often want to store prompts there too — alongside the rest of their application data. Benefits:

- Versioning via a `version` column or audit table
- A/B variants selectable via SQL
- Managed access control through existing DB roles
- No extra infrastructure

Works with any SQLAlchemy-supported database: PostgreSQL, MySQL, SQLite, and others.

## Optional dependency

```bash
pip install pypromptr[sql]
# adds: sqlalchemy
```

## Interface

```python
from pypromptr.sql_source import SqlPrompts

source = SqlPrompts(
    url="postgresql+psycopg2://user:pass@localhost/mydb",
    # OR pass an existing engine/connection
    engine=my_engine,

    table="prompts",           # table name; default: "prompts"
    key_column="key",          # column holding the prompt key; default: "key"
    content_column="content",  # column holding the prompt body; default: "content"
    metadata_column="metadata",# JSON column for metadata; default: "metadata" (nullable)
    where=None,                # optional SQLAlchemy clause for filtering, e.g. active=True
)
```

## Expected schema

```sql
CREATE TABLE prompts (
    key      TEXT PRIMARY KEY,
    content  TEXT NOT NULL,
    metadata JSONB             -- nullable; use NULL or {} if not needed
);
```

Columns beyond these are ignored. The schema is intentionally minimal — teams add `version`, `environment`, `created_at` etc. to suit their needs, using `where` to filter.

## Behaviour

### `keys() -> list[str]`
`SELECT key FROM {table} [WHERE ...]`. Returns all matching keys. Called at init.

### `get_prompt(key: str) -> PromptLike`
`SELECT content, metadata FROM {table} WHERE key = :key [AND ...]`. Raises `KeyError(key)` if no row is found. Parses `content` as a prompt template if it contains `{{` (same heuristic as `FilePrompts`), otherwise as a `SimplePrompt`.

## Notes

- Uses a connection pool via SQLAlchemy engine; connection management is handled by SQLAlchemy.
- `where` enables multi-tenant or multi-environment setups from a single table: `where=and_(col("env") == "prod", col("active") == True)`.
- No ORM models — raw `select()` statements only, to avoid coupling to any specific model layer.
- Thread-safe; SQLAlchemy connection pools are designed for concurrent use.
- No file-watcher; prompt updates are read on the next `get_prompt` call (no caching by default).

## Example

```python
from pypromptr import PromptRegistry
from pypromptr.sql_source import SqlPrompts

registry = PromptRegistry(
    SqlPrompts("postgresql+psycopg2://user:pass@db/app", table="prompts"),
)
rendered = registry.get("welcome-email", user="Alice")
```

### With filtering (multi-environment)

```python
from sqlalchemy import column

source = SqlPrompts(
    engine=my_engine,
    where=(column("environment") == "production") & (column("active") == True),
)
```
