from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0040_v2_7__number_generation02'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='simplebillingalgo',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='simplebillingalgo',
            name='ct',
        ),
        migrations.RemoveField(
            model_name='simplebillingalgo',
            name='organisation',
        ),
        migrations.DeleteModel(
            name='ConfigBillingAlgo',
        ),
        migrations.DeleteModel(
            name='SimpleBillingAlgo',
        ),
    ]
