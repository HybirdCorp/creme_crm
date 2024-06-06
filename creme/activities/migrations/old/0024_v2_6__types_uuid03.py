from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0023_v2_6__types_uuid02'),
    ]

    operations = [
        # Finalize Activity ----------------------------------------------------
        migrations.RemoveField(
            model_name='activity',
            name='old_sub_type',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='old_type',
        ),
        migrations.AlterField(
            model_name='activity',
            name='sub_type',
            field=models.ForeignKey(
                to='activities.activitysubtype',
                verbose_name='Activity sub-type',
                on_delete=models.PROTECT,
            ),
        ),
        migrations.AlterField(
            model_name='activity',
            name='type',
            field=models.ForeignKey(
                to='activities.activitytype',
                verbose_name='Activity type',
                on_delete=models.PROTECT,
            ),
        ),

        # Clean new types ------------------------------------------------------
        migrations.RemoveField(
            model_name='activitytype',
            name='old_id',
        ),
        migrations.RemoveField(
            model_name='activitysubtype',
            name='old_id',
        ),

        # Delete useless old models --------------------------------------------
        migrations.DeleteModel(name='OldActivitySubType'),
        migrations.DeleteModel(name='OldActivityType'),
    ]
