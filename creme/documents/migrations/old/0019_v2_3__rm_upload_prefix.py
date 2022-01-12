from django.conf import settings
from django.db import migrations


def remove_filedata_prefix(apps, schema_editor):
    if settings.DOCUMENTS_DOCUMENT_MODEL == 'documents.Document':
        prefix = 'upload/'
        prefix_length = len(prefix)

        for document in apps.get_model('documents', 'Document').objects.filter(
            filedata__startswith='upload/',
        ):
            document.filedata = str(document.filedata)[prefix_length:]
            document.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_filedata_prefix),
    ]
