from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='acttype',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
