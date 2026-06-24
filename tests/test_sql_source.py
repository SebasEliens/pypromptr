"""Tests for SqlPrompts. Uses SQLite in-memory engine — requires sqlalchemy."""

import json

import pytest

try:
    from sqlalchemy import create_engine, text

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

pytestmark = pytest.mark.skipif(not HAS_SQLALCHEMY, reason="sqlalchemy not installed")

from pypromptr.sql_source import SqlPrompts
from pypromptr.prompts import SimplePrompt, SimplePromptTemplate


def make_engine_with_data(rows):
    """Create a fresh SQLite in-memory engine and populate the prompts table."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE prompts (key TEXT PRIMARY KEY, content TEXT NOT NULL, metadata TEXT)"
            )
        )
        for row in rows:
            conn.execute(
                text(
                    "INSERT INTO prompts (key, content, metadata) VALUES (:key, :content, :metadata)"
                ),
                row,
            )
    return engine


def test_keys_returns_all_rows():
    engine = make_engine_with_data([
        {"key": "greeting", "content": "Hello!", "metadata": None},
        {"key": "farewell", "content": "Goodbye!", "metadata": None},
    ])
    source = SqlPrompts(engine=engine)
    assert set(source.keys()) == {"greeting", "farewell"}


def test_keys_with_where_filter():
    engine = make_engine_with_data([
        {"key": "prod-prompt", "content": "Prod!", "metadata": json.dumps({"env": "prod"})},
        {"key": "staging-prompt", "content": "Staging!", "metadata": json.dumps({"env": "staging"})},
    ])
    # Add env column to table by rebuilding with extra column
    from sqlalchemy import create_engine as ce, text as t
    eng = ce("sqlite:///:memory:", future=True)
    with eng.begin() as conn:
        conn.execute(t(
            "CREATE TABLE prompts (key TEXT PRIMARY KEY, content TEXT NOT NULL, metadata TEXT, env TEXT)"
        ))
        conn.execute(t("INSERT INTO prompts VALUES ('prod-prompt', 'Prod!', NULL, 'prod')"))
        conn.execute(t("INSERT INTO prompts VALUES ('staging-prompt', 'Staging!', NULL, 'staging')"))
    source = SqlPrompts(engine=eng, where={"env": "prod"})
    assert source.keys() == ["prod-prompt"]


def test_get_prompt_returns_simple_prompt():
    engine = make_engine_with_data([
        {"key": "greeting", "content": "Hello!", "metadata": None},
    ])
    source = SqlPrompts(engine=engine)
    prompt = source.get_prompt("greeting")
    assert isinstance(prompt, SimplePrompt)
    assert prompt.content == "Hello!"


def test_get_prompt_returns_template_when_placeholders_present():
    engine = make_engine_with_data([
        {"key": "tmpl", "content": "Hello, {{name}}!", "metadata": None},
    ])
    source = SqlPrompts(engine=engine)
    prompt = source.get_prompt("tmpl")
    assert isinstance(prompt, SimplePromptTemplate)
    assert "{{name}}" in prompt.content


def test_get_prompt_includes_metadata_from_json_column():
    engine = make_engine_with_data([
        {"key": "meta", "content": "Hi", "metadata": json.dumps({"title": "My Prompt"})},
    ])
    source = SqlPrompts(engine=engine)
    prompt = source.get_prompt("meta")
    assert prompt.metadata.model_extra["title"] == "My Prompt"


def test_get_prompt_raises_key_error_for_unknown_key():
    engine = make_engine_with_data([])
    source = SqlPrompts(engine=engine)
    with pytest.raises(KeyError):
        source.get_prompt("nonexistent")


def test_get_prompt_respects_where_filter():
    from sqlalchemy import create_engine as ce, text as t
    eng = ce("sqlite:///:memory:", future=True)
    with eng.begin() as conn:
        conn.execute(t(
            "CREATE TABLE prompts (key TEXT PRIMARY KEY, content TEXT NOT NULL, metadata TEXT, env TEXT)"
        ))
        conn.execute(t("INSERT INTO prompts VALUES ('p', 'Prod content', NULL, 'prod')"))
        conn.execute(t("INSERT INTO prompts VALUES ('p2', 'Other content', NULL, 'staging')"))
    source = SqlPrompts(engine=eng, where={"env": "prod"})
    # Should find key 'p' for prod
    prompt = source.get_prompt("p")
    assert prompt.content == "Prod content"
    # 'p2' is staging, not visible through this source
    with pytest.raises(KeyError):
        source.get_prompt("p2")
