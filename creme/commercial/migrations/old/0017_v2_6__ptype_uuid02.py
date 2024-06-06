from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0016_v2_6__ptype_uuid01'),
        ('creme_core', '0132_v2_6__propertytype_uuid03'),
    ]
    run_before = [
        ('creme_core', '0133_v2_6__propertytype_uuid04'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketsegment',
            name='property_type',
            field=models.ForeignKey(
                to='creme_core.CremePropertyType',
                editable=False, null=True,
                on_delete=models.CASCADE,
            ),
        ),
    ]
