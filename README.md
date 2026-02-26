# Spidey

Easy prompt loading from anywhere.

## Quick Start

```python
from pydantic import BaseModel
from spidey import Prompt, PromptMessage, PromptRegistry


class GreetingMeta(BaseModel):
    owner: str
    locale: str


registry = PromptRegistry.from_mapping(
    {
        "welcome": Prompt(
            key="welcome",
            messages=(
                PromptMessage(role="system", content="You are concise."),
                PromptMessage(role="user", content="Welcome {name}."),
            ),
            metadata=GreetingMeta(owner="support", locale="en-US"),
        )
    }
)

rendered = registry.get("welcome", name="Sam")
print(rendered.metadata.locale)  # en-US
print(rendered.to_dict_messages())
```

## Markdown Source

```python
from pathlib import Path
from pydantic import BaseModel
from spidey import MarkdownPromptSource, PromptRegistry


class GreetingMeta(BaseModel):
    owner: str
    locale: str


registry = PromptRegistry()
registry.load_source(
    MarkdownPromptSource(
        root=Path("prompts"),
        metadata_models={"welcome": GreetingMeta},
    )
)

rendered = registry.get("welcome", name="Sam")
print(rendered.to_string())
```

Expected markdown format:

```md
---
key: welcome
version: v1
metadata.owner: docs
metadata.locale: en-US
---
## system
You are concise.
## user
Welcome {name}.
```

## Rendering Modes and Adapters

```python
rendered = registry.get("welcome", name="Sam")

# Strict by default (missing/extra vars raise errors)
rendered_warn = registry.get("welcome", _mode="warn", name="Sam", extra="unused")
rendered_permissive = registry.get("welcome", _mode="permissive")

dict_messages = rendered.to_dict_messages()
plain_text = rendered.to_string()

# Optional dependency: langchain-core
# langchain_messages = rendered.to_langchain_messages()
```