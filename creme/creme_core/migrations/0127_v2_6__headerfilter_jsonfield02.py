from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
         ('creme_core', '0126_v2_6__headerfilter_jsonfield01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='headerfilter',
            name='json_cells',
            field=models.JSONField(default=list, editable=False),
        ),
    ]
