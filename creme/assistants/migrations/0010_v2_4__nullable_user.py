from django.conf import settings
from django.db import migrations

from creme.creme_core.models.fields import CremeUserForeignKey


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assistants', '0009_v2_4__alert_trigger_offset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alert',
            name='user',
            field=CremeUserForeignKey(blank=True, null=True, to=settings.AUTH_USER_MODEL, verbose_name='Owner user'),
        ),
        migrations.AlterField(
            model_name='todo',
            name='user',
            field=CremeUserForeignKey(blank=True, null=True, to=settings.AUTH_USER_MODEL, verbose_name='Owner user'),
        ),
    ]
