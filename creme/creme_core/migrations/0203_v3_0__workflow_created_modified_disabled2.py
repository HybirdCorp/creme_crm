from django.conf import settings
from django.db import migrations
from django.utils.translation import activate
from django.utils.translation import gettext as _

from creme.creme_core.migrations.utils.utils_30 import EPOCH


def fix_disabled_workflows(apps, schema_editor):
    activate(settings.LANGUAGE_CODE)
    apps.get_model('creme_core', 'Workflow').objects.filter(enabled=False).update(
        disabled=EPOCH,
        disabling_reason=_('N/A (migration Creme 3.0)'),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0202_v3_0__workflow_created_modified_disabled1'),
    ]

    operations = [
        migrations.RunPython(fix_disabled_workflows),
    ]
