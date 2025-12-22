from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY
from creme.activities.models import Calendar
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.models import SetCredentials
from creme.projects.constants import (
    REL_SUB_PART_AS_RESOURCE,
    UUID_TSTATUS_NOT_STARTED,
)
from creme.projects.models import ProjectStatus, TaskStatus
from creme.projects.tests.base import (
    Contact,
    Project,
    ProjectsTestCase,
    ProjectTask,
    skipIfCustomTask,
)


@skipIfCustomTask
class ResourceTestCase(ProjectsTestCase):
    DELETE_RESOURCE_URL = reverse('projects__delete_resource')

    def test_create_resource(self):
        user = self.login_as_projects_user()
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'], model=Project)

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
            # tstatus=TaskStatus.objects.get(pk=NOT_STARTED_PK),
            tstatus=TaskStatus.objects.get(uuid=UUID_TSTATUS_NOT_STARTED),
            start=now_value,
            end=now_value + timedelta(days=3),
            duration=21,
        )
        self.assertTrue(user.has_perm_to_change(task))
        self.assertGET200(self._build_add_resource_url(task))

    def test_create_resource__edition_perm(self):
        "Edition permission needed."
        user = self.login_as_projects_user()
        self.add_credentials(user.role, all=['VIEW'], model=Project)  # Not CHANGE

        project = Project.objects.create(
            user=user,
            name='Eva02',
            status=ProjectStatus.objects.first(),
        )
        now_value = now()
        task = ProjectTask.objects.create(
            user=user,
            linked_project=project,
            tstatus=TaskStatus.objects.get(uuid=UUID_TSTATUS_NOT_STARTED),
            start=now_value,
            end=now_value + timedelta(days=3),
            duration=21,
        )
        self.assertGET403(self._build_add_resource_url(task))

    @skipIfCustomActivity
    def test_edition(self):
        "Related contact participates in activities."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        project = self.create_project(user=user, name='Eva02')[0]
        task1 = self.create_task(project, 'arms')
        task2 = self.create_task(project, 'legs')

        worker1 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')
        worker2 = other_user.linked_contact

        self.create_resource(task1, worker1)
        resource1 = task1.resources_set.all()[0]
        self.create_activity(user=user, resource=resource1)

        self.create_resource(task2, worker1)
        resource2 = task2.resources_set.all()[0]
        self.create_activity(user=user, resource=resource2)

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
        activity1 = self.get_alone_element(task1.related_activities)

        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_2_ACTIVITY,  object=activity1)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_AS_RESOURCE, object=activity1)

        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_2_ACTIVITY,  object=activity1)
        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_AS_RESOURCE, object=activity1)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(other_user)],
            [*activity1.calendars.all()],
        )

        # activity of the other resource => no change
        activity2 = self.get_alone_element(task2.related_activities)

        self.assertHaveRelation(subject=worker1, type=REL_SUB_PART_2_ACTIVITY,  object=activity2)
        self.assertHaveRelation(subject=worker1, type=REL_SUB_PART_AS_RESOURCE, object=activity2)

    @skipIfCustomActivity
    def test_edition__old_resource(self):
        "Related contact participates in activities: old resource continues to participate."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')

        worker1 = user.linked_contact
        worker2 = other_user.linked_contact

        self.create_resource(task, worker1)
        resource1 = task.resources_set.all()[0]
        self.create_activity(user=user, resource=resource1)

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

        activity = self.get_alone_element(task.related_activities)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        self.assertHaveRelation(subject=worker1, type=REL_SUB_PART_2_ACTIVITY, object=activity)
        self.assertHaveNoRelation(subject=worker1, type=REL_SUB_PART_AS_RESOURCE, object=activity)

        get_cal = Calendar.objects.get_default_calendar
        self.assertCountEqual(
            [get_cal(user), get_cal(other_user)],
            activity.calendars.all(),
        )

    @skipIfCustomActivity
    def test_delete__no_related_activity(self):
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task1 = self.create_task(project, 'arms')
        task2 = self.create_task(project, 'legs')
        worker1 = self.create_user().linked_contact
        worker2 = Contact.objects.create(user=user, first_name='Yui', last_name='Ikari')

        self.create_resource(task1, worker1)
        resource1 = task1.resources_set.all()[0]

        self.create_resource(task1, worker2)
        resource2 = task1.resources_set.exclude(pk=resource1.id)[0]

        self.create_resource(task2, worker1)
        resource3 = task2.resources_set.all()[0]

        self.create_activity(user=user, resource=resource2)
        activity = task1.related_activities[0]

        # This activity is linked to the same contact, but not the same
        # resource, so it should not avoid the deletion of resource1
        self.create_activity(user=user, resource=resource3)

        url = self.DELETE_RESOURCE_URL
        data = {'id': resource1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertDoesNotExist(resource1)

        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker2, type=REL_SUB_PART_AS_RESOURCE, object=activity)

    @skipIfCustomActivity
    def test_delete__related_activity(self):
        "Related activity => 409."
        user = self.login_as_root_and_get()

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.create_user().linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.create_activity(user=user, resource=resource)
        activity = task.related_activities[0]

        self.assertPOST409(self.DELETE_RESOURCE_URL, data={'id': resource.id})
        self.assertStillExists(resource)

        self.assertHaveRelation(subject=worker, type=REL_SUB_PART_2_ACTIVITY,  object=activity)
        self.assertHaveRelation(subject=worker, type=REL_SUB_PART_AS_RESOURCE, object=activity)

    @skipIfCustomActivity
    def test_delete__regular_user(self):
        user = self.login_as_projects_user(
            allowed_apps=['persons'],
            creatable_models=[Project, ProjectTask],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.get_root_user().linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        self.assertPOST200(self.DELETE_RESOURCE_URL, data={'id': resource.id}, follow=True)
        self.assertDoesNotExist(resource)

    @skipIfCustomActivity
    @skipIfCustomTask
    def test_delete__forbidden(self):
        "Not super-user + cannot change the task => error."
        user = self.login_as_projects_user(
            allowed_apps=['persons'],
            creatable_models=[Project, ProjectTask],
        )
        creds = SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        project = self.create_project(user=user, name='Eva02')[0]
        task = self.create_task(project, 'arms')
        worker = self.get_root_user().linked_contact

        self.create_resource(task, worker)
        resource = task.resources_set.all()[0]

        creds.value = EntityCredentials.VIEW | EntityCredentials.LINK
        creds.save()
        self.assertPOST403(self.DELETE_RESOURCE_URL, data={'id': resource.id})
