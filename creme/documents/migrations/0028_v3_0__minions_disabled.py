from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentcategory',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='foldercategory',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
