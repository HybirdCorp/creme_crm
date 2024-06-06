from django.db import migrations


def fill_segments(apps, schema_editor):
    get_ptype = apps.get_model('creme_core', 'CremePropertyType').objects.get

    for segment in apps.get_model('commercial', 'MarketSegment').objects.exclude(old_property_type_id=None):
        segment.property_type = get_ptype(old_id=segment.old_property_type_id)
        segment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0018_v2_6__ptype_uuid03'),
        ('creme_core', '0133_v2_6__propertytype_uuid04'),
    ]
    run_before = [
        ('creme_core', '0134_v2_6__propertytype_uuid05'),
    ]

    operations = [
        migrations.RunPython(fill_segments),
    ]
