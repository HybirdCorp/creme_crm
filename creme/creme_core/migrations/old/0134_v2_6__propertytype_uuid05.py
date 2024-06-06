from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0133_v2_6__propertytype_uuid04'),
    ]

    operations = [
        # Finalize CremeProperty -----------------------------------------------
        migrations.RemoveField(
            model_name='CremeProperty',
            name='old_type',
        ),
        migrations.AlterField(
            model_name='CremeProperty',
            name='type',
            field=models.ForeignKey(
                verbose_name='Type of property',
                to='creme_core.CremePropertyType',
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='CremeProperty',
            unique_together={('type', 'creme_entity')},
        ),

        # Finalize RelationType -----------------------------------------------
        migrations.RemoveField(
            model_name='relationtype',
            name='subject_properties_bk',
        ),
        migrations.RemoveField(
            model_name='relationtype',
            name='subject_forbidden_properties_bk',
        ),

        # Clean new type -------------------------------------------------------
        migrations.RemoveField(
            model_name='cremepropertytype',
            name='old_id',
        ),

        # Delete useless old model ---------------------------------------------
        migrations.DeleteModel(name='OldCremePropertyType'),
    ]
