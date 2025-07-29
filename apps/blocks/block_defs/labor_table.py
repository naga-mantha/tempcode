from apps.blocks.models import Block

class LaborTableBlock(Block):
    id = "labor_table"
    template_name = "blocks/labor_table.html"

    def get_context(self, request):
        return {
            "data": [
                {"labor": "John Smith", "d1": 8, "d2": 7.5, "d3": 8, "d4": 8, "d5": 7, "d6": 0, "d7": 0},
                {"labor": "Jane Doe", "d1": 6, "d2": 8, "d3": 8, "d4": 7.5, "d5": 7.5, "d6": 0, "d7": 0},
            ]
        }
