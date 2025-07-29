from apps.blocks.models import Block
from apps.blocks.forms import DummyLaborForm

class LaborFormBlock(Block):
    id = "labor_form"
    template_name = "blocks/labor_form.html"

    def get_context(self, request):
        form = DummyLaborForm()
        return {
            "form": form,
            "save_url": "#"
        }