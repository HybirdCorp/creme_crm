from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0019_v2_6__ptype_uuid04'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marketsegment',
            name='old_property_type',
        ),
    ]
