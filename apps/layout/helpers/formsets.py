from django.forms import modelformset_factory

from apps.layout.models import LayoutBlock
from apps.layout.forms import LayoutBlockForm


def get_layoutblock_formset():
    return modelformset_factory(
        LayoutBlock,
        form=LayoutBlockForm,
        fields=("col_sm", "col_md", "col_lg", "col_xl", "col_xxl", "title", "note"),
        extra=0,
    )
