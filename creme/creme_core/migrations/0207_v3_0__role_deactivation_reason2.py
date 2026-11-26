from django.conf import settings
from django.db import migrations
from django.utils.translation import activate
from django.utils.translation import gettext as _


def fill_deactivation_reasons(apps, schema_editor):
    activate(settings.LANGUAGE_CODE)
    apps.get_model('creme_core', 'UserRole').objects.exclude(deactivated_on=None).update(
        deactivation_reason=_('N/A (migration Creme 3.0)'),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0206_v3_0__role_deactivation_reason1'),
    ]

    operations = [
        migrations.RunPython(fill_deactivation_reasons),
    ]
