from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='origin',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='salesphase',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
