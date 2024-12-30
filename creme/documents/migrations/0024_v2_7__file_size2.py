from django.db import migrations


def fill_sizes(apps, schema_editor):
    for document in apps.get_model('documents', 'Document').objects.filter(file_size=None):
        try:
            document.file_size = document.filedata.size
        except FileNotFoundError:
            document.file_size = 0

        document.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0023_v2_7__file_size1'),
    ]

    operations = [
        migrations.RunPython(fill_sizes),
    ]
