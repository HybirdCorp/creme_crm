from django.db import migrations

from creme.creme_core.models.fields import ColorField


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditnotestatus',
            name='color',
            field=ColorField(default=ColorField.random, max_length=6, verbose_name='Color'),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='color',
            field=ColorField(default=ColorField.random, max_length=6, verbose_name='Color'),
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='color',
            field=ColorField(default=ColorField.random, max_length=6, verbose_name='Color'),
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='color',
            field=ColorField(default=ColorField.random, max_length=6, verbose_name='Color'),
        ),
    ]
