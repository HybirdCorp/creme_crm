from django.db import migrations


# NB: this migration should be useless (the code avoids empty Conditions).
def fill_empty(apps, schema_editor):
    apps.get_model('creme_core', 'EntityFilterCondition').objects.filter(
        raw_value='',
    ).update(raw_value='{}')


def convert_property_conditions(apps, schema_editor):
    for cond in apps.get_model('creme_core', 'EntityFilterCondition').objects.filter(
        type=15,  # PropertyConditionHandler.type_id
    ):
        cond.raw_value = '{"has":%s}' % cond.raw_value
        cond.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0127_v2_6__headerfilter_jsonfield02'),
    ]

    operations = [
        migrations.RunPython(fill_empty),
        migrations.RunPython(convert_property_conditions),
    ]
