from django.core.management.base import BaseCommand, CommandError
from django.apps import apps as django_apps

from django_bi.workflow.utils import generate_workflow_permissions_for_model


class Command(BaseCommand):
    help = (
        "Rebuild per-state workflow permissions for all models or a specific app/model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            help="App label to limit which models are processed.",
        )
        parser.add_argument(
            "--model",
            help="Model name to limit processing to. Requires --app.",
        )

    def handle(self, *args, **options):
        app_label = options.get("app")
        model_name = options.get("model")

        if model_name and not app_label:
            raise CommandError("--model option requires --app.")

        try:
            if app_label:
                try:
                    app_config = django_apps.get_app_config(app_label)
                except LookupError:
                    raise CommandError(f"App '{app_label}' not found.")

                if model_name:
                    try:
                        models = [app_config.get_model(model_name)]
                    except LookupError:
                        raise CommandError(
                            f"Model '{model_name}' not found in app '{app_label}'."
                        )
                else:
                    models = app_config.get_models()
            else:
                models = django_apps.get_models()

            created_count = 0
            deleted_count = 0
            for model in models:
                created, deleted = generate_workflow_permissions_for_model(model)
                created_count += created
                deleted_count += deleted

            self.stdout.write(
                self.style.SUCCESS(
                    "Workflow permissions rebuilt. "
                    f"Created {created_count} and deleted {deleted_count} permissions."
                )
            )
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"Error rebuilding workflow permissions: {exc}")

