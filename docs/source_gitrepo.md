# Design: GitRepoPrompts

## Motivation

Teams that version-control prompts alongside code want to load them directly from a Git repository — a specific branch, tag, or commit — without cloning manually. This enables:

- Pinning prompts to a release tag (`v1.2.0`) for reproducibility
- Loading prompts from a shared monorepo without checking it out locally
- Staging environments that always pull from `main`, production that pins to a tag

## Optional dependency

```bash
pip install pypromptr[git]
# adds: gitpython
```

## Interface

```python
from pypromptr.git_source import GitRepoPrompts

# Remote repo, pin to tag
source = GitRepoPrompts(
    url="https://github.com/org/prompts-repo.git",
    ref="v1.2.0",          # branch, tag, or commit SHA; default: HEAD of default branch
    path="prompts/",        # subdirectory within the repo; default: repo root
    extension=".md",        # file extension to scan; default: ".md"
)

# Already-cloned local repo
source = GitRepoPrompts(local_path="/path/to/repo", ref="main", path="prompts/")
```

## Behaviour

### `keys() -> list[str]`
Lists files matching `extension` under `path` at the given `ref`. Returns filenames stripped of extension. Clones (shallow, `--depth 1`) or fetches on first call and caches the working tree for the process lifetime.

### `get_prompt(key: str) -> PromptLike`
Reads the file `{path}/{key}{extension}` from the cached working tree. Parses the same way as `FilePrompts` (frontmatter + body). Raises `KeyError(key)` if the file does not exist at that ref.

## Caching

- Clone/fetch is done once per `(url, ref)` pair per process, into a temp directory.
- For mutable refs (branches like `main`), the cache may be stale between process restarts — acceptable for most use cases. Document this clearly.
- For immutable refs (tags, commit SHAs), the cache is always valid.

## Notes

- Shallow clone (`--depth 1`) keeps init fast for large repos.
- Private repos require credentials: support `url` with embedded token (`https://token@github.com/...`) or SSH via the user's existing git config.
- Does **not** implement a file-watcher; prompt updates require process restart.
- `keys()` is supported (shallow clone makes it cheap enough).

## Example

```python
from pypromptr import PromptRegistry
from pypromptr.git_source import GitRepoPrompts

registry = PromptRegistry(
    GitRepoPrompts("https://github.com/org/prompts.git", ref="v2.0.0", path="prompts/"),
)
rendered = registry.get("system-prompt", role="assistant")
```
