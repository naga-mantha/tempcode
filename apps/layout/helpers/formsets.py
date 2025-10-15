from django.forms import modelformset_factory

from apps.layout.models import LayoutBlock
from apps.layout.forms import LayoutBlockForm


def get_layoutblock_formset():
    return modelformset_factory(
        LayoutBlock,
        form=LayoutBlockForm,
        fields=(
            "col_span",
            "row_span",
            "title",
            "note",
            "preferred_filter_name",
            "preferred_setting_name",
        ),
        extra=0,
    )
