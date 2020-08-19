from django.db import migrations


def init_ids(apps, schema_editor):
    for i, bmi in enumerate(
        apps.get_model('creme_core', 'ButtonMenuItem').objects.order_by(
            'content_type', 'order',
        ),
        start=1,
    ):
        bmi.tmp_id = i
        bmi.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0072_v2_2__buttonmenuitem_int_id01'),
    ]

    operations = [
        migrations.RunPython(init_ids),
    ]
