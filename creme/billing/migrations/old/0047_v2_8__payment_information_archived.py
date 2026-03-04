from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0046_v2_8__minions_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentinformation',
            name='archived',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Archiving date'),
        ),
    ]
