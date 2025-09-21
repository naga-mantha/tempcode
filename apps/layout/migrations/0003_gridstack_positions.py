from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layout', '0002_remove_layoutblock_layoutblock_col_allowed_values_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='layoutblock',
            name='x',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='layoutblock',
            name='y',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='layoutblock',
            name='w',
            field=models.PositiveIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='layoutblock',
            name='h',
            field=models.PositiveIntegerField(default=2),
        ),
        migrations.AddConstraint(
            model_name='layoutblock',
            constraint=models.CheckConstraint(check=models.Q(('w__gte', 1), ('w__lte', 12)), name='layoutblock_w_range'),
        ),
        migrations.AddConstraint(
            model_name='layoutblock',
            constraint=models.CheckConstraint(check=models.Q(('h__gte', 1), ('h__lte', 12)), name='layoutblock_h_range'),
        ),
        migrations.AddConstraint(
            model_name='layoutblock',
            constraint=models.CheckConstraint(check=models.Q(('x__gte', 0)), name='layoutblock_x_nonneg'),
        ),
        migrations.AddConstraint(
            model_name='layoutblock',
            constraint=models.CheckConstraint(check=models.Q(('y__gte', 0)), name='layoutblock_y_nonneg'),
        ),
    ]

