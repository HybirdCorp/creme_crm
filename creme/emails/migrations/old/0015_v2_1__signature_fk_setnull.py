from django.db import migrations, models
from django.db.models.deletion import SET_NULL


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entityemail',
            name='signature',
            field=models.ForeignKey(blank=True, null=True, on_delete=SET_NULL,
                                    to='emails.EmailSignature', verbose_name='Signature',
                                   ),
        ),
    ]
