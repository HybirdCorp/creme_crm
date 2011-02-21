# -*- coding: utf-8 -*-

from datetime import datetime, date, time

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, UserRole, SetCredentials
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact

from projects.models import *
from projects.constants import *


class ProjectsTestCase(TestCase):
    def login(self, is_superuser=True):
        password = 'test'

        superuser = User.objects.create(username='Kirika')
        superuser.set_password(password)
        superuser.is_superuser = True
        superuser.save()

        role = UserRole.objects.create(name='Basic')
        role.allowed_apps = ['projects']
        role.save()
        basic_user = User.objects.create(username='Mireille', role=role)
        basic_user.set_password(password)
        basic_user.save()

        self.user, self.other_user = (superuser, basic_user) if is_superuser else \
                                     (basic_user, superuser)

        logged = self.client.login(username=self.user.username, password=password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'projects'])
        self.password = 'test'
        self.user = None

    def assertNoFormError(self, response): #move in a CremeTestCase ???
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

    def test_populate(self):
        rtypes = RelationType.objects.filter(pk=REL_SUB_PROJECT_MANAGER)
        self.assertEqual(1, rtypes.count())

        rtype  = rtypes[0]
        get_ct = ContentType.objects.get_for_model
        self.assertEqual([get_ct(Contact)], list(rtype.subject_ctypes.all()))
        self.assertEqual([get_ct(Project)], list(rtype.object_ctypes.all()))

        self.assert_(TaskStatus.objects.exists())
        self.assert_(ProjectStatus.objects.exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/projects/').status_code)

    def create_project(self, name):
        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        response = self.client.post('/projects/project/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2010-10-11',
                                            'end_date':     '2010-12-31',
                                            'responsibles': manager.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            project = Project.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        return project, manager

    def test_project_createview01(self):
        self.login()

        response = self.client.get('/projects/project/add')
        self.assertEqual(200, response.status_code)

        project, manager = self.create_project('Eva00')
        self.assertEqual(1, Relation.objects.filter(subject_entity=project, type=REL_OBJ_PROJECT_MANAGER, object_entity=manager).count())

    def test_project_createview02(self):
        self.login(is_superuser=False)

        role = self.user.role
        create_sc = SetCredentials.objects.create
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )
        role.creatable_ctypes = [ContentType.objects.get_for_model(Project)]

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        self.failIf(manager.can_link(self.user))

        response = self.client.post('/projects/project/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         'Eva00',
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2011-10-11',
                                            'end_date':     '2011-12-31',
                                            'responsibles': manager.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assert_('responsibles' in errors)

    def test_project_lisview(self):
        self.login()

        self.create_project('Eva00')
        self.create_project('Eva01')

        self.assertEqual(200, self.client.get('/projects/projects').status_code)

    def test_task_createview01(self):
        self.login()

        project = self.create_project('Eva01')[0]

        response = self.client.get('/projects/project/%s/task/add' % project.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/projects/project/%s/task/add' % project.id, follow=True,
                                    data={
                                        'user':     self.user.id,
                                        'title':    'head',
                                        'start':    '2010-10-11',
                                        'end':      '2010-10-30',
                                        'duration': 50,
                                        'tstatus':   TaskStatus.objects.all()[0].id,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(1, task1.order)

        response = self.client.post('/projects/project/%s/task/add' % project.id, follow=True,
                                    data={
                                        'user':         self.user.id,
                                        'title':        'torso',
                                        'start':        '2010-10-30',
                                        'end':          '2010-11-20',
                                        'duration':     180,
                                        'tstatus':       TaskStatus.objects.all()[0].id,
                                        'parents_task': task1.id,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(2, tasks.count())

        task2 = filter(lambda t: t.id != task1.id, tasks)
        self.assertEqual(1, len(task2))

        task2 = task2[0]
        self.assertEqual([task1.id], [t.id for t in task2.parents_task.all()])

        self.assertEqual(list(tasks), list(project.get_tasks()))

        self.assertEqual(180 + 50, project.get_expected_duration())

    def create_task(self, project, title):
        response = self.client.post('/projects/project/%s/task/add' % project.id, follow=True,
                                    data={
                                        'user':     self.user.id,
                                        'title':    title,
                                        'start':    '2010-10-11',
                                        'end':      '2010-10-30',
                                        'duration': 50,
                                        'tstatus':   TaskStatus.objects.all()[0].id,
                                    })
        self.assertEqual(200, response.status_code)

        try:
            task = ProjectTask.objects.get(project=project, title=title)
        except Exception, e:
            self.fail(str(e))

        return task

    def test_resource_n_period01(self): #createviews
        self.login()

        project = self.create_project('Eva02')[0]
        task    = self.create_task(project, 'legs')
        self.failIf(task.resources_set.all())

        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    100,
                                    })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        #self.failIf(response.context['form'].errors)

        resources = list(task.resources_set.all())
        self.assertEqual(1, len(resources))

        resource = resources[0]
        self.failIf(resource.workingperiod_set.all())

        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   8,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)
        self.assertEqual(1, resource.workingperiod_set.count())

        self.assertEqual(8,   task.get_effective_duration())
        self.assertEqual(800, task.get_task_cost()) #8 * 100
        self.assertEqual(-42, task.get_delay()) # 8 - 50
        self.assert_(task.is_alive())

        self.assertEqual(8,   project.get_effective_duration())
        self.assertEqual(800, project.get_project_cost()) #8 * 100
        self.assertEqual(0,   project.get_delay())

    def test_resource_n_period02(self): #editviews
        self.login()

        project  = self.create_project('Eva02')[0]
        task     = self.create_task(project, 'arms')
        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    100,
                                    })
        resource = task.resources_set.all()[0]
        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   8,
                                    })

        response = self.client.get('/projects/resource/edit/%s' % resource.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/projects/resource/edit/%s' % resource.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    200,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        resource = Resource.objects.get(pk=resource.id) #refresh
        self.assertEqual(200, resource.hourly_cost)


        wperiods = list(resource.workingperiod_set.all())
        self.assertEqual(1, len(wperiods))

        wperiod = wperiods[0]
        response = self.client.get('/projects/period/edit/%s' % wperiod.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/projects/period/edit/%s' % wperiod.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   10,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        wperiod = WorkingPeriod.objects.get(pk=wperiod.id) #refresh
        self.assertEqual(10, wperiod.duration)

    def test_project_close(self):
        self.login()

        project = self.create_project('Eva01')[0]
        self.assert_(not project.is_closed)
        self.assert_(not project.effective_end_date)

        response = self.client.get('/projects/project/%s/close' % project.id)
        self.assertEqual(404, response.status_code)

        response = self.client.post('/projects/project/%s/close' % project.id, follow=True)
        self.assertEqual(200, response.status_code)

        project = Project.objects.get(pk=project.id) #refresh
        self.assert_(project.is_closed)
        self.assert_(project.effective_end_date)

        delta = datetime.combine(date.today(), time()) - project.effective_end_date
        self.assert_(delta.seconds < 10)

        #already closed
        response = self.client.post('/projects/project/%s/close' % project.id, follow=True)
        self.assertEqual(404, response.status_code)

    #TODO: test better get_project_cost(), get_effective_duration(), get_delay()
