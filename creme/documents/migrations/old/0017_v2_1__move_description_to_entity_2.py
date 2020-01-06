from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity

    if settings.DOCUMENTS_DOCUMENT_MODEL == 'documents.Document':
        # apps.get_model('documents', 'Document').objects.update(description=F('description_tmp'))
        for doc in apps.get_model('documents', 'Document').objects.exclude(description_tmp=''):
            doc.description = doc.description_tmp
            doc.save()

    if settings.DOCUMENTS_FOLDER_MODEL == 'documents.Folder':
        # apps.get_model('documents', 'Folder').objects.update(description=F('description_tmp'))
        for folder in apps.get_model('documents', 'Folder').objects.exclude(description_tmp=''):
            folder.description = folder.description_tmp
            folder.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents',  '0016_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
