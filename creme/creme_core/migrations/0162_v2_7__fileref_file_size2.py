from django.db import migrations


def fill_sizes(apps, schema_editor):
    for file_ref in apps.get_model('creme_core', 'FileRef').objects.filter(file_size=None):
        try:
            file_ref.file_size = file_ref.filedata.size
        except FileNotFoundError:
            file_ref.file_size = 0

        file_ref.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0161_v2_7__fileref_file_size1'),
    ]

    operations = [
        migrations.RunPython(fill_sizes),
    ]
