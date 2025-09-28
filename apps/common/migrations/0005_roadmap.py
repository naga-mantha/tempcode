from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0004_alter_productionmrpmessage_mrp_message_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Roadmap",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("technical_specifications", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                        ],
                        default="planned",
                        max_length=20,
                    ),
                ),
                (
                    "timeframe",
                    models.CharField(
                        choices=[("Q1", "Q1"), ("Q2", "Q2"), ("Q3", "Q3"), ("Q4", "Q4")], max_length=2
                    ),
                ),
                (
                    "app",
                    models.CharField(
                        choices=[
                            ("Common", "Common"),
                            ("Workflows", "Workflows"),
                            ("Permissions", "Permissions"),
                            ("Blocks", "Blocks"),
                            ("Layouts", "Layouts"),
                            ("Purchase", "Purchase"),
                            ("Production", "Production"),
                            ("Sales", "Sales"),
                            ("Planning", "Planning"),
                            ("Service", "Service"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["app", "timeframe", "title"]},
        ),
    ]

