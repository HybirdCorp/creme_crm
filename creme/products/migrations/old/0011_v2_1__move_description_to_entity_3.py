from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0010_v2_1__move_description_to_entity_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='description_tmp',
        ),
        migrations.RemoveField(
            model_name='service',
            name='description_tmp',
        ),
    ]
