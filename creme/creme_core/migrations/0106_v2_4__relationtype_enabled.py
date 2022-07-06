from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0105_v2_4__relation_object_ctype03'),
    ]

    operations = [
        migrations.AddField(
            model_name='relationtype',
            name='enabled',
            field=models.BooleanField(default=True, editable=False, verbose_name='Enabled?'),
        ),
    ]
