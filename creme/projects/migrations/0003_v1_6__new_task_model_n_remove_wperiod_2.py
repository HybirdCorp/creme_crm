# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY


REL_SUB_LINKED_2_PTASK = 'projects-subject_linked_2_projecttask'
REL_OBJ_LINKED_2_PTASK = 'projects-object_linked_2_projecttask'

REL_SUB_PART_AS_RESOURCE = 'projects-subject_part_as_resource'
REL_OBJ_PART_AS_RESOURCE = 'projects-object_part_as_resource'


def _create_rtype(RelationType, subject_desc, object_desc):
    create = RelationType.objects.create
    sub_relation_type = create(id=subject_desc[0],
                               predicate=subject_desc[1],
                               is_internal=True,
                              )
    obj_relation_type = create(id=object_desc[0],
                               predicate=object_desc[1],
                               is_internal=True,
                              )

    sub_relation_type.symmetric_type = obj_relation_type
    obj_relation_type.symmetric_type = sub_relation_type

    #NB: we ignore ContentType constraint : they will be set by populate script

    sub_relation_type.save()
    obj_relation_type.save()

    return sub_relation_type

def copy_old_fields(apps, schema_editor):
    field_names = (
            'cremeentity_ptr',
            'title',
            'start',
            'end',
            'duration',
            'description',
        )

    #TODO: if custom task => do nothing
    #TODO: if custom activity => do nothing

    for instance in apps.get_model('projects', 'ProjectTask').objects.all():
        activity_instance = instance.activity_ptr
        instance.id = activity_instance.pk

        for field_name in field_names:
            setattr(instance, field_name, getattr(activity_instance, field_name))

        instance.save()

def create_activities(apps, schema_editor):
    get_model = apps.get_model
    WorkingPeriod = get_model('projects', 'WorkingPeriod')

    if not WorkingPeriod.objects.exists():
        return

    RelationType = get_model('creme_core',   'RelationType')
    Relation     = get_model('creme_core',   'Relation')
    Activity     = get_model('activities',   'Activity')
    Calendar     = get_model('activities',   'Calendar')
    ProjectTask  = get_model('projects',     'ProjectTask')
    ContentType  = get_model('contenttypes', 'ContentType')

    #TODO: if custom activity => do nothing + error message

    rtype_part = RelationType.objects.get(pk=REL_SUB_PART_2_ACTIVITY)

    #NB: predicate are not translared => fixed by populate script
    rtype_link2ptask = _create_rtype(RelationType,
                                     (REL_SUB_LINKED_2_PTASK, u'is related to the task of project'),
                                     (REL_OBJ_LINKED_2_PTASK, u'includes the activity'),
                                    )
    rtype_part_as_rsrc = _create_rtype(RelationType,
                                       (REL_SUB_PART_AS_RESOURCE, u'is a resource of'),
                                       (REL_OBJ_PART_AS_RESOURCE, u'has as a resource'),
                                      )

    create_activity = Activity.objects.create
    create_rel_simple = Relation.objects.create

    get_ct = ContentType.objects.get
    activity_ctype = get_ct(app_label='activities', model='activity')
    relation_ctype = get_ct(app_label='creme_core', model='relation')

    def create_relation(subject_entity_id, rtype, object_entity_id, user):
        r1 = create_rel_simple(entity_type=relation_ctype,
                               subject_entity_id=subject_entity_id,
                               type=rtype,
                               object_entity_id=object_entity_id,
                               user=user,
                             )
        r2 = create_rel_simple(entity_type=relation_ctype,
                               subject_entity_id=object_entity_id,
                               type=rtype.symmetric_type,
                               object_entity_id=subject_entity_id,
                               user=user,
                               symmetric_relation=r1,
                              )
        r1.symmetric_relation = r2
        r1.save()

    for task in ProjectTask.objects.all():
        # The max_length is 100 => 2 * 45 + formatting/number
        project_name = task.project.name[:45]
        task_name = task.title[:45]

        task_activity = task.activity_ptr
        user = task_activity.user

        for i, wperiod in enumerate(WorkingPeriod.objects.filter(task=task), start=1):
            activity = create_activity(user=user,
                                       entity_type=activity_ctype,
                                       title=u'%s - %s - %003d' % (project_name, task_name, i),
                                       start=wperiod.start_date,
                                       end=wperiod.end_date,
                                       duration=wperiod.duration,
                                       type=task_activity.type,
                                       sub_type=task_activity.sub_type,
                                       #busy= TODO ??
                                      )
            contact = wperiod.resource.linked_contact

            create_relation(activity.id, rtype_link2ptask,   task.pk,     user=user)
            create_relation(contact.id,  rtype_part,         activity.id, user=user)
            create_relation(contact.id,  rtype_part_as_rsrc, activity.id, user=user)

            if contact.is_user:
                activity.calendars.add(Calendar.objects.get(user=contact.is_user, is_default=True))

        task_activity.calendars.clear()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0002_v1_6__new_task_model_n_remove_wperiod_1'),
    ]

    operations = [
        migrations.RunPython(copy_old_fields),
        migrations.RunPython(create_activities),
    ]
