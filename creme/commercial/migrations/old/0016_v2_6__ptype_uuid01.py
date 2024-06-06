from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('commercial', '0001_initial'),
    ]
    run_before = [
        ('creme_core', '0132_v2_6__propertytype_uuid03'),
    ]

    operations = [
        migrations.RenameField(
            model_name='marketsegment',
            old_name='property_type',
            new_name='old_property_type',
        ),
        migrations.AlterField(
            model_name='marketsegment',
            name='old_property_type',
            field=models.ForeignKey(
                to='creme_core.CremePropertyType',
                editable=False, null=True,
                on_delete=models.CASCADE,
                db_constraint=False,
                db_index=False,
            ),
        ),
    ]
