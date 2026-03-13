from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0191_v3_0__efilter_condition_string_types3'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='requirement_mode',
            field=models.PositiveSmallIntegerField(
                verbose_name='Is required?',
                choices=[
                    (1, 'Not required'), (2, 'Required'), (3, 'Required (at creation only)'),
                ],
                default=1,
                help_text=(
                    'A required custom-field must be filled when a new entity is created, '
                    'or an existing entity is edited; existing entities are not immediately '
                    'impacted.'
                ),
            ),
        ),
    ]
