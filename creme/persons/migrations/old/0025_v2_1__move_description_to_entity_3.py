from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0024_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='description_tmp',
        ),
        migrations.RemoveField(
            model_name='organisation',
            name='description_tmp',
        ),
    ]
