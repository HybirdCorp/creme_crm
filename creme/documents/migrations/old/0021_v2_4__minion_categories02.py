from uuid import uuid4

from django.db import migrations

DOCUMENTS_FROM_ENTITIES = 1
DOCUMENTS_FROM_EMAILS = 2
UUID_FOLDER_CAT_ENTITIES = 'ab9e449a-0844-44fa-99c5-1d1e6abed9bf'
UUID_FOLDER_CAT_EMAILS = '7161caaa-013b-4c32-ac19-19da7cee4561'

UUID_MAP = {
    DOCUMENTS_FROM_ENTITIES: UUID_FOLDER_CAT_ENTITIES,
    DOCUMENTS_FROM_EMAILS: UUID_FOLDER_CAT_EMAILS,
}


def generate_UUIDs(apps, schema_editor):
    for instance in apps.get_model('documents', 'FolderCategory').objects.all():
        instance.uuid = UUID_MAP.get(instance.id) or uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0020_v2_4__minion_categories01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
