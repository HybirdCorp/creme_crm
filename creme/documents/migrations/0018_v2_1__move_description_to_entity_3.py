from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0017_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='description_tmp',
        ),
        migrations.RemoveField(
            model_name='folder',
            name='description_tmp',
        ),
    ]
