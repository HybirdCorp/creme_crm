from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='civility',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='legalform',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='position',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='sector',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='staffsize',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
