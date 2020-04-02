from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0065_v2_2__efiltercondition_raw_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='is_required',
            field=models.BooleanField(
                default=False, verbose_name='Is required?',
                help_text='A required custom-field must be filled when a new entity is created ; '
                          'existing entities are not immediately impacted.',
            ),
        ),
    ]
