from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('recurrents', '0007_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recurrentgenerator',
            name='description_tmp',
        ),
    ]
