from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
    if settings.PROJECTS_PROJECT_MODEL == 'projects.Project':
        # apps.get_model('projects', 'Project').objects.update(description=F('description_tmp'))
        for project in apps.get_model('projects', 'Project').objects.exclude(description_tmp=''):
            project.description = project.description_tmp
            project.save()

    if settings.PROJECTS_TASK_MODEL == 'projects.ProjectTask':
        # apps.get_model('projects', 'ProjectTask').objects.update(description=F('description_tmp'))
        for task in apps.get_model('projects', 'ProjectTask').objects.exclude(description_tmp=''):
            task.description = task.description_tmp
            task.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects',   '0016_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
