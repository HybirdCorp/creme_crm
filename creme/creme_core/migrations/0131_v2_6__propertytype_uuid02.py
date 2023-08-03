from django.db import migrations


# NB: we back up in TextFields because there are small numbers of elements
def backup_ptype_m2m(apps, schema_editor):
    for ptype in apps.get_model('creme_core', 'CremePropertyType').objects.all():
        ctypes_ids = ','.join(
            str(ct_id) for ct_id in ptype.subject_ctypes.values_list('id', flat=True)
        )
        if ctypes_ids:
            ptype.subject_ctypes_bk = ctypes_ids
            ptype.save()


def backup_rtype_m2m(apps, schema_editor):
    for rtype in apps.get_model('creme_core', 'RelationType').objects.all():
        rtype.subject_properties_bk = ','.join(
            rtype.subject_properties.values_list('id', flat=True)
        )
        rtype.subject_forbidden_properties_bk = ','.join(
            rtype.subject_forbidden_properties.values_list('id', flat=True)
        )

        if rtype.subject_properties_bk or rtype.subject_forbidden_properties_bk:
            rtype.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0130_v2_6__propertytype_uuid01'),
    ]

    operations = [
        migrations.RunPython(backup_ptype_m2m),
        migrations.RunPython(backup_rtype_m2m),
    ]
