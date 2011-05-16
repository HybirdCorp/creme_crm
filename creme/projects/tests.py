# -*- coding: utf-8 -*-

from datetime import datetime, date, time

from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, SetCredentials
from creme_core.tests.base import CremeTestCase

from persons.models import Contact

from projects.models import *
from projects.constants import *


class ProjectsTestCase(CremeTestCase):
    def login(self, is_superuser=True):
        super(ProjectsTestCase, self).login(is_superuser, allowed_apps=['projects'])

    def setUp(self):
        self.populate('creme_core', 'projects')

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

    def _create_task(self, title, project, parents=None):
        status = TaskStatus.objects.get_or_create(name='status', description="")[0]
        task = ProjectTask.objects.create(project=project, order=0, duration=0, tstatus=status, user=self.user, title=title)
        if parents is not None:
            task.parents_task = parents
        return task

    def _create_resource(self, contact, task):
        return Resource.objects.create(linked_contact=contact, user=self.user, task=task)

    def _create_working_period(self, task, resource):
        return WorkingPeriod.objects.create(task=task, resource=resource)

    def test_project_clone01(self):
        self.login()
        self.populate('creme_core', 'activities')
        user = self.user
        
        project, manager = self.create_project('Project')

        task1 = self._create_task('1', project)
        task11 = self._create_task('1.1', project, [task1])
        task111 = self._create_task('1.1.1', project, [task11])
        task1111 = self._create_task('1.1.1.1', project, [task111])

        task_all_1 = self._create_task('all 1', project, [task1, task11, task111, task1111])

        task2 = self._create_task('2', project)

        task_all = self._create_task('all 2', project, [task1, task11, task111, task1111, task2])

        cloned_project = project.clone()

        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2']), set(cloned_project.get_tasks().values_list('title', flat=True)))
        self.assertNotEqual(set(project.get_tasks().values_list('pk', flat=True)), set(cloned_project.get_tasks().values_list('pk', flat=True)))

        self.assertFalse(set(project.get_tasks().values_list('pk', flat=True)) & set(cloned_project.get_tasks().values_list('pk', flat=True)))

        c_task1 = cloned_project.get_tasks().get(title='1')
        c_task11 = cloned_project.get_tasks().get(title='1.1')
        c_task111 = cloned_project.get_tasks().get(title='1.1.1')
        c_task1111 = cloned_project.get_tasks().get(title='1.1.1.1')

        c_task_all_1 = cloned_project.get_tasks().get(title='all 1')

        c_task2 = cloned_project.get_tasks().get(title='2')

        c_task_all = cloned_project.get_tasks().get(title='all 2')

        self.assertEqual(set(), set(c_task1.get_parents().values_list('title', flat=True)))
        self.assertEqual(set(['1']), set(c_task11.get_parents().values_list('title', flat=True)))
        self.assertEqual(set(['1.1']), set(c_task111.get_parents().values_list('title', flat=True)))
        self.assertEqual(set(['1.1.1']), set(c_task1111.get_parents().values_list('title', flat=True)))

        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1']), set(c_task_all_1.get_parents().values_list('title', flat=True)))
        
        self.assertEqual(set(), set(c_task2.get_parents().values_list('title', flat=True)))

        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1', '2']), set(c_task_all.get_parents().values_list('title', flat=True)))


    def test_project_clone02(self):
        self.login()
        self.populate('creme_core', 'activities')
        user = self.user

        project, manager = self.create_project('Project')
        contact1 = Contact.objects.create(user=self.user)
        contact2 = Contact.objects.create(user=self.user)

        task1 = self._create_task('1', project)
        resource1 = self._create_resource(contact1, task1)
        resource2 = self._create_resource(contact2, task1)
        work_period1 = self._create_working_period(task1, resource1)
        work_period2 = self._create_working_period(task1, resource2)

        task2 = self._create_task('2', project)
        resource3 = self._create_resource(contact1, task2)
        resource4 = self._create_resource(contact2, task2)
        work_period3 = self._create_working_period(task2, resource3)
        work_period4 = self._create_working_period(task2, resource4)

        task3 = self._create_task('3', project, [task1, task2])
        task4 = self._create_task('4', project, [task3])

        cloned_project = project.clone()

        for attr in ['name', 'description', 'status', 'start_date', 'end_date', 'effective_end_date']:
            self.assertEqual(getattr(project, attr), getattr(cloned_project, attr))

        c_tasks1 = cloned_project.get_tasks().get(title='1')
        c_tasks2 = cloned_project.get_tasks().get(title='2')
        c_tasks3 = cloned_project.get_tasks().get(title='3')
        c_tasks4 = cloned_project.get_tasks().get(title='4')
        
        self.assertEqual(set(['1', '2', '3', '4']), set(cloned_project.get_tasks().values_list('title', flat=True)))
        self.assertNotEqual(set(project.get_tasks().values_list('pk', flat=True)), set(cloned_project.get_tasks().values_list('pk', flat=True)))

        self.assertEqual(set(['1', '2']), set(c_tasks3.get_parents().values_list('title', flat=True)))
        self.assertEqual(set(['3']), set(c_tasks4.get_parents().values_list('title', flat=True)))

        self.assertEqual(set([contact1.pk, contact2.pk]), set(c_tasks1.get_resources().values_list('linked_contact', flat=True)))
        self.assertEqual(set([contact1.pk, contact2.pk]), set(c_tasks2.get_resources().values_list('linked_contact', flat=True)))

        self.assertEqual(set([resource1.pk, resource2.pk]), set(c_tasks1.get_working_periods().values_list('resource', flat=True)))
        self.assertEqual(set([resource3.pk, resource4.pk]), set(c_tasks2.get_working_periods().values_list('resource', flat=True)))

    #TODO: test better get_project_cost(), get_effective_duration(), get_delay()
