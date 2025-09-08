from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0049_alter_currency_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='ToDo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                (
                    'status',
                    models.CharField(
                        choices=[('Not Started', 'Not Started'), ('In Progress', 'In Progress'), ('Completed', 'Completed')],
                        default='Not Started',
                        max_length=20,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('priority', models.IntegerField(db_index=True, default=0)),
            ],
            options={
                'ordering': ['priority', 'created_at'],
            },
        ),
        migrations.AddField(
            model_name='todo',
            name='dependencies',
            field=models.ManyToManyField(blank=True, related_name='dependents', symmetrical=False, to='common.todo'),
        ),
    ]

