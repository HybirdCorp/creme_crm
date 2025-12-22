from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.activities.tests.base import skipIfCustomActivity
from creme.projects.models import TaskStatus
from creme.projects.tests.base import (
    Contact,
    Project,
    ProjectsTestCase,
    ProjectTask,
    skipIfCustomTask,
)


@skipIfCustomTask
class TaskTestCase(ProjectsTestCase):
    EXTRA_PARENTTASKS_KEY = 'cform_extra-projects_parent_tasks'

    @staticmethod
    def _build_add_parent_task_url(task):
        return reverse('projects__add_parent_task', args=(task.id,))

    def test_populate(self):
        status_count = TaskStatus.objects.count()
        self.assertGreaterEqual(status_count, 2)
        self.assertEqual(status_count, TaskStatus.objects.order_by('-order')[0].order)

    def test_creation(self):
        "Create 2 tasks without collision."
        user = self.login_as_root_and_get()
        project = self.create_project(user=user, name='Eva01')[0]

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
        dt_value = self.formfield_value_datetime

        def post(duration):
            return self.client.post(
                url,
                follow=True,
                data={
                    'user':     user.id,
                    'title':    title,
                    'start':    dt_value(year=2010, month=10, day=11, hour=15),
                    'end':      dt_value(year=2010, month=10, day=11, hour=17),
                    'duration': duration,
                    'tstatus':  tstatus.id,
                },
            )

        response1 = post('')
        self.assertEqual(200, response1.status_code)
        self.assertFormError(
            response1.context['form'],
            field='duration', errors=_('This field is required.'),
        )

        # ---
        duration_1 = 50
        response2 = post(duration_1)
        self.assertNoFormError(response2)

        tasks = ProjectTask.objects.filter(linked_project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(title,   task1.title)
        self.assertEqual(1,       task1.order)
        self.assertEqual(tstatus, task1.tstatus)

        # ---
        duration_2 = 180
        dt_value = self.formfield_value_datetime
        response3 = self.client.post(
            url,
            follow=True,
            data={
                'user':     user.id,
                'title':    'torso',
                'start':    dt_value(year=2010, month=10, day=11, hour=17, minute=1),
                'end':      dt_value(year=2010, month=10, day=11, hour=17, minute=30),
                'duration': duration_2,
                'tstatus':  TaskStatus.objects.all()[0].id,

                self.EXTRA_PARENTTASKS_KEY: self.formfield_value_multi_creator_entity(task1),
            },
        )
        self.assertNoFormError(response3)

        tasks = ProjectTask.objects.filter(linked_project=project)
        self.assertEqual(2, tasks.count())

        task2 = self.get_alone_element(t for t in tasks if t.id != task1.id)
        self.assertListEqual([task1.id], [t.id for t in task2.parent_tasks.all()])

        self.assertCountEqual(tasks, project.get_tasks())
        self.assertEqual(duration_1 + duration_2, project.get_expected_duration())

    def test_creation__different_project(self):
        "Can not be parented with task of another project + not super-user."
        user = self.login_as_projects_user(
            allowed_apps=['persons'],
            creatable_models=[Project, ProjectTask],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        project1 = self.create_project(user=user, name='Eva01')[0]
        project2 = self.create_project(user=user, name='Eva02')[0]

        task01 = self.create_task(project1, 'Title')
        response = self.client.post(
            self._build_add_task_url(project2),
            data={
                'user':     user.id,
                'title':    'head',
                'start':    self.formfield_value_date(2010, 10, 11),
                'end':      self.formfield_value_date(2010, 10, 30),
                'duration': 50,
                'tstatus':  TaskStatus.objects.all()[0].id,

                self.EXTRA_PARENTTASKS_KEY: self.formfield_value_multi_creator_entity(task01),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_PARENTTASKS_KEY,
            errors=_('«%(entity)s» violates the constraints.') % {'entity': task01},
        )

    def test_creation__creation_perms(self):
        "Not allowed to create a task."
        user = self.login_as_projects_user(
            allowed_apps=['persons'],
            creatable_models=[Project],  # ProjectTask
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        project = self.create_project(user=user, name='Eva01')[0]
        self.assertGET403(self._build_add_task_url(project))

    def test_detailview(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        task = self.create_task(project, 'Title')

        response = self.assertGET200(task.get_absolute_url())
        self.assertTemplateUsed(response, 'projects/view_task.html')

    def test_edition(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
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
                'start':    self.formfield_value_date(2011, 5, 16),
                'end':      self.formfield_value_date(2012, 6, 17),
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

    def test_edition__popup(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
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
                'start':    self.formfield_value_date(2011, 5, 16),
                'end':      self.formfield_value_date(2012, 6, 17),
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

    def test_add_parent(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        task1 = self.create_task(project, 'Parent01')
        task2 = self.create_task(project, 'Parent02')
        task3 = self.create_task(project, 'Task')

        url = self._build_add_parent_task_url(task3)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Adding parents to «{object}»').format(object=task3),
            response1.context.get('title'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'parents': self.formfield_value_multi_creator_entity(task1, task2)},
        ))
        self.assertCountEqual([task1, task2], task3.parent_tasks.all())

        # ---
        self.assertPOST200(
            reverse('projects__remove_parent_task'),
            data={'id': task3.id, 'parent_id': task1.id},
            follow=True,
        )
        self.assertListEqual([task2], [*task3.parent_tasks.all()])

        # Error: already parent
        response4 = self.assertPOST200(
            url,
            data={'parents': self.formfield_value_multi_creator_entity(task2)},
        )
        self.assertFormError(
            response4.context['form'],
            field='parents',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': task2},
        )

    def test_add_parent__different_project(self):
        "Error task that belongs to another project."
        user = self.login_as_root_and_get()

        project1 = self.create_project(user=user, name='Eva01')[0]
        project2 = self.create_project(user=user, name='Eva02')[0]

        task1 = self.create_task(project1, 'Task01')
        task2 = self.create_task(project2, 'Task02')

        response = self.assertPOST200(
            self._build_add_parent_task_url(task2),
            data={'parents': self.formfield_value_multi_creator_entity(task1)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='parents',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': task1},
        )

    def test_add_parent__cycle(self):
        "Cycle error."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        task1 = self.create_task(project, 'Task01')
        task2 = self.create_task(project, 'Task02')
        task3 = self.create_task(project, 'Task03')

        self.assertListEqual([task1], [*task1.get_subtasks()])

        build_url = self._build_add_parent_task_url
        field_value = self.formfield_value_multi_creator_entity
        self.assertNoFormError(self.client.post(
            build_url(task2), data={'parents': field_value(task1)},
        ))
        self.assertCountEqual([task1, task2], task1.get_subtasks())

        self.assertNoFormError(self.client.post(
            build_url(task3), data={'parents': field_value(task2)},
        ))
        self.assertCountEqual([task1, task2, task3], task1.get_subtasks())

        response = self.assertPOST200(
            build_url(task1), data={'parents': field_value(task3)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='parents',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': task3},
        )

    def test_duration(self):
        user = self.login_as_root_and_get()
        project = self.create_project(user=user, name='Eva01')[0]
        task = self.create_task(project, 'Title')

        self.assertEqual(50, task.duration)

        self.assertEqual(0, task.get_effective_duration())
        self.assertEqual(0, task.get_effective_duration('%'))

        self.assertEqual(-50, task.get_delay())
        self.assertEqual(50, project.get_expected_duration())

    def test_duration__zero(self):
        user = self.login_as_root_and_get()
        project = self.create_project(user=user, name='Eva01')[0]

        task = self.create_task(project, 'Title')
        task.duration = 0
        task.save()

        self.assertEqual(0,   task.get_effective_duration())
        self.assertEqual(100, task.get_effective_duration('%'))

        self.assertEqual(0, task.get_delay())
        self.assertEqual(0, project.get_expected_duration())

    @parameterized.expand([True, False])
    @skipIfCustomActivity
    def test_delete(self, deletion_allowed):
        with override_settings(ENTITIES_DELETION_ALLOWED=deletion_allowed):
            user = self.login_as_root_and_get()

            project = self.create_project(user=user, name='Eva02')[0]
            task = self.create_task(project, 'arms')
            worker = self.create_user().linked_contact

            self.create_resource(task, worker)
            resource = task.resources_set.all()[0]

            self.create_activity(user=user, resource=resource)
            activity = task.related_activities[0]

            response = self.client.post(task.get_delete_absolute_url())
            self.assertDoesNotExist(task)
            self.assertDoesNotExist(resource)
            self.assertStillExists(activity)
            self.assertRedirects(response, project.get_absolute_url())

    def test_delete_status(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        status2 = TaskStatus.objects.first()
        status1 = TaskStatus.objects.create(name='Coming soon')
        task = self.create_task(project, 'Building head', status=status1)
        self.assertNoFormError(self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('projects', 'taskstatus', status1.id),
            ),
            data={'replace_projects__projecttask_tstatus': status2.id},
        ))

        job = self.get_deletion_command_or_fail(TaskStatus).job
        job.type.execute(job)
        self.assertDoesNotExist(status1)

        self.assertStillExists(project)
        task = self.assertStillExists(task)
        self.assertEqual(status2, task.tstatus)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_cost_n_duration(self):
        "With several activities."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
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

        self.create_activity(user=user, resource=resource1, duration=8)
        self.create_activity(user=user, resource=resource2, duration=3)

        self.assertEqual(8 + 3, task.get_effective_duration())

        cost = task.get_task_cost()
        self.assertEqual(8 * 100 + 3 * 150, cost)
        self.assertEqual(cost, project.get_project_cost())
