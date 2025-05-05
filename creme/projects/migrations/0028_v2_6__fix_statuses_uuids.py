from django.db import migrations


def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('projects', model_name).objects.filter
    count = 0

    for old_id, new_uuid in ids_to_uuids:
        instance = filter_instances(id=old_id).first()

        if instance is not None:
            old_uuid = str(instance.uuid)

            if old_uuid != new_uuid:
                instance.extra_data['old_uuid'] = old_uuid
                instance.uuid = new_uuid
                instance.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "{model_name}" have been modified '
            f'(old ones are stored in meta_data).'
        )

PROJECTS_PROJECTSTATUS_UUIDS = [
    (1, 'e0487a58-7c2a-45e9-a6da-f770c2f1bd53'),
    (2, 'c065000b-51a8-4f73-8585-64893d30770f'),
    (3, 'c9e3665d-2747-4ee9-a037-de751ae2a59a'),
    (4, '680c049d-d01f-4835-aa92-dc1455ee2e9f'),
    (5, '61d1f8dd-1849-4ec6-9cce-3b73e3f4d9ae'),
    (6, '27d1c818-d7c7-4200-ac6e-744998cfa9b7'),
    (7, 'a7d5caf2-c41c-4695-ab07-29300b2d19c1'),
]

PROJECTS_TASKSTATUS_UUIDS = [
    (1, '23cea775-dfed-44d4-82c0-809708618798'),
    (2, 'c05da59c-4a58-49b3-99af-c922c796caa7'),
    (3, '0a345a07-9790-4278-ab1a-e568b90efd0e'),
    (4, '35fbdfa6-d4ba-4f49-8e5f-60ccb6c4b8b2'),
    (5, '2f74b370-a381-44cb-8e01-5bfc3ab4a8da'),
]

def fix_project_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='ProjectStatus',
        ids_to_uuids=PROJECTS_PROJECTSTATUS_UUIDS,
    )

def fix_task_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='TaskStatus',
        ids_to_uuids=PROJECTS_TASKSTATUS_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_project_statuses_uuids),
        migrations.RunPython(fix_task_statuses_uuids),
    ]
