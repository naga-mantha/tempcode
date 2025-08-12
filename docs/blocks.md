# Blocks Framework

This project exposes a small framework for building reusable UI blocks. Blocks are
Python classes that encapsulate configuration, runtime data, and the rendering
logic needed to display a component on a page.

## BaseBlock interface

All blocks inherit from `BaseBlock`. The class requires implementers to
separate configuration data from runtime data via two abstract methods:

```python
class BaseBlock(ABC):
    template_name = ""
    supported_features: list[str] = []

    @abstractmethod
    def get_config(self, request):
        """Return configuration metadata for this block."""

    @abstractmethod
    def get_data(self, request):
        """Return the data required to render this block."""
```
The default `render()` implementation merges the dictionaries returned by these
methods and renders the configured template【F:apps/blocks/base.py†L1-L35】.

A simple block can therefore implement these two methods and rely on `render()`
to produce its output.

## Registering blocks

Blocks are registered with the global `block_registry` so that other parts of
the system can look them up by name:

```python
from apps.blocks.registry import block_registry
from apps.production.blocks import ProductionOrderTableBlock

block_registry.register("production_order_table", ProductionOrderTableBlock())
```
`BlockRegistry.register()` stores the instance and tracks metadata such as the
supported features【F:apps/blocks/registry.py†L1-L35】.

## User configuration models

Two models store per-user configuration for table-style blocks:

* `BlockColumnConfig` keeps the list of visible fields for a block (`fields` JSON
  array) and enforces uniqueness per user/block combo【F:apps/blocks/models/block_column_config.py†L1-L17】.
* `BlockFilterConfig` stores saved filter values in its `values` JSON field【F:apps/blocks/models/block_filter_config.py†L1-L9】.

These models allow users to persist multiple named configurations with one
marked as the default.

## Filter schema

Table blocks that declare the `"filters"` feature describe their available
filters using a schema dictionary. Each key represents a filter and maps to a
configuration object. The `FilterResolutionMixin` normalizes this schema,
providing a default type of `"text"` and resolving callable `choices` against
the current user【F:apps/blocks/blocks/table/filter_utils.py†L1-L14】.

Supported configuration keys include:

* `label` – human-friendly label displayed in the UI.
* `type` – `text`, `multiselect`, `select`, `boolean`, etc.
* `choices` – optional list of choices or a callable receiving the user and
  returning such a list.
* `help` – optional help text.
* `handler` – callable applied to the queryset when the filter is present.

Example:

```python
def get_filter_schema(self, request):
    def status_choices(user):
        return [("open", "Open"), ("in_progress", "In Progress"), ("closed", "Closed")]

    return {
        "production_order": {
            "label": "Order #",
            "type": "text",
            "handler": lambda qs, val: qs.filter(production_order__icontains=val),
        },
        "status": {
            "label": "Status",
            "type": "multiselect",
            "choices": status_choices,
            "handler": lambda qs, val: qs.filter(status__in=val if isinstance(val, list) else [val]),
        },
    }
```
For a complete working example see
[`apps/production/blocks.py`](../apps/production/blocks.py), which defines a
`ProductionOrderTableBlock` and demonstrates registering callable filter
handlers【F:apps/production/blocks.py†L1-L77】.

The `apply_filter_registry()` helper iterates over this schema and executes each
filter's handler when its value is provided, returning the filtered queryset
【F:apps/blocks/services/filtering.py†L1-L28】.
