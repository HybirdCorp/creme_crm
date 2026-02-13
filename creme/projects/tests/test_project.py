from datetime import date, timedelta

from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import now
from django.utils.translation import gettext as _

import creme.creme_core.tests.views.base as views_base
import creme.projects.bricks as proj_bricks
from creme.creme_core.gui import actions
from creme.creme_core.models import CremeProperty, CremePropertyType
from creme.creme_core.utils.currency_format import currency
from creme.projects.actions import ProjectCloseAction
from creme.projects.constants import (
    REL_OBJ_PROJECT_MANAGER,
    REL_SUB_PROJECT_MANAGER,
    UUID_TSTATUS_NOT_STARTED,
)
from creme.projects.models import ProjectStatus, Resource, TaskStatus
from creme.projects.tests.base import (
    Contact,
    Project,
    ProjectsTestCase,
    ProjectTask,
    skipIfCustomTask,
)


class ProjectTestCase(views_base.BrickTestCaseMixin,
                      views_base.ButtonTestCaseMixin,
                      ProjectsTestCase):
    def _create_parented_task(self, title, project, parents=None):
        status = TaskStatus.objects.get_or_create(name='status', description='')[0]
        now_value = now()
        task = ProjectTask.objects.create(
            linked_project=project,
            order=0, duration=0,
            tstatus=status, title=title,
            user=project.user,
            start=now_value,
            end=now_value + timedelta(hours=1),
        )

        if parents is not None:
            task.parent_tasks.set(parents)

        return task

    @staticmethod
    def _tasks_pk_set(project):
        return {*project.get_tasks().values_list('pk', flat=True)}

    @staticmethod
    def _titles_collections(tasks_qs, constructor):
        return constructor(tasks_qs.values_list('title', flat=True))

    def _titles_list(self, tasks_qs):
        return self._titles_collections(tasks_qs, list)

    def _titles_set(self, tasks_qs):
        return self._titles_collections(tasks_qs, set)

    def test_populate(self):
        self.get_relationtype_or_fail(
            REL_SUB_PROJECT_MANAGER,
            sub_models=[Contact], obj_models=[Project],
        )

        pstatus_orders = [*ProjectStatus.objects.values_list('order', flat=True)]
        self.assertTrue(pstatus_orders)
        self.assertTrue(range(len(pstatus_orders) + 1), pstatus_orders)

    def test_detailview(self):
        user = self.login_as_root_and_get()

        status = ProjectStatus.objects.all()[0]
        project = self.create_project(
            user=user, name='Eva00', status=status,
            start_date=date(2010, 10, 11), end_date=date(2010, 12, 31),
        )[0]
        response = self.assertGET200(project.get_absolute_url())
        self.assertTemplateUsed(response, 'projects/view_project.html')

        # ---
        tree = self.get_html_tree(response.content)
        info_brick_node = self.get_brick_node(tree, brick=proj_bricks.ProjectExtraInfoBrick)
        self.assertListEqual(
            [
                currency(0, project.currency),  # Cost
                '—',  # Delay
            ],
            [node.text for node in info_brick_node.findall('.//div[@class="brick-kv-value"]')],
        )

        # ---
        task_brick_node = self.get_brick_node(tree, brick=proj_bricks.ProjectTasksBrick)
        self.assertEqual(
            _('Related tasks'),
            self.get_brick_title(task_brick_node),
        )

    def test_detailview__tasks(self):
        user = self.login_as_root_and_get()

        project = Project.objects.create(
            user=user, name='Eva02', status=ProjectStatus.objects.first(),
        )
        now_value = now()
        task = ProjectTask.objects.create(
            user=user,
            linked_project=project,
            title='legs',
            tstatus=TaskStatus.objects.get(uuid=UUID_TSTATUS_NOT_STARTED),
            start=now_value,
            end=now_value + timedelta(days=3),
            duration=1,
        )

        resource = Resource.objects.create(
            linked_contact=user.linked_contact, task=task, hourly_cost=100,
        )
        self.create_activity(user=user, resource=resource, duration='3')

        response = self.assertGET200(project.get_absolute_url())

        # ---
        tree = self.get_html_tree(response.content)
        info_brick_node = self.get_brick_node(tree, brick=proj_bricks.ProjectExtraInfoBrick)
        self.assertListEqual(
            [
                currency(300, project.currency),  # Cost
                '2',  # Delay (3 - 1)
            ],
            [node.text for node in info_brick_node.findall('.//div[@class="brick-kv-value"]')],
        )

        # ---
        task_brick_node = self.get_brick_node(tree, brick=proj_bricks.ProjectTasksBrick)
        self.assertBrickTitleEqual(
            task_brick_node,
            count=1, title='{count} Related task', plural_title='{count} Related tasks',
        )
        self.assertInstanceLink(task_brick_node, task)

    def test_creation(self):
        user = self.login_as_root_and_get()
        self.assertGET200(self.ADD_PROJECT_URL)

        name = 'Eva00'
        status = ProjectStatus.objects.all()[0]
        project, manager = self.create_project(
            user=user, name=name, status=status,
            start_date=date(2010, 10, 11), end_date=date(2010, 12, 31),
        )
        self.assertEqual(user,   project.user)
        self.assertEqual(name,   project.name)
        self.assertEqual(status, project.status)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=10, day=11), project.start_date)
        self.assertEqual(create_dt(year=2010, month=12, day=31), project.end_date)

        self.assertHaveRelation(subject=project, type=REL_OBJ_PROJECT_MANAGER, object=manager)

    def test_creation__perms(self):
        "Credentials error."
        user = self.login_as_projects_user(creatable_models=[Project])
        self.add_credentials(user.role, all='!LINK', own='*')

        manager = Contact.objects.create(user=user, first_name='Gendo', last_name='Ikari')
        self.assertFalse(user.has_perm_to_link(manager))

        response = self.assertPOST200(
            self.ADD_PROJECT_URL,
            follow=True,
            data={
                'user':         user.pk,
                'name':         'Eva00',
                'status':       ProjectStatus.objects.all()[0].id,
                'start_date':   self.formfield_value_date(2011, 10, 11),
                'end_date':     self.formfield_value_date(2011, 12, 31),

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EXTRA_LEADERS_KEY,
            errors=_('Some entities are not linkable: {}').format(
                _('Entity #{id} (not viewable)').format(id=manager.id),
            ),
        )

    def test_creation__error_start_end(self):
        "Validation error with start/end."
        user = self.login_as_root_and_get()

        manager = Contact.objects.create(user=user, first_name='Gendo', last_name='Ikari')
        response = self.assertPOST200(
            self.ADD_PROJECT_URL, follow=True,
            data={
                'user':         user.pk,
                'name':         'Eva00',
                'status':       ProjectStatus.objects.all()[0].id,
                'start_date':   self.formfield_value_date(2012, 2, 16),
                'end_date':     self.formfield_value_date(2012, 2, 15),

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )

        create_dt = self.create_datetime
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('Start ({start}) must be before end ({end}).').format(
                start=date_format(create_dt(2012, 2, 16), 'DATE_FORMAT'),
                end=date_format(create_dt(2012, 2, 15), 'DATE_FORMAT'),
            ),
        )

    def test_listview(self):
        user = self.login_as_root_and_get()

        self.create_project(user=user, name='Eva00')
        self.create_project(user=user, name='Eva01')
        self.assertGET200(reverse('projects__list_projects'))

    def test_listview_instance_actions(self):
        user = self.login_as_projects_user(
            allowed_apps=['persons'], creatable_models=[Project],
        )
        self.add_credentials(user.role, all='*')

        project = self.create_project(user=user, name='Eva00')[0]
        self.assertTrue(user.has_perm_to_change(project))

        close_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=project)
            if isinstance(action, ProjectCloseAction)
        )
        self.assertEqual('projects-close', close_action.type)
        self.assertEqual(
            reverse('projects__close_project', args=(project.id,)),
            close_action.url,
        )
        self.assertTrue(close_action.is_enabled)
        self.assertTrue(close_action.is_visible)
        self.assertEqual('', close_action.help_text)

    def test_listview_instance_actions__closed(self):
        user = self.login_as_root_and_get()
        project = self.create_project(
            user=user, name='Eva00', start_date=date(2012, 2, 16), end_date=date(2012, 3, 26),
        )[0]
        project.effective_end_date = now()
        project.save()

        self.assertTrue(project.is_closed)

        close_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=project)
            if isinstance(action, ProjectCloseAction)
        )
        self.assertEqual('projects-close', close_action.type)
        self.assertEqual(
            reverse('projects__close_project', args=(project.id,)),
            close_action.url,
        )
        self.assertFalse(close_action.is_enabled)
        self.assertTrue(close_action.is_visible)
        self.assertEqual(_('Project is already closed.'), close_action.help_text)

    def test_listview_instance_actions__forbidden(self):
        user = self.login_as_projects_user(
            allowed_apps=['persons'], creatable_models=[Project],
        )
        self.add_credentials(user.role, all='!CHANGE')

        project = self.create_project(user=user, name='Eva00')[0]
        self.assertFalse(user.has_perm_to_change(project))

        close_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=project)
            if isinstance(action, ProjectCloseAction)
        )
        self.assertFalse(close_action.is_enabled)
        self.assertEqual(
            _('You are not allowed to edit this entity: {}').format(project),
            close_action.help_text,
        )

    def test_inner_edit(self):
        user = self.login_as_root_and_get()

        project = self.create_project(
            user=user, name='Eva01', start_date=date(2012, 2, 16), end_date=date(2012, 3, 26),
        )[0]
        uri = self.build_inneredit_uri(project, 'start_date')
        self.assertGET200(uri)

        self.assertNoFormError(self.client.post(
            uri, data={'start_date':  self.formfield_value_date(2012, 3, 4)},
        ))
        self.assertEqual(
            self.create_datetime(year=2012, month=3, day=4),
            self.refresh(project).start_date,
        )

    def test_inner_edit__error(self):
        "Validation error."
        user = self.login_as_root_and_get()

        project = self.create_project(
            user=user, name='Eva01', start_date=date(2012, 2, 20), end_date=date(2012, 3, 25),
        )[0]
        response = self.assertPOST200(
            self.build_inneredit_uri(project, 'start_date'),
            data={
                'start_date': date(2012, 3, 27),  # <= after end_date
            },
        )

        create_dt = self.create_datetime
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('Start ({start}) must be before end ({end}).').format(
                start=date_format(create_dt(2012, 3, 27), 'DATE_FORMAT'),
                end=date_format(create_dt(2012, 3, 25), 'DATE_FORMAT'),
            ),
        )
        self.assertEqual(
            create_dt(year=2012, month=2, day=20),
            self.refresh(project).start_date,
        )

    @skipIfCustomTask
    def test_close(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva01')[0]
        self.assertFalse(project.is_closed)
        self.assertIsNone(project.effective_end_date)

        detail_url = project.get_absolute_url()
        close_url = reverse('projects__close_project', args=(project.id,))

        detail_response1 = self.assertGET200(detail_url)
        self.assertTrue(
            [*self.iter_button_nodes(
                self.get_instance_buttons_node(self.get_html_tree(detail_response1.content)),
                tags=['a'], href=close_url,
            )],
            msg='<Close> button not found!',
        )

        # ---
        self.assertGET405(close_url)
        self.assertPOST200(close_url, follow=True)

        project = self.refresh(project)
        self.assertTrue(project.is_closed)
        self.assertTrue(project.effective_end_date)

        self.assertDatetimesAlmostEqual(now(), project.effective_end_date)

        detail_response2 = self.assertGET200(detail_url)
        self.assertFalse(
            [*self.iter_button_nodes(
                self.get_instance_buttons_node(self.get_html_tree(detail_response2.content)),
                tags=['a'], href=close_url,
            )],
            msg='<Close> button found!',
        )

        # Already closed
        self.assertPOST409(close_url, follow=True)

    @skipIfCustomTask
    def test_clone(self):
        user = self.login_as_root_and_get()
        project = self.create_project(user=user, name='Project')[0]

        create_task = self._create_parented_task
        task1    = create_task('1', project)
        task11   = create_task('1.1', project, [task1])
        task111  = create_task('1.1.1', project, [task11])
        task1111 = create_task('1.1.1.1', project, [task111])
        create_task('all 1', project, [task1, task11, task111, task1111])

        ptype = CremePropertyType.objects.create(text='Important')
        CremeProperty.objects.create(type=ptype, creme_entity=task1)

        task2 = create_task('2', project)
        create_task('all 2', project, [task1, task11, task111, task1111, task2])

        cloned_project = self.clone(project)

        cloned_tasks = {
            task.title: task for task in cloned_project.get_tasks()
        }
        self.assertCountEqual(
            ['1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2'],
            cloned_tasks.keys(),
        )
        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        def get_task(title):
            task = cloned_tasks.get(title)
            if task is None:
                self.fail(f'Task "{title}" has not been found')  # pragma: no cover

            return task

        titles_list = self._titles_list
        cloned_task1 = get_task(title='1')
        self.assertSameProperties(task1, cloned_task1)

        self.assertFalse(cloned_task1.get_parents())
        self.assertListEqual(['1'],     titles_list(get_task(title='1.1').get_parents()))
        self.assertListEqual(['1.1'],   titles_list(get_task(title='1.1.1').get_parents()))
        self.assertListEqual(['1.1.1'], titles_list(get_task(title='1.1.1.1').get_parents()))

        titles_set = self._titles_set
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
    def test_clone__ressource(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Project')[0]
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

        cloned_project = self.clone(project)

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

    # @skipIfCustomTask
    # def test_project_clone__method01(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     project = self.create_project(user=user, name='Project')[0]
    #
    #     create_task = self._create_parented_task
    #     task1    = create_task('1', project)
    #     task11   = create_task('1.1', project, [task1])
    #     task111  = create_task('1.1.1', project, [task11])
    #     task1111 = create_task('1.1.1.1', project, [task111])
    #     create_task('all 1', project, [task1, task11, task111, task1111])
    #
    #     task2 = create_task('2', project)
    #     create_task('all 2', project, [task1, task11, task111, task1111, task2])
    #
    #     cloned_project = project.clone()
    #
    #     titles_list = self._titles_list
    #     titles_set = self._titles_set
    #     self.assertSetEqual(
    #         {'1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2'},
    #         titles_set(cloned_project.get_tasks()),
    #     )
    #
    #     self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))
    #
    #     get_task = cloned_project.get_tasks().get
    #     self.assertFalse(get_task(title='1').get_parents())
    #     self.assertListEqual(['1'],     titles_list(get_task(title='1.1').get_parents()))
    #     self.assertListEqual(['1.1'],   titles_list(get_task(title='1.1.1').get_parents()))
    #     self.assertListEqual(['1.1.1'], titles_list(get_task(title='1.1.1.1').get_parents()))
    #     self.assertSetEqual(
    #         {'1', '1.1', '1.1.1', '1.1.1.1'},
    #         titles_set(get_task(title='all 1').get_parents()),
    #     )
    #     self.assertFalse(get_task(title='2').get_parents())
    #     self.assertSetEqual(
    #         {'1', '1.1', '1.1.1', '1.1.1.1', '2'},
    #         titles_set(get_task(title='all 2').get_parents()),
    #     )
    #
    # @skipIfCustomTask
    # def test_project_clone__method02(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     project = self.create_project(user=user, name='Project')[0]
    #     contact1 = Contact.objects.create(user=user)
    #     contact2 = Contact.objects.create(user=user)
    #
    #     create_resource = Resource.objects.create
    #
    #     task1 = self._create_parented_task('1', project)
    #     create_resource(linked_contact=contact1, task=task1)
    #     create_resource(linked_contact=contact2, task=task1)
    #
    #     task2 = self._create_parented_task('2', project)
    #     create_resource(linked_contact=contact1, task=task2)
    #     create_resource(linked_contact=contact2, task=task2)
    #
    #     task3 = self._create_parented_task('3', project, [task1, task2])
    #     self._create_parented_task('4', project, [task3])
    #
    #     cloned_project = project.clone()
    #
    #     for attr in [
    #         'name', 'description', 'status', 'start_date', 'end_date', 'effective_end_date',
    #     ]:
    #         self.assertEqual(getattr(project, attr), getattr(cloned_project, attr))
    #
    #     get_task = cloned_project.get_tasks().get
    #     c_task1 = get_task(title='1')
    #     c_task2 = get_task(title='2')
    #
    #     self.assertEqual({'1', '2', '3', '4'}, self._titles_set(cloned_project.get_tasks()))
    #     self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))
    #
    #     self.assertSetEqual({'1', '2'}, self._titles_set(get_task(title='3').get_parents()))
    #     self.assertListEqual(['3'], self._titles_list(get_task(title='4').get_parents()))
    #
    #     def linked_contacts_set(task):
    #         return {*task.get_resources().values_list('linked_contact', flat=True)}
    #
    #     self.assertSetEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task1))
    #     self.assertSetEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task2))

    @skipIfCustomTask
    def test_delete_status(self):
        user = self.login_as_root_and_get()

        status2 = ProjectStatus.objects.first()
        status = ProjectStatus.objects.create(name='Sinking')
        project = self.create_project(user=user, name='Project', status=status)[0]
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
