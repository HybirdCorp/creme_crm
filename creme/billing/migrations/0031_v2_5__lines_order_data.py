from django.db import migrations
from django.db.models import F


def generate_line_ordering(apps, schema_editor):
    # Updating the order with the primary key a correct & efficient approximation.
    apps.get_model('billing', 'ProductLine').objects.update(order=F('pk'))
    apps.get_model('billing', 'ServiceLine').objects.update(order=F('pk'))


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0030_v2_5__lines_order'),
    ]

    operations = [
        migrations.RunPython(generate_line_ordering),
    ]
