from django.db import migrations, models
from django.db.models.deletion import PROTECT


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0018_v2_4__not_null_subtype01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='sub_type',
            field=models.ForeignKey(
                to='activities.activitysubtype',
                verbose_name='Activity sub-type',
                on_delete=PROTECT,
            ),
        ),
    ]
