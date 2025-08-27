import django
from django.test import SimpleTestCase
from django.template.loader import render_to_string

django.setup()


class FilterFieldsTemplateTests(SimpleTestCase):
    def test_ajax_multiselect_renders_empty_option(self):
        schema = {
            "status": {
                "label": "Status",
                "type": "multiselect",
                "choices_url": "/dummy-url/",
            }
        }
        html = render_to_string(
            "components/filter_fields.html",
            {
                "filter_schema": schema,
                "initial_values": {},
                "name_prefix": "filters.",
                "id_prefix": "test",
            },
        )
        self.assertIn('<option value=""></option>', html)
