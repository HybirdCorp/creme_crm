from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0006_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='description_tmp',
        ),
        migrations.RemoveField(
            model_name='tickettemplate',
            name='description_tmp',
        ),
    ]
