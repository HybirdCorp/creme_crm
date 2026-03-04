from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0171_v2_8__extra_data_for_ptype_n_rtype'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='deactivated_on',
            field=models.DateTimeField(
                default=None, null=True, verbose_name='Deactivated on', editable=False,
            ),
        ),
    ]
