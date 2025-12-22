from datetime import date, datetime
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

import creme.projects.bricks as proj_bricks
from creme.activities.constants import (
    REL_SUB_PART_2_ACTIVITY,
    UUID_SUBTYPE_MEETING_MEETING,
    UUID_TYPE_TASK,
)
from creme.activities.models import ActivitySubType, Calendar
from creme.activities.tests.base import Activity, skipIfCustomActivity
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.projects.constants import (
    REL_SUB_LINKED_2_PTASK,
    REL_SUB_PART_AS_RESOURCE,
    UUID_TSTATUS_COMPLETED,
)
from creme.projects.models import Resource, TaskStatus
from creme.projects.tests.base import (
    Contact,
    Project,
    ProjectsTestCase,
    ProjectTask,
    skipIfCustomTask,
)


@skipIfCustomActivity
@skipIfCustomTask
class ActivityTestCase(BrickTestCaseMixin, ProjectsTestCase):
    DELETE_ACTIVITY_URL = reverse('projects__delete_activity')

    @staticmethod
    def _build_edit_activity_url(activity):
        return reverse('projects__edit_activity', args=(activity.id,))

    def test_resource_n_activity__creation_views(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'legs')
        self.assertFalse(task.resources_set.all())

        response1 = self.assertGET200(self._build_add_resource_url(task))
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(_('Allocation of a new resource'), context.get('title'))
        self.assertEqual(Resource.save_label,               context.get('submit_label'))
        # ---
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        self.create_resource(task, worker, hourly_cost=100)

        resource = self.get_alone_element(task.resources_set.all())

        context = self.assertGET200(self._build_add_activity_url(task)).context
        self.assertEqual(
            _('New activity related to «{entity}»').format(entity=task),
            context.get('title'),
        )
        self.assertEqual(Activity.save_label, context.get('submit_label'))

        stype = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        self.create_activity(user=user, resource=resource, duration='8', sub_type_id=stype.id)

        activity = self.get_object_or_fail(Activity, title='Eva02 - legs - 001')

        self.assertEqual(stype.type_id, activity.type_id)
        self.assertEqual(stype.id,      activity.sub_type_id)
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)
        self.assertEqual(8, activity.duration)
        self.assertFalse(activity.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2015, month=5, day=19), activity.start)
        self.assertEqual(create_dt(year=2015, month=6, day=3),  activity.end)

        self.assertHaveRelation(subject=activity, type=REL_SUB_LINKED_2_PTASK,   object=task)
        self.assertHaveRelation(subject=worker,   type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker,   type=REL_SUB_PART_AS_RESOURCE, object=activity)

        self.assertEqual(8,   task.get_effective_duration())
        self.assertEqual(800, task.get_task_cost())  # 8 * 100
        self.assertEqual(-42, task.get_delay())  # 8 - 50
        self.assertTrue(task.is_alive())

        self.assertEqual(8,   project.get_effective_duration())
        self.assertEqual(800, project.get_project_cost())  # 8 * 100
        self.assertEqual(0,   project.get_delay())

        # ---
        detail_response = self.assertGET200(task.get_absolute_url())
        tree = self.get_html_tree(detail_response.content)

        resources_brick_node = self.get_brick_node(tree, brick=proj_bricks.TaskResourcesBrick)
        self.assertBrickTitleEqual(
            resources_brick_node,
            count=1,
            title='{count} Resource assigned to this task',
            plural_title='{count} Resources assigned to this task',
        )

        activities_brick_node = self.get_brick_node(tree, brick=proj_bricks.TaskActivitiesBrick)
        self.assertBrickTitleEqual(
            activities_brick_node,
            count=1,
            title='{count} Related activity',
            plural_title='{count} Related activities',
        )
        self.assertInstanceLink(activities_brick_node, worker)

    def test_resource_n_activity__edition_views(self):
        "Edition views + Calendar."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(user=user, resource=resource)

        url = resource.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.id,
                'contact':     worker.id,
                'hourly_cost': 200,
            },
        )
        self.assertNoFormError(response)

        resource = self.refresh(resource)
        self.assertEqual(200, resource.hourly_cost)

        activity = self.get_alone_element(task.related_activities)
        self.assertListEqual(
            [Calendar.objects.get_default_calendar(other_user)],
            [*activity.calendars.all()],
        )
        url = self._build_edit_activity_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        # ---
        response = self.client.post(
            url, follow=True,
            data={
                'resource':      worker.id,
                'start':         self.formfield_value_date(2010, 10, 11),
                'end':           self.formfield_value_date(2010, 10, 12),
                'duration':      10,
                'user':          user.id,
                'type_selector': activity.sub_type_id,
            },
        )
        self.assertNoFormError(response)

        activity = self.refresh(activity)
        self.assertEqual(10, activity.duration)
        self.assertHaveRelation(subject=worker, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker, type=REL_SUB_PART_AS_RESOURCE, object=activity)

    def test_resource_n_activity__not_alive_task03(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        status = self.get_object_or_fail(TaskStatus, uuid=UUID_TSTATUS_COMPLETED)
        task = self.create_task(project, 'legs', status=status)

        self.assertGET409(self._build_add_resource_url(task))

        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        response = self.create_resource(task, worker, error=True)
        self.assertFalse(task.resources_set.all())
        self.assertEqual(409, response.status_code)

    def test_resource_n_activity__collision(self):
        "Create 2 activities with a collision."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        task = self.create_task(project, 'arms')
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(
            user=user, resource=resource,
            start=datetime(year=2010, month=10, day=11, hour=15),
            end=datetime(year=2010, month=10, day=11, hour=17),
            busy='on'
        )
        act1 = task.related_activities[0]
        self.assertTrue(act1.busy)

        response = self.create_activity(
            user=user, resource=resource,
            start=datetime(year=2010, month=10, day=11, hour=16, minute=59),
            end=datetime(year=2010, month=10, day=11, hour=17, minute=30),
            busy='on', errors=True,
        )
        self.assertEqual(1, len(self.refresh(task).related_activities))
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                '{participant} already participates in the activity '
                '«{activity}» between {start} and {end}.'
            ).format(
                participant=worker,
                activity=act1,
                start='16:59:00',
                end='17:00:00',
            ),
        )

    def test_resource_n_activity__activity_edition(self):
        "Edition of activity: resource changes."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker1 = other_user.linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker1)
        self.create_resource(task, worker2)

        stype = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        data = {
            'resource':      worker1.id,
            'start':         self.formfield_value_date(2015, 5, 21),
            'end':           self.formfield_value_date(2015, 5, 22),
            'duration':      10,
            'user':          user.id,
            # 'type_selector': ACTIVITYSUBTYPE_MEETING_MEETING,
            'type_selector': stype.id,
        }
        self.client.post(self._build_add_activity_url(task), follow=True, data=data)

        activity = self.get_alone_element(task.related_activities)
        self.assertListEqual(
            [Calendar.objects.get_default_calendar(other_user)],
            [*activity.calendars.all()],
        )

        response = self.client.post(
            self._build_edit_activity_url(activity),
            follow=True,
            data={**data, 'resource': worker2.id},
        )
        self.assertNoFormError(response)

        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        # Alright the project Activities can be on no Calendar
        self.assertFalse(activity.calendars.all())

    def test_resource_n_activity__activity__edition__keep_participating(self):
        "Edition of activity: resource changes + keep_participating."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker1 = other_user.linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker1)
        self.create_resource(task, worker2)

        stype = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        data = {
            'resource':      worker1.id,
            'start':         self.formfield_value_date(2015, 5, 21),
            'end':           self.formfield_value_date(2015, 5, 22),
            'duration':      10,
            'user':          user.id,
            'type_selector': stype.id,
        }
        self.client.post(self._build_add_activity_url(task), follow=True, data=data)
        activity = self.get_alone_element(task.related_activities)

        response = self.client.post(
            self._build_edit_activity_url(activity),
            follow=True,
            data={
                **data,
                'resource': worker2.id,
                'keep_participating': 'on',
            },
        )
        self.assertNoFormError(response)

        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        self.assertHaveRelation(subject=worker1, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(other_user)],
            [*activity.calendars.all()],
        )

    def test_resource_n_activity__resource_must_be_related07(self):
        "Resource must be related to the task."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]

        task1 = self.create_task(project, 'Legs')
        task2 = self.create_task(project, 'Head')

        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        self.create_resource(task1, worker, hourly_cost=100)

        resources = [*task1.resources_set.all()]
        self.assertEqual(1, len(resources))

        stype = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        response = self.assertPOST200(
            self._build_add_activity_url(task2), follow=True,
            data={
                'resource':      worker.id,
                'start':         self.formfield_value_date(2016, 5, 19),
                'end':           self.formfield_value_date(2016, 6,  3),
                'duration':      8,
                'type_selector': stype.id,
                'user':          user.id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='resource',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': worker},
        )

    def test_resource_n_activity__perms(self):
        "Creation credentials are needed."
        user = self.login_as_projects_user(
            allowed_apps=['activities', 'persons'],
            creatable_models=[Project, ProjectTask],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'legs')
        url = self._build_add_activity_url(task)
        self.assertGET403(url)

        user.role.creatable_ctypes.add(ContentType.objects.get_for_model(Activity))
        self.assertGET200(url)

    def test_resource_n_activity__contacts_must_be_resources(self):
        "Posted contacts must be resources."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        contact = self.create_user().linked_contact
        stype = self.get_object_or_fail(ActivitySubType, uuid=UUID_SUBTYPE_MEETING_MEETING)
        response = self.assertPOST200(
            self._build_add_activity_url(task),
            follow=True,
            data={
                'resource':      contact.id,
                'start':         self.formfield_value_date(2020,  9, 14),
                'end':           self.formfield_value_date(2020, 12, 31),
                'duration':      100,
                'user':          user.id,
                'type_selector': stype.id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='resource',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': contact},
        )

    def test_activity_title(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva00')[0]
        task = self.create_task(project, 'head')
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker)
        resource = task.get_resources()[0]

        create_activity = partial(self.create_activity, user=user)
        create_activity(resource=resource, start=date(2015, 5, 20), end=date(2015, 5, 21))
        create_activity(resource=resource, start=date(2015, 5, 22), end=date(2015, 5, 23))
        self.assertCountEqual(
            ['Eva00 - head - 001', 'Eva00 - head - 002'],
            [a.title for a in task.related_activities],
        )

    def test_edit_activity_error(self):
        "Activity not related to a project task."
        user = self.login_as_root_and_get()
        sub_type = ActivitySubType.objects.filter(type__uuid=UUID_TYPE_TASK).first()
        activity = Activity.objects.create(
            user=user, title='My task',
            type_id=sub_type.type_id,
            sub_type=sub_type,
        )
        self.assertGET409(self._build_edit_activity_url(activity))

    @skipIfCustomActivity
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_activity__no_related_task(self):
        "Activity not related to a project task."
        user = self.login_as_root_and_get()

        sub_type = ActivitySubType.objects.filter(type__uuid=UUID_TYPE_TASK).first()
        activity = Activity.objects.create(
            user=user, title='My task',
            type_id=sub_type.type_id,
            sub_type=sub_type,
        )
        url = self.DELETE_ACTIVITY_URL
        data = {'id': activity.id}
        self.assertGET405(url, data=data)
        self.assertPOST409(url, data=data)

    @skipIfCustomActivity
    @skipIfCustomTask
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_activity__related_task(self):
        "Activity is related to a project task."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task    = self.create_task(project, 'arms')
        worker  = self.create_user().linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(user=user, resource=resource)
        activity = task.related_activities[0]

        self.assertPOST200(self.DELETE_ACTIVITY_URL, data={'id': activity.id}, follow=True)
        self.assertDoesNotExist(activity)

    @skipIfCustomActivity
    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_activity__forbidden(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task    = self.create_task(project, 'arms')
        worker  = self.create_user().linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(user=user, resource=resource)
        activity = task.related_activities[0]

        response = self.client.post(
            self.DELETE_ACTIVITY_URL, data={'id': activity.id}, follow=True,
        )
        self.assertContains(
            response,
            _('The definitive deletion has been disabled by the administrator.'),
            status_code=409,
            html=True,
        )
        self.assertStillExists(activity)
