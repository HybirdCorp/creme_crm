from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0194_v3_0__customfield_requirement_mode3'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='language',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='vat',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
