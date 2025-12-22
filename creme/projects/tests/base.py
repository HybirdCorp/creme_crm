from datetime import date
from unittest import skipIf

from django.urls import reverse

from creme.activities.constants import UUID_TYPE_TASK
from creme.activities.models import ActivitySubType
from creme.creme_core.models import Currency
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import get_contact_model
from creme.persons.tests.base import skipIfCustomContact
from creme.projects import (
    get_project_model,
    get_task_model,
    project_model_is_custom,
    task_model_is_custom,
)
from creme.projects.constants import UUID_TSTATUS_NOT_STARTED
from creme.projects.models import ProjectStatus, TaskStatus

skip_projects_tests = project_model_is_custom()
skip_tasks_tests = task_model_is_custom()

Contact = get_contact_model()

Project = get_project_model()
ProjectTask = get_task_model()


def skipIfCustomProject(test_func):
    return skipIf(skip_projects_tests, 'Custom Project model in use')(test_func)


def skipIfCustomTask(test_func):
    return skipIf(skip_tasks_tests, 'Custom ProjectTask model in use')(test_func)


@skipIfCustomContact
@skipIfCustomProject
class ProjectsTestCase(CremeTestCase):
    ADD_PROJECT_URL = reverse('projects__create_project')
    EXTRA_LEADERS_KEY = 'cform_extra-projects_leaders'

    def login_as_projects_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['projects', *allowed_apps],
            **kwargs
        )

    @staticmethod
    def _build_add_activity_url(task):
        return reverse('projects__create_activity', args=(task.id,))

    @staticmethod
    def _build_add_task_url(project):
        return reverse('projects__create_task', args=(project.id,))

    @staticmethod
    def _build_add_resource_url(task):
        return reverse('projects__create_resource', args=(task.id,))

    def create_resource(self, task, contact, hourly_cost=100, error=False):
        response = self.client.post(
            self._build_add_resource_url(task),
            follow=True,
            data={
                'user':        task.user.id,
                'contact':     contact.id,
                'hourly_cost': hourly_cost,
            },
        )

        if not error:
            self.assertNoFormError(response)

        return response

    def create_activity(self, *,
                        user,
                        resource,
                        start=date(2015, 5, 19), end=date(2015, 6, 3),
                        duration='8', sub_type_id=None, busy='', errors=False,
                        ):
        if not sub_type_id:
            sub_type_id = ActivitySubType.objects.filter(type__uuid=UUID_TYPE_TASK).first().id

        response = self.client.post(
            self._build_add_activity_url(resource.task),
            follow=True,
            data={
                'resource':      resource.linked_contact_id,
                'start':         self.formfield_value_datetime(start),
                'end':           self.formfield_value_datetime(end),
                'duration':      duration,
                'type_selector': sub_type_id,
                'user':          user.id,
                'busy':          busy,
            },
        )

        if not errors:
            self.assertNoFormError(response)

        return response

    def create_project(self, *,
                       user,
                       name,
                       status=None,
                       start_date=date(2010, 10, 11), end_date=date(2010, 12, 31),
                       ):
        status = status or ProjectStatus.objects.all()[0]
        manager = Contact.objects.create(user=user, first_name='Gendo', last_name='Ikari')
        currency = Currency.objects.all()[0]
        response = self.client.post(
            self.ADD_PROJECT_URL, follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'status':       status.id,
                'currency':     currency.id,
                'start_date':   self.formfield_value_datetime(start_date),
                'end_date':     end_date,

                self.EXTRA_LEADERS_KEY: self.formfield_value_multi_creator_entity(manager),
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Project, name=name), manager

    def create_task(self, project, title,
                    status=None, sub_type_id=None,
                    ):
        if not sub_type_id:
            sub_type_id = ActivitySubType.objects.filter(type__uuid=UUID_TYPE_TASK).first().id

        status = status or TaskStatus.objects.get(uuid=UUID_TSTATUS_NOT_STARTED)
        response = self.client.post(
            self._build_add_task_url(project), follow=True,
            data={
                'user':          project.user.id,
                'title':         title,
                'start':         self.formfield_value_date(2010, 10, 11),
                'end':           self.formfield_value_date(2010, 10, 30),
                'duration':      50,
                'tstatus':       status.id,
                'type_selector': sub_type_id,
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ProjectTask, linked_project=project, title=title)

    # TODO: test better get_project_cost(), get_effective_duration(), get_delay()
