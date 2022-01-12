from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0083_v2_2__remove_language_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='raw_data',
            field=models.TextField(editable=False, null=True),
        ),
    ]
