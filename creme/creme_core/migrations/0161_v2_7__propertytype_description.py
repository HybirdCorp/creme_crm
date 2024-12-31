from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0160_v2_7__customentitytype'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremepropertytype',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description'),
        ),
    ]
