from django.db import migrations

from creme.creme_core.models.fields import ColorField


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesphase',
            name='color',
            field=ColorField(default=ColorField.random, max_length=6, verbose_name='Color'),
        ),
    ]
