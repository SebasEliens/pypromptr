"""GitRepoPrompts: PromptSource that reads prompts from a Git repository. Requires pip install pypromptr[git]."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from pypromptr._parsing import parse_prompt_text
from pypromptr.prompts import MessagesPrompt, SimplePrompt


class GitRepoAdapter(Protocol):
    """Port for git repository access. Implement to swap out gitpython in tests."""

    def list_keys(self) -> list[str]:
        """Return all prompt keys (path prefix and extension already stripped)."""
        ...

    def read_file(self, key: str) -> str:
        """Return raw content for key. Raises KeyError if file not found."""
        ...


class FakeGitAdapter:
    """Test double: in-memory dict of key → raw content."""

    def __init__(self, files: dict[str, str]) -> None:
        self._files = dict(files)

    def list_keys(self) -> list[str]:
        return list(self._files.keys())

    def read_file(self, key: str) -> str:
        if key not in self._files:
            raise KeyError(key)
        return self._files[key]


class GitPythonAdapter:
    """Real adapter using gitpython. Requires pip install pypromptr[git]."""

    def __init__(
        self,
        url: str | None = None,
        *,
        ref: str = "HEAD",
        path: str = "",
        extension: str = ".md",
        local_path: str | Path | None = None,
    ) -> None:
        self._url = url
        self._ref = ref
        self._path = path.rstrip("/")
        self._extension = extension
        self._local_path = Path(local_path) if local_path is not None else None
        self._repo = None
        self._tmpdir = None

    def _import_git(self):
        try:
            import git
            return git
        except ImportError as e:
            raise ImportError("Install Git support with: pip install pypromptr[git]") from e

    def _get_repo(self):
        if self._repo is not None:
            return self._repo
        git = self._import_git()
        if self._local_path is not None:
            self._repo = git.Repo(str(self._local_path))
        elif self._url is not None:
            self._tmpdir = tempfile.mkdtemp(prefix="pypromptr-git-")
            self._repo = git.Repo.clone_from(self._url, self._tmpdir, depth=1)
        else:
            raise ValueError("Either url or local_path must be provided")
        return self._repo

    def _get_tree(self):
        repo = self._get_repo()
        try:
            commit = repo.commit(self._ref)
        except Exception as e:
            raise ValueError(f"Could not resolve ref {self._ref!r}: {e}") from e
        tree = commit.tree
        if self._path:
            for part in self._path.split("/"):
                tree = tree[part]
        return tree

    def list_keys(self) -> list[str]:
        tree = self._get_tree()
        keys: list[str] = []
        for blob in tree.traverse():
            if hasattr(blob, "data_stream") and blob.name.endswith(self._extension):
                stem = blob.name[: -len(self._extension)]
                keys.append(stem)
        return keys

    def read_file(self, key: str) -> str:
        tree = self._get_tree()
        filename = f"{key}{self._extension}"
        try:
            blob = tree[filename]
            return blob.data_stream.read().decode("utf-8")
        except KeyError:
            raise KeyError(key)


class GitRepoPrompts:
    """PromptSource that reads prompts from a Git repository (lazy)."""

    def __init__(
        self,
        url: str | None = None,
        *,
        ref: str = "HEAD",
        path: str = "",
        extension: str = ".md",
        local_path: str | Path | None = None,
        adapter: GitRepoAdapter | None = None,
    ) -> None:
        if adapter is not None:
            self._adapter: GitRepoAdapter = adapter
        else:
            self._adapter = GitPythonAdapter(
                url=url,
                ref=ref,
                path=path,
                extension=extension,
                local_path=local_path,
            )

    def keys(self) -> list[str]:
        """Return all prompt keys from the repository."""
        return self._adapter.list_keys()

    def get_prompt(self, key: str) -> SimplePrompt | MessagesPrompt:
        """Read and parse the prompt for key. Raises KeyError if file not found."""
        raw = self._adapter.read_file(key)
        return parse_prompt_text(raw)
