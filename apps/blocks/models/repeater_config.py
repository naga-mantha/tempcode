from django.db import models

from apps.blocks.models.base_user_config import BaseUserConfig


class RepeaterConfig(BaseUserConfig):
    """Stores a saved repeater schema per user + block.

    schema keys (suggested):
    - block_code: str
    - group_by: str (field path)
    - label_field: Optional[str]
    - include_null: bool
    - cols: int (Bootstrap span)
    - child_filters_map: dict[str, str] mapping filter key -> 'value'|'label'|<literal>
    - child_filter_config_name: Optional[str]
    - child_column_config_name: Optional[str]
    - sort: 'asc'|'desc'|'none'
    - limit: Optional[int]
    - title_template: Optional[str] e.g., "{label}"
    """

    schema = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_repeater_config_per_user_block",
            )
        ]

