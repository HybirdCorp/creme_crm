from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0018_v3_0__default_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
