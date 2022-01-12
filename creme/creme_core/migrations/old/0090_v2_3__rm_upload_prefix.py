from django.db import migrations


def remove_filedata_prefix(apps, schema_editor):
    prefix = 'upload/'
    prefix_length = len(prefix)

    for file_ref in apps.get_model('creme_core', 'FileRef').objects.filter(
        filedata__startswith='upload/',
    ):
        file_ref.filedata = str(file_ref.filedata)[prefix_length:]
        file_ref.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0089_v2_3__customforms_per_role03'),
    ]

    operations = [
        migrations.RunPython(remove_filedata_prefix),
    ]
