from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0009_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='opportunity',
            name='description_tmp',
        ),
    ]
