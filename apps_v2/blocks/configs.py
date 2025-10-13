from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from django.db.models import Q, Case, When, IntegerField

from apps.blocks.models.block import Block
from apps.blocks.models.table_config import BlockTableConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.models.pivot_config import PivotConfig


def get_block_for_spec(spec_id: str) -> Block:
    obj, _ = Block.objects.get_or_create(code=spec_id, defaults={"name": spec_id, "description": ""})
    return obj


def list_table_configs(block: Block, user) -> Iterable[BlockTableConfig]:
    qs = BlockTableConfig.objects.filter(block=block).filter(Q(user=user) | Q(visibility=BlockTableConfig.VISIBILITY_PUBLIC))
    return qs.annotate(
        _vis_order=Case(
            When(visibility=BlockTableConfig.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("_vis_order", "name")


def list_filter_configs(block: Block, user) -> Iterable[BlockFilterConfig]:
    from django.db.models import Q, Case, When, IntegerField
    qs = BlockFilterConfig.objects.filter(block=block).filter(Q(user=user) | Q(visibility=BlockFilterConfig.VISIBILITY_PUBLIC))
    return qs.annotate(
        _vis_order=Case(
            When(visibility=BlockFilterConfig.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("_vis_order", "name")


def choose_active_table_config(block: Block, user, config_id: Optional[int]) -> Optional[BlockTableConfig]:
    qs = list_table_configs(block, user)
    if config_id:
        try:
            return qs.get(pk=config_id)
        except BlockTableConfig.DoesNotExist:
            pass
    # Prefer user's default; else public default; else first private; else first public
    return (
        qs.filter(user=user, is_default=True).first()
        or qs.filter(visibility=BlockTableConfig.VISIBILITY_PUBLIC, is_default=True).first()
        or qs.filter(user=user).first()
        or qs.filter(visibility=BlockTableConfig.VISIBILITY_PUBLIC).first()
    )


def choose_active_filter_config(block: Block, user, config_id: Optional[int]) -> Optional[BlockFilterConfig]:
    qs = list_filter_configs(block, user)
    if config_id:
        try:
            return qs.get(pk=config_id)
        except BlockFilterConfig.DoesNotExist:
            pass
    return (
        qs.filter(user=user, is_default=True).first()
        or qs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC, is_default=True).first()
        or qs.filter(user=user).first()
        or qs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC).first()
    )



def list_pivot_configs(block: Block, user) -> Iterable[PivotConfig]:
    qs = PivotConfig.objects.filter(block=block).filter(Q(user=user) | Q(visibility=PivotConfig.VISIBILITY_PUBLIC))
    return qs.annotate(
        _vis_order=Case(
            When(visibility=PivotConfig.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("_vis_order", "name")



def choose_active_pivot_config(block: Block, user, config_id: Optional[int]) -> Optional[PivotConfig]:
    qs = list_pivot_configs(block, user)
    if config_id:
        try:
            return qs.get(pk=config_id)
        except PivotConfig.DoesNotExist:
            pass
    return (
        qs.filter(user=user, is_default=True).first()
        or qs.filter(visibility=PivotConfig.VISIBILITY_PUBLIC, is_default=True).first()
        or qs.filter(user=user).first()
        or qs.filter(visibility=PivotConfig.VISIBILITY_PUBLIC).first()
    )
