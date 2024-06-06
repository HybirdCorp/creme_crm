from django.db import migrations
from django.db.models import Q


# NB: this migration should be useless (the code avoids empty HeaderFilters).
def fill_null(apps, schema_editor):
    apps.get_model('creme_core', 'HeaderFilter').objects.filter(
        Q(json_cells=None) | Q(json_cells='')
    ).update(json_cells='[]')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_null),
    ]
