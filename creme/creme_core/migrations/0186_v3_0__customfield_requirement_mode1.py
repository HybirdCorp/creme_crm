from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='requirement_mode',
            field=models.PositiveSmallIntegerField(
                verbose_name='Is required?',
                choices=[
                    (1, 'Not required'), (2, 'Required'), (3, 'Required at creation'),
                ],
                default=1,
                help_text=(
                    # TODO: fix
                    'A required custom-field must be filled when a new entity is created; existing entities are not immediately impacted.'
                ),
            ),
        ),
    ]
