# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial
from json import dumps as json_dump
from unittest import skipIf

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities.constants import (
    ACTIVITYSUBTYPE_MEETING_MEETING,
    ACTIVITYTYPE_MEETING,
    ACTIVITYTYPE_TASK,
    NARROW,
    REL_SUB_PART_2_ACTIVITY,
)
from creme.activities.models import Activity, Calendar
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui import actions
from creme.creme_core.models import Currency, SetCredentials
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.models import Contact
from creme.persons.tests.base import skipIfCustomContact

from . import (
    get_project_model,
    get_task_model,
    project_model_is_custom,
    task_model_is_custom,
)
from .actions import ProjectCloseAction
from .constants import (
    COMPLETED_PK,
    NOT_STARTED_PK,
    REL_OBJ_PROJECT_MANAGER,
    REL_SUB_LINKED_2_PTASK,
    REL_SUB_PART_AS_RESOURCE,
    REL_SUB_PROJECT_MANAGER,
)
from .models import ProjectStatus, Resource, TaskStatus

skip_projects_tests = project_model_is_custom()
skip_tasks_tests = task_model_is_custom()

Project = get_project_model()
ProjectTask = get_task_model()


def skipIfCustomProject(test_func):
    return skipIf(skip_projects_tests, 'Custom Project model in use')(test_func)


def skipIfCustomTask(test_func):
    return skipIf(skip_tasks_tests, 'Custom ProjectTask model in use')(test_func)


