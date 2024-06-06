from django.db import migrations


class Migration(migrations.Migration):
    run_before = [
        ('creme_core', '0134_v2_6__propertytype_uuid05')
    ]

    dependencies = [
        ('commercial', '0019_v2_6__ptype_uuid04'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marketsegment',
            name='old_property_type',
        ),
    ]