@skipIfCustomContact
@skipIfCustomProject
class ProjectsTestCase(CremeTestCase):
    EXTRA_LEADERS_KEY = 'cform_extra-projects_leaders'
    EXTRA_PARENTTASKS_KEY = 'cform_extra-projects_parent_tasks'
    DELETE_RESOURCE_URL = reverse('projects__delete_resource')
    DELETE_ACTIVITY_URL = reverse('projects__delete_activity')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ADD_PROJECT_URL = reverse('projects__create_project')

    def login(self, is_superuser=True, allowed_apps=('projects',), *args, **kwargs):
        return super().login(
            is_superuser, allowed_apps=allowed_apps, *args, **kwargs
        )

    @staticmethod
    def _build_add_task_url(project):
        return reverse('projects__create_task', args=(project.id,))

    @staticmethod
    def _build_add_parent_task_url(task):
        return reverse('projects__add_parent_task', args=(task.id,))

    @staticmethod
    def _build_add_resource_url(task):
        return reverse('projects__create_resource', args=(task.id,))

    @staticmethod
    def _build_add_activity_url(task):
        return reverse('projects__create_activity', args=(task.id,))

    @staticmethod
    def _build_edit_activity_url(activity):
        return reverse('projects__edit_activity', args=(activity.id,))

    @staticmethod
    def _build_type_value(atype=ACTIVITYTYPE_TASK, sub_type=None):
        return json_dump({'type': atype, 'sub_type': sub_type})

    def create_resource(self, task, contact, hourly_cost=100, error=False):
        response = self.client.post(
            self._build_add_resource_url(task),
            follow=True,
            data={
                'user':        self.user.id,
                'contact':     contact.id,
                'hourly_cost': hourly_cost,
            },
        )

        if not error:
            self.assertNoFormError(response)

        return response

    def create_activity(self, resource, start='2015-05-19', end='2015-06-03',
                        duration='8', atype=None, busy='', errors=False):
        response = self.client.post(
            self._build_add_activity_url(resource.task), follow=True,
            data={
                'resource':      resource.linked_contact_id,
                'start':         start,
                'end':           end,
                'duration':      duration,
                'type_selector': atype or self._build_type_value(),
                'user':          self.user.id,
                'busy':          busy,
            },
        )

        if not errors:
            self.assertNoFormError(response)

        return response

    def test_populate(self):
        self.get_relationtype_or_fail(
            REL_SUB_PROJECT_MANAGER,
            sub_models=[Contact], obj_models=[Project],
        )

        status_count = TaskStatus.objects.count()
        self.assertGreaterEqual(status_count, 2)
        self.assertEqual(status_count, TaskStatus.objects.order_by('-order')[0].order)

        pstatus_orders = [*ProjectStatus.objects.values_list('order', flat=True)]
        self.assertTrue(pstatus_orders)
        self.assertTrue(range(len(pstatus_orders) + 1), pstatus_orders)

    def create_project(self, name,
                       status=None, start_date='2010-10-11', end_date='2010-12-31'):
        status = status or ProjectStatus.objects.all()[0]
        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        currency = Currency.objects.all()[0]
        response = self.client.post(
            self.ADD_PROJECT_URL, follow=True,
            data={
                'user':         self.user.pk,
                'name':         name,
                'status':       status.id,
                'currency':     currency.id,
                'start_date':   start_date,
                'end_date':     end_date,

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Project, name=name), manager

    def create_task(self, project, title,
                    status=None, atype=ACTIVITYTYPE_TASK, sub_type=None):
        status = status or TaskStatus.objects.get(pk=NOT_STARTED_PK)
        response = self.client.post(
            self._build_add_task_url(project), follow=True,
            data={
                'user':          self.user.id,
                'title':         title,
                'start':         '2010-10-11',
                'end':           '2010-10-30',
                'duration':      50,
                'tstatus':       status.id,
                'type_selector': self._build_type_value(atype, sub_type),
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ProjectTask, linked_project=project, title=title)

    def test_project_detailview(self):
        self.login()

        status = ProjectStatus.objects.all()[0]
        project = self.create_project('Eva00', status, '2010-10-11', '2010-12-31')[0]
        response = self.assertGET200(project.get_absolute_url())
        self.assertTemplateUsed(response, 'projects/view_project.html')

    def test_project_createview01(self):
        user = self.login()

        self.assertGET200(self.ADD_PROJECT_URL)

        name = 'Eva00'
        status = ProjectStatus.objects.all()[0]
        project, manager = self.create_project(name, status, '2010-10-11', '2010-12-31')
        self.assertEqual(user,   project.user)
        self.assertEqual(name,   project.name)
        self.assertEqual(status, project.status)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=10, day=11), project.start_date)
        self.assertEqual(create_dt(year=2010, month=12, day=31), project.end_date)

        self.assertRelationCount(1, project, REL_OBJ_PROJECT_MANAGER, manager)

    def test_project_createview02(self):
        "Credentials error."
        user = self.login(is_superuser=False, creatable_models=[Project])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not LINK
            set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        manager = Contact.objects.create(user=user, first_name='Gendo', last_name='Ikari')
        self.assertFalse(user.has_perm_to_link(manager))

        response = self.assertPOST200(
            self.ADD_PROJECT_URL,
            follow=True,
            data={
                'user':         user.pk,
                'name':         'Eva00',
                'status':       ProjectStatus.objects.all()[0].id,
                'start_date':   '2011-10-11',
                'end_date':     '2011-12-31',

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )
        self.assertFormError(
            response, 'form', self.EXTRA_LEADERS_KEY,
            _('Some entities are not linkable: {}').format(
                _('Entity #{id} (not viewable)').format(id=manager.id),
            ),
        )

    def test_project_createview03(self):
        "Validation error with start/end."
        user = self.login()

        manager = Contact.objects.create(user=user, first_name='Gendo', last_name='Ikari')
        response = self.assertPOST200(
            self.ADD_PROJECT_URL, follow=True,
            data={
                'user':         user.pk,
                'name':         'Eva00',
                'status':       ProjectStatus.objects.all()[0].id,
                'start_date':   '2012-2-16',
                'end_date':     '2012-2-15',

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )

        create_dt = self.create_datetime
        self.assertFormError(
            response, 'form', None,
            _('Start ({start}) must be before end ({end}).').format(
                start=date_format(create_dt(2012, 2, 16), 'DATE_FORMAT'),
                end=date_format(create_dt(2012, 2, 15), 'DATE_FORMAT'),
            ),
        )

    def test_project_listview(self):
        self.login()

        self.create_project('Eva00')
        self.create_project('Eva01')
        self.assertGET200(reverse('projects__list_projects'))

    def test_listview_instance_actions(self):
        user = self.login()
        project = self.create_project('Eva00')[0]

        project_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=project)
            if isinstance(action, ProjectCloseAction)
        ]
        self.assertEqual(1, len(project_actions))

        close_action = project_actions[0]
        self.assertEqual('projects-close', close_action.type)
        self.assertEqual(
            reverse('projects__close_project', args=(project.id,)),
            close_action.url,
        )
        self.assertTrue(close_action.is_enabled)
        self.assertTrue(close_action.is_visible)

    def test_listview_instance_actions_closed(self):
        user = self.login()
        project = self.create_project('Eva00', start_date='2012-2-16', end_date='2012-3-26')[0]
        project.effective_end_date = now()
        project.save()

        self.assertTrue(project.is_closed)

        project_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=project)
            if isinstance(action, ProjectCloseAction)
        ]
        self.assertEqual(1, len(project_actions))

        close_action = project_actions[0]
        self.assertEqual('projects-close', close_action.type)
        self.assertEqual(
            reverse('projects__close_project', args=(project.id,)),
            close_action.url,
        )
        self.assertFalse(close_action.is_enabled)
        self.assertTrue(close_action.is_visible)

    def test_project_inner_edit01(self):
        self.login()

        project = self.create_project('Eva01', start_date='2012-2-16', end_date='2012-3-26')[0]
        url = self.build_inneredit_url(project, 'start_date')
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities_lbl': [str(project)],
                'field_value':  '2012-3-4',
            },
        ))
        self.assertEqual(
            self.create_datetime(year=2012, month=3, day=4),
            self.refresh(project).start_date,
        )

    def test_project_inner_edit02(self):
        "Validation error."
        self.login()

        project = self.create_project(
            'Eva01', start_date='2012-02-20', end_date='2012-03-25',
        )[0]
        response = self.assertPOST200(
            self.build_inneredit_url(project, 'start_date'),
            data={
                'entities_lbl': [str(project)],
                'field_value':  '2012-03-27',  # <= after end_date
            },
        )

        create_dt = self.create_datetime
        self.assertFormError(
            response, 'form', None,
            _('Start ({start}) must be before end ({end}).').format(
                start=date_format(create_dt(2012, 3, 27), 'DATE_FORMAT'),
                end=date_format(create_dt(2012, 3, 25), 'DATE_FORMAT'),
            ),
        )
        self.assertEqual(
            create_dt(year=2012, month=2, day=20),
            self.refresh(project).start_date,
        )

    @skipIfCustomTask
    def test_task_createview01(self):
        "Create 2 tasks without collision."
        user = self.login()
        project = self.create_project('Eva01')[0]

        url = self._build_add_task_url(project)

        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a task for «{entity}»').format(entity=project),
            context.get('title'),
        )
        self.assertEqual(ProjectTask.save_label, context.get('submit_label'))

        # ---
        tstatus = TaskStatus.objects.all()[0]
        title = 'head'

        def post(duration):
            return self.client.post(
                url,
                follow=True,
                data={
                    'user':     user.id,
                    'title':    title,
                    'start':    '2010-10-11 15:00',
                    'end':      '2010-10-11 17:00',
                    'duration': duration,
                    'tstatus':  tstatus.id,
                },
            )

        response = post('')
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'duration', _('This field is required.'))

        duration_1 = 50
        response = post(duration_1)
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(linked_project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(title,   task1.title)
        self.assertEqual(1,       task1.order)
        self.assertEqual(tstatus, task1.tstatus)

        duration_2 = 180
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':     user.id,
                'title':    'torso',
                'start':    '2010-10-11 17:01',
                'end':      '2010-10-11 17:30',
                'duration': duration_2,
                'tstatus':  TaskStatus.objects.all()[0].id,

                self.EXTRA_PARENTTASKS_KEY: self.formfield_value_multi_creator_entity(task1),
            },
        )
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(linked_project=project)
        self.assertEqual(2, tasks.count())

        tasks2 = [t for t in tasks if t.id != task1.id]
        self.assertEqual(1, len(tasks2))

        task2 = tasks2[0]
        self.assertListEqual([task1.id], [t.id for t in task2.parent_tasks.all()])

        self.assertSetEqual({*tasks}, {*project.get_tasks()})
        self.assertEqual(duration_1 + duration_2, project.get_expected_duration())

    @skipIfCustomTask
    def test_task_createview02(self):
        "Can not be parented with task of an other project + not super-user."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'projects'],
            creatable_models=[Project, ProjectTask],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Title')
        response = self.client.post(
            self._build_add_task_url(project02),
            data={
                'user':     user.id,
                'title':    'head',
                'start':    '2010-10-11',
                'end':      '2010-10-30',
                'duration': 50,
                'tstatus':  TaskStatus.objects.all()[0].id,

                self.EXTRA_PARENTTASKS_KEY: self.formfield_value_multi_creator_entity(task01),
            },
        )
        self.assertFormError(
            # response, 'form', self.EXTRA_PARENTTASKS_KEY, _('This entity does not exist.'),
            response, 'form', self.EXTRA_PARENTTASKS_KEY,
            _('«%(entity)s» violates the constraints.') % {'entity': task01},
        )

    def test_task_createview03(self):
        "Not allowed to create a task."
        self.login(
            is_superuser=False, allowed_apps=['persons', 'projects'],
            creatable_models=[Project],  # ProjectTask
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project = self.create_project('Eva01')[0]
        self.assertGET403(self._build_add_task_url(project))

    @skipIfCustomTask
    def test_task_detailview(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')

        response = self.assertGET200(task.get_absolute_url())
        self.assertTemplateUsed(response, 'projects/view_task.html')

    @skipIfCustomTask
    def test_task_editview01(self):
        user = self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')
        url = task.get_edit_absolute_url()
        self.assertGET200(url)

        title = 'Head'
        duration = 55
        tstatus = TaskStatus.objects.all()[1]
        response = self.client.post(
            url, follow=True,
            data={
                'user':     user.id,
                'title':    title,
                'start':    '2011-5-16',
                'end':      '2012-6-17',
                'duration': duration,
                'tstatus':  tstatus.id,
            },
        )
        self.assertNoFormError(response)

        task = self.refresh(task)
        self.assertEqual(title,    task.title)
        self.assertEqual(duration, task.duration)
        self.assertEqual(tstatus,  task.tstatus)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2011, month=5, day=16), task.start)
        self.assertEqual(create_dt(year=2012, month=6, day=17), task.end)

    @skipIfCustomTask
    def test_task_editview_popup01(self):
        "Popup version."
        user = self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')
        url = reverse('projects__edit_task_popup', args=(task.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        # ---
        title = 'Head'
        duration = 55
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':     user.id,
                'title':    title,
                'start':    '2011-5-16',
                'end':      '2012-6-17',
                'duration': duration,
                'tstatus':  TaskStatus.objects.all()[0].id,
            },
        )
        self.assertNoFormError(response)

        task = self.refresh(task)
        self.assertEqual(title,    task.title)
        self.assertEqual(duration, task.duration)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2011, month=5, day=16), task.start)
        self.assertEqual(create_dt(year=2012, month=6, day=17), task.end)

    @skipIfCustomTask
    def test_task_add_parent01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Parent01')
        task02 = self.create_task(project, 'Parent02')
        task03 = self.create_task(project, 'Task')

        url = self._build_add_parent_task_url(task03)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Adding parents to «{object}»').format(object=task03),
            response.context.get('title'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'parents': self.formfield_value_multi_creator_entity(task01, task02)},
        ))
        self.assertSetEqual({task01, task02}, {*task03.parent_tasks.all()})

        self.assertPOST200(
            reverse('projects__remove_parent_task'),
            data={'id': task03.id, 'parent_id': task01.id},
            follow=True,
        )
        self.assertListEqual([task02], [*task03.parent_tasks.all()])

        # Error: already parent
        self.assertFormError(
            self.client.post(
                url,
                data={'parents': self.formfield_value_multi_creator_entity(task02)},
            ),
            # 'form', 'parents', _('This entity does not exist.'),
            'form', 'parents', _('«%(entity)s» violates the constraints.') % {'entity': task02},
        )

    @skipIfCustomTask
    def test_task_add_parent02(self):
        "Error task that belongs to another project."
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Task01')
        task02 = self.create_task(project02, 'Task02')

        response = self.client.post(
            self._build_add_parent_task_url(task02),
            data={'parents': self.formfield_value_multi_creator_entity(task01)},
        )
        self.assertFormError(
            # response, 'form', 'parents', _('This entity does not exist.'),
            response, 'form', 'parents',
            _('«%(entity)s» violates the constraints.') % {'entity': task01},
        )

    @skipIfCustomTask
    def test_task_add_parent03(self):
        "Cycle error."
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Task01')
        task02 = self.create_task(project, 'Task02')
        task03 = self.create_task(project, 'Task03')

        self.assertEqual([task01], [*task01.get_subtasks()])

        build_url = self._build_add_parent_task_url
        field_value = self.formfield_value_multi_creator_entity
        self.assertNoFormError(self.client.post(
            build_url(task02), data={'parents': field_value(task01)},
        ))
        self.assertSetEqual({task01, task02}, {*task01.get_subtasks()})

        self.assertNoFormError(self.client.post(
            build_url(task03), data={'parents': field_value(task02)},
        ))
        self.assertSetEqual({task01, task02, task03}, {*task01.get_subtasks()})

        response = self.client.post(
            build_url(task01), data={'parents': field_value(task03)},
        )
        # self.assertFormError(response, 'form', 'parents', _('This entity does not exist.'))
        self.assertFormError(
            response, 'form', 'parents',
            _('«%(entity)s» violates the constraints.') % {'entity': task03},
        )

    @skipIfCustomTask
    def test_duration01(self):
        self.login()
        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')

        self.assertEqual(50, task.duration)
        # self.assertEqual(50, task.safe_duration)

        self.assertEqual(0, task.get_effective_duration())
        self.assertEqual(0, task.get_effective_duration('%'))

        self.assertEqual(-50, task.get_delay())
        self.assertEqual(50, project.get_expected_duration())

    @skipIfCustomTask
    def test_duration02(self):
        self.login()
        project = self.create_project('Eva01')[0]

        task = self.create_task(project, 'Title')
        # task.duration = None
        task.duration = 0
        task.save()

        # self.assertEqual(0, task.safe_duration)

        self.assertEqual(0,   task.get_effective_duration())
        self.assertEqual(100, task.get_effective_duration('%'))

        self.assertEqual(0, task.get_delay())
        self.assertEqual(0, project.get_expected_duration())

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity01(self):
        "Creation views."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'legs')
        self.assertFalse(task.resources_set.all())

        response = self.assertGET200(self._build_add_resource_url(task))
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Allocation of a new resource'), context.get('title'))
        self.assertEqual(Resource.save_label,               context.get('submit_label'))
        # ---
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        self.create_resource(task, worker, hourly_cost=100)

        resources = [*task.resources_set.all()]
        self.assertEqual(1, len(resources))
        resource = resources[0]

        context = self.assertGET200(self._build_add_activity_url(task)).context
        self.assertEqual(
            _('New activity related to «{entity}»').format(entity=task),
            context.get('title'),
        )
        self.assertEqual(Activity.save_label, context.get('submit_label'))

        atype = ACTIVITYTYPE_MEETING
        stype = ACTIVITYSUBTYPE_MEETING_MEETING
        self.create_activity(resource, duration='8', atype=self._build_type_value(atype, stype))

        activity = self.get_object_or_fail(Activity, title='Eva02 - legs - 001')

        self.assertEqual(atype, activity.type_id)
        self.assertEqual(stype, activity.sub_type_id)
        self.assertEqual(NARROW, activity.floating_type)
        self.assertEqual(8, activity.duration)
        self.assertFalse(activity.busy)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2015, month=5, day=19), activity.start)
        self.assertEqual(create_dt(year=2015, month=6, day=3),  activity.end)

        self.assertRelationCount(1, activity, REL_SUB_LINKED_2_PTASK, task)
        self.assertRelationCount(1, worker, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker, REL_SUB_PART_AS_RESOURCE, activity)

        self.assertEqual(8,   task.get_effective_duration())
        self.assertEqual(800, task.get_task_cost())  # 8 * 100
        self.assertEqual(-42, task.get_delay())  # 8 - 50
        self.assertTrue(task.is_alive())

        self.assertEqual(8,   project.get_effective_duration())
        self.assertEqual(800, project.get_project_cost())  # 8 * 100
        self.assertEqual(0,   project.get_delay())

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity02(self):
        "Edition views + Calendar."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(resource)

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

        activities = task.related_activities
        self.assertEqual(1, len(activities))

        activity = activities[0]
        self.assertListEqual(
            [Calendar.objects.get_default_calendar(self.other_user)],
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
                'start':         '2010-10-11',
                'end':           '2010-10-12',
                'duration':      10,
                'user':          user.id,
                'type_selector': self._build_type_value(),
            },
        )
        self.assertNoFormError(response)

        activity = self.refresh(activity)
        self.assertEqual(10, activity.duration)
        self.assertRelationCount(1, worker, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker, REL_SUB_PART_AS_RESOURCE, activity)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity03(self):
        "Not alive task."
        user = self.login()

        project = self.create_project('Eva02')[0]
        status = self.get_object_or_fail(TaskStatus, id=COMPLETED_PK)
        task = self.create_task(project, 'legs', status=status)

        self.assertGET409(self._build_add_resource_url(task))

        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        response = self.create_resource(task, worker, error=True)
        self.assertFalse(task.resources_set.all())
        self.assertEqual(409, response.status_code)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity04(self):
        "Create 2 activities with a collision."
        user = self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'arms')
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(resource, '2010-10-11 15:00', '2010-10-11 17:00', busy='on')
        act1 = task.related_activities[0]
        self.assertTrue(act1.busy)

        response = self.create_activity(
            resource, '2010-10-11 16:59', '2010-10-11 17:30', busy='on', errors=True,
        )
        self.assertEqual(1, len(self.refresh(task).related_activities))
        self.assertFormError(
            response, 'form', None,
            _(
                '{participant} already participates to the activity '
                '«{activity}» between {start} and {end}.'
            ).format(
                participant=worker,
                activity=act1,
                start='16:59:00',
                end='17:00:00',
            ),
        )

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity05(self):
        "Edition of activity: resource changes."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker1 = self.other_user.linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker1)
        self.create_resource(task, worker2)

        data = {
            'resource':      worker1.id,
            'start':         '2015-05-21',
            'end':           '2015-05-22',
            'duration':      10,
            'user':          user.id,
            'type_selector': self._build_type_value(),
        }
        self.client.post(self._build_add_activity_url(task), follow=True, data=data)
        activities = task.related_activities
        self.assertEqual(1, len(activities))

        activity = activities[0]
        self.assertListEqual(
            [Calendar.objects.get_default_calendar(self.other_user)],
            [*activity.calendars.all()],
        )

        response = self.client.post(
            self._build_edit_activity_url(activity),
            follow=True,
            data={**data, 'resource': worker2.id},
        )
        self.assertNoFormError(response)

        self.assertRelationCount(1, worker2, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker2, REL_SUB_PART_AS_RESOURCE, activity)

        self.assertRelationCount(0, worker1, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(0, worker1, REL_SUB_PART_AS_RESOURCE, activity)

        # Alright the project Activities can be on no Calendar
        self.assertFalse(activity.calendars.all())

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity06(self):
        "Edition of activity: resource changes + keep_participating."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker1 = self.other_user.linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker1)
        self.create_resource(task, worker2)

        data = {
            'resource':      worker1.id,
            'start':         '2015-05-21',
            'end':           '2015-05-22',
            'duration':      10,
            'user':          user.id,
            'type_selector': self._build_type_value(),
        }
        self.client.post(self._build_add_activity_url(task), follow=True, data=data)
        activities = task.related_activities
        self.assertEqual(1, len(activities))

        activity = activities[0]
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

        self.assertRelationCount(1, worker2, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker2, REL_SUB_PART_AS_RESOURCE, activity)

        self.assertRelationCount(1, worker1, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(0, worker1, REL_SUB_PART_AS_RESOURCE, activity)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(self.other_user)],
            [*activity.calendars.all()],
        )

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity07(self):
        "Resource must ne related to the task."
        user = self.login()

        project = self.create_project('Eva01')[0]

        task1 = self.create_task(project, 'Legs')
        task2 = self.create_task(project, 'Head')

        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        self.create_resource(task1, worker, hourly_cost=100)

        resources = [*task1.resources_set.all()]
        self.assertEqual(1, len(resources))
        # resource1 = resources[0]

        response = self.assertPOST200(
            self._build_add_activity_url(task2), follow=True,
            data={
                'resource':      worker.id,
                'start':         '2016-05-19',
                'end':           '2016-06-03',
                'duration':      8,
                'type_selector': self._build_type_value(),
                'user':          user.id,
            },
        )
        self.assertFormError(
            # response, 'form', 'resource', _('This entity does not exist.'),
            response, 'form', 'resource',
            _('«%(entity)s» violates the constraints.') % {'entity': worker},
        )

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity08(self):
        "Creation credentials are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'projects'],
            creatable_models=[Project, ProjectTask],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'legs')
        url = self._build_add_activity_url(task)
        self.assertGET403(url)

        self.role.creatable_ctypes.add(ContentType.objects.get_for_model(Activity))
        self.assertGET200(url)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_resource_n_activity09(self):
        "Posted contacts must be resources."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        contact = self.other_user.linked_contact
        response = self.assertPOST200(
            self._build_add_activity_url(task),
            follow=True,
            data={
                'resource':      contact.id,
                'start':         '2020-09-14',
                'end':           '2020-12-31',
                'duration':      100,
                'user':          user.id,
                'type_selector': self._build_type_value(),
            },
        )
        self.assertFormError(
            # response, 'form', 'resource', _('This entity does not exist.'),
            response, 'form', 'resource',
            _('«%(entity)s» violates the constraints.') % {'entity': contact},
        )

    @skipIfCustomTask
    def test_create_resource01(self):
        "Not super-user."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_ALL,
            ctype=Project,
        )

        project = Project.objects.create(
            user=user,
            name='Eva02',
            status=ProjectStatus.objects.first(),
        )
        now_value = now()
        task = ProjectTask.objects.create(
            user=user,
            linked_project=project,
            title='legs',
            tstatus=TaskStatus.objects.get(pk=NOT_STARTED_PK),
            start=now_value,
            end=now_value + timedelta(days=3),
            duration=21,
        )
        self.assertTrue(user.has_perm_to_change(task))
        self.assertGET200(self._build_add_resource_url(task))

    @skipIfCustomTask
    def test_create_resource02(self):
        "Edition permission needed."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,  # | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_ALL,
            ctype=Project,
        )

        project = Project.objects.create(
            user=user,
            name='Eva02',
            status=ProjectStatus.objects.first(),
        )
        now_value = now()
        task = ProjectTask.objects.create(
            user=user,
            linked_project=project,
            tstatus=TaskStatus.objects.get(pk=NOT_STARTED_PK),
            start=now_value,
            end=now_value + timedelta(days=3),
            duration=21,
        )
        self.assertGET403(self._build_add_resource_url(task))

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_edit_resource01(self):
        "Related contact participates to activities."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task1 = self.create_task(project, 'arms')
        task2 = self.create_task(project, 'legs')

        worker1 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        worker2 = self.other_user.linked_contact

        self.create_resource(task1, worker1)
        resource1 = task1.resources_set.all()[0]
        self.create_activity(resource1)

        self.create_resource(task2, worker1)
        resource2 = task2.resources_set.all()[0]
        self.create_activity(resource2)

        url = resource1.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Resource for «{entity}»').format(entity=task1),
            response.context.get('title'),
        )

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.id,
                'contact':     worker2.id,
                'hourly_cost': 200,
            },
        )
        self.assertNoFormError(response)

        resource1 = self.refresh(resource1)
        self.assertEqual(worker2, resource1.linked_contact)

        # activity of the resource => changes
        activities1 = task1.related_activities
        self.assertEqual(1, len(activities1))
        activity1 = activities1[0]

        self.assertRelationCount(1, worker2, REL_SUB_PART_2_ACTIVITY, activity1)
        self.assertRelationCount(1, worker2, REL_SUB_PART_AS_RESOURCE, activity1)

        self.assertRelationCount(0, worker1, REL_SUB_PART_2_ACTIVITY, activity1)
        self.assertRelationCount(0, worker1, REL_SUB_PART_AS_RESOURCE, activity1)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(self.other_user)],
            [*activity1.calendars.all()],
        )

        # activity of the other resource => no change
        activities2 = task2.related_activities
        self.assertEqual(1, len(activities2))
        activity2 = activities2[0]

        self.assertRelationCount(1, worker1, REL_SUB_PART_2_ACTIVITY, activity2)
        self.assertRelationCount(1, worker1, REL_SUB_PART_AS_RESOURCE, activity2)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_edit_resource02(self):
        "Related contact participates to activities: old resource continues to participate."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')

        worker1 = user.linked_contact
        worker2 = self.other_user.linked_contact

        self.create_resource(task, worker1)
        resource1 = task.resources_set.all()[0]
        self.create_activity(resource1)

        response = self.client.post(
            resource1.get_edit_absolute_url(),
            follow=True,
            data={
                'user':               user.id,
                'contact':            worker2.id,
                'hourly_cost':        200,
                'keep_participating': 'on',
            },
        )
        self.assertNoFormError(response)

        resource1 = self.refresh(resource1)
        self.assertEqual(worker2, resource1.linked_contact)

        activities = task.related_activities
        self.assertEqual(1, len(activities))
        activity = activities[0]

        self.assertRelationCount(1, worker2, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker2, REL_SUB_PART_AS_RESOURCE, activity)

        self.assertRelationCount(1, worker1, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(0, worker1, REL_SUB_PART_AS_RESOURCE, activity)

        get_cal = Calendar.objects.get_default_calendar
        self.assertSetEqual(
            {get_cal(user), get_cal(self.other_user)},
            {*activity.calendars.all()},
        )

    @skipIfCustomTask
    def test_project_close(self):
        self.login()

        project = self.create_project('Eva01')[0]
        self.assertFalse(project.is_closed)
        self.assertIsNone(project.effective_end_date)

        url = reverse('projects__close_project', args=(project.id,))
        self.assertGET405(url)
        self.assertPOST200(url, follow=True)

        project = self.refresh(project)
        self.assertTrue(project.is_closed)
        self.assertTrue(project.effective_end_date)

        self.assertDatetimesAlmostEqual(now(), project.effective_end_date)

        # Already closed
        self.assertPOST409(url, follow=True)

    def _create_parented_task(self, title, project, parents=None):
        status = TaskStatus.objects.get_or_create(name='status', description='')[0]
        now_value = now()
        task = ProjectTask.objects.create(
            linked_project=project,
            order=0, duration=0,
            tstatus=status, title=title,
            user=self.user,
            start=now_value,
            end=now_value + timedelta(hours=1),
        )

        if parents is not None:
            task.parent_tasks.set(parents)

        return task

    @staticmethod
    def _titles_collections(tasks_qs, constructor):
        return constructor(tasks_qs.values_list('title', flat=True))

    def _titles_list(self, tasks_qs):
        return self._titles_collections(tasks_qs, list)

    def _titles_set(self, tasks_qs):
        return self._titles_collections(tasks_qs, set)

    @staticmethod
    def _tasks_pk_set(project):
        return {*project.get_tasks().values_list('pk', flat=True)}

    @skipIfCustomTask
    def test_project_clone01(self):
        self.login()
        project = self.create_project('Project')[0]

        create_task = self._create_parented_task
        task1    = create_task('1', project)
        task11   = create_task('1.1', project, [task1])
        task111  = create_task('1.1.1', project, [task11])
        task1111 = create_task('1.1.1.1', project, [task111])
        create_task('all 1', project, [task1, task11, task111, task1111])

        task2 = create_task('2', project)
        create_task('all 2', project, [task1, task11, task111, task1111, task2])

        cloned_project = project.clone()

        titles_list = self._titles_list
        titles_set = self._titles_set
        self.assertSetEqual(
            {'1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2'},
            titles_set(cloned_project.get_tasks()),
        )

        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        get_task = cloned_project.get_tasks().get
        self.assertFalse(get_task(title='1').get_parents())
        self.assertListEqual(['1'],     titles_list(get_task(title='1.1').get_parents()))
        self.assertListEqual(['1.1'],   titles_list(get_task(title='1.1.1').get_parents()))
        self.assertListEqual(['1.1.1'], titles_list(get_task(title='1.1.1.1').get_parents()))
        self.assertSetEqual(
            {'1', '1.1', '1.1.1', '1.1.1.1'},
            titles_set(get_task(title='all 1').get_parents()),
        )
        self.assertFalse(get_task(title='2').get_parents())
        self.assertSetEqual(
            {'1', '1.1', '1.1.1', '1.1.1.1', '2'},
            titles_set(get_task(title='all 2').get_parents()),
        )

    @skipIfCustomTask
    def test_project_clone02(self):
        user = self.login()

        project = self.create_project('Project')[0]
        contact1 = Contact.objects.create(user=user)
        contact2 = Contact.objects.create(user=user)

        create_resource = Resource.objects.create

        task1 = self._create_parented_task('1', project)
        create_resource(linked_contact=contact1, task=task1)
        create_resource(linked_contact=contact2, task=task1)

        task2 = self._create_parented_task('2', project)
        create_resource(linked_contact=contact1, task=task2)
        create_resource(linked_contact=contact2, task=task2)

        task3 = self._create_parented_task('3', project, [task1, task2])
        self._create_parented_task('4', project, [task3])

        cloned_project = project.clone()

        for attr in [
            'name', 'description', 'status', 'start_date', 'end_date', 'effective_end_date',
        ]:
            self.assertEqual(getattr(project, attr), getattr(cloned_project, attr))

        get_task = cloned_project.get_tasks().get
        c_task1 = get_task(title='1')
        c_task2 = get_task(title='2')

        self.assertEqual({'1', '2', '3', '4'}, self._titles_set(cloned_project.get_tasks()))
        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        self.assertSetEqual({'1', '2'}, self._titles_set(get_task(title='3').get_parents()))
        self.assertListEqual(['3'], self._titles_list(get_task(title='4').get_parents()))

        def linked_contacts_set(task):
            return {*task.get_resources().values_list('linked_contact', flat=True)}

        self.assertSetEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task1))
        self.assertSetEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task2))

    @skipIfCustomTask
    def test_delete_project_status(self):
        self.login()

        status2 = ProjectStatus.objects.first()
        status = ProjectStatus.objects.create(name='Sinking')
        project = self.create_project('Project', status=status)[0]
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('projects', 'projectstatus', status.id),
            ),
            data={'replace_projects__project_status': status2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(ProjectStatus).job
        job.type.execute(job)
        self.assertDoesNotExist(status)

        project = self.assertStillExists(project)
        self.assertEqual(status2, project.status)

    @skipIfCustomTask
    def test_delete_task_status(self):
        self.login()

        project = self.create_project('Eva01')[0]
        status2 = TaskStatus.objects.first()
        status1 = TaskStatus.objects.create(name='Coming soon')
        task = self.create_task(project, 'Building head', status=status1)
        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('projects', 'taskstatus', status1.id),
            ),
            data={'replace_projects__projecttask_tstatus': status2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(TaskStatus).job
        job.type.execute(job)
        self.assertDoesNotExist(status1)

        self.assertStillExists(project)
        task = self.assertStillExists(task)
        self.assertEqual(status2, task.tstatus)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_task_cost_n_duration(self):
        "With several activities."
        user = self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'legs')

        create_contact = partial(Contact.objects.create, user=user)
        worker1 = create_contact(first_name='Yui',     last_name='Ikari')
        worker2 = create_contact(first_name='Ritsuko', last_name='Akagi')

        self.create_resource(task, worker1, 100)
        self.create_resource(task, worker2, 150)

        resources = {res.linked_contact_id: res for res in task.resources_set.all()}
        self.assertEqual(2, len(resources))

        with self.assertNoException():
            resource1 = resources[worker1.id]
            resource2 = resources[worker2.id]

        self.create_activity(resource1, duration=8)
        self.create_activity(resource2, duration=3)

        self.assertEqual(8 + 3, task.get_effective_duration())

        cost = task.get_task_cost()
        self.assertEqual(8 * 100 + 3 * 150, cost)
        self.assertEqual(cost, project.get_project_cost())

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_activity_title(self):
        user = self.login()

        project = self.create_project('Eva00')[0]
        task = self.create_task(project, 'head')
        worker = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task, worker)
        resource = task.get_resources()[0]

        self.create_activity(resource, '2015-05-20', '2015-05-21')
        self.create_activity(resource, '2015-05-22', '2015-05-23')
        self.assertSetEqual(
            {'Eva00 - head - 001', 'Eva00 - head - 002'},
            {a.title for a in task.related_activities},
        )

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_resource01(self):
        "No related activity"
        user = self.login()

        project = self.create_project('Eva02')[0]
        task1 = self.create_task(project, 'arms')
        task2 = self.create_task(project, 'legs')
        worker1 = self.other_user.linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task1, worker1)
        resource1 = task1.resources_set.all()[0]

        self.create_resource(task1, worker2)
        resource2 = task1.resources_set.exclude(pk=resource1.id)[0]

        self.create_resource(task2, worker1)
        resource3 = task2.resources_set.all()[0]

        self.create_activity(resource2)
        activity = task1.related_activities[0]

        # This activity is linked to the same contact, but not the same resource
        # so it should not avoid the deletion of resource1
        self.create_activity(resource3)

        url = self.DELETE_RESOURCE_URL
        data = {'id': resource1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertDoesNotExist(resource1)

        self.assertRelationCount(1, worker2, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertRelationCount(1, worker2, REL_SUB_PART_AS_RESOURCE, activity)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_resource02(self):
        "Related activity => 409."
        self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(resource)
        activity = task.related_activities[0]

        self.assertPOST409(self.DELETE_RESOURCE_URL, data={'id': resource.id})
        self.assertStillExists(resource)

        self.assertRelationCount(1, worker, REL_SUB_PART_2_ACTIVITY,  activity)
        self.assertRelationCount(1, worker, REL_SUB_PART_AS_RESOURCE, activity)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_resource03(self):
        "Not super-user."
        self.login(
            is_superuser=False, allowed_apps=['persons', 'projects'],
            creatable_models=[Project, ProjectTask],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.assertPOST200(self.DELETE_RESOURCE_URL, data={'id': resource.id}, follow=True)
        self.assertDoesNotExist(resource)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_resource04(self):
        "Not super-user + cannot change the task => error."
        self.login(
            is_superuser=False, allowed_apps=['persons', 'projects'],
            creatable_models=[Project, ProjectTask],
        )
        creds = SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        creds.value = EntityCredentials.VIEW | EntityCredentials.LINK
        creds.save()
        self.assertPOST403(self.DELETE_RESOURCE_URL, data={'id': resource.id})

    @skipIfCustomActivity
    def test_edit_activity_error(self):
        "Activity not related to a project task."
        user = self.login()

        activity = Activity.objects.create(
            user=user, title='My task', type_id=ACTIVITYTYPE_TASK,
        )
        self.assertGET409(self._build_edit_activity_url(activity))

    @skipIfCustomActivity
    def test_delete_activity01(self):
        "Activity not related to a project task."
        user = self.login()

        activity = Activity.objects.create(
            user=user, title='My task', type_id=ACTIVITYTYPE_TASK,
        )
        url = self.DELETE_ACTIVITY_URL
        data = {'id': activity.id}
        self.assertGET405(url, data=data)
        self.assertPOST409(url, data=data)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_activity02(self):
        "Activity not related to a project task."
        self.login()

        project = self.create_project('Eva02')[0]
        task    = self.create_task(project, 'arms')
        worker  = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(resource)
        activity = task.related_activities[0]

        self.assertPOST200(self.DELETE_ACTIVITY_URL, data={'id': activity.id}, follow=True)
        self.assertDoesNotExist(activity)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete_task(self):
        self.login()

        project = self.create_project('Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.other_user.linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(resource)
        activity = task.related_activities[0]

        response = self.client.post(task.get_delete_absolute_url())
        self.assertDoesNotExist(task)
        self.assertDoesNotExist(resource)
        self.assertStillExists(activity)
        self.assertRedirects(response, project.get_absolute_url())

    # TODO: test better get_project_cost(), get_effective_duration(), get_delay()
