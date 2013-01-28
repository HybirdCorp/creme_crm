# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date, time
    from functools import partial

    from django.utils.translation import ugettext as _

    from creme_core.models import RelationType, Relation, SetCredentials
    from creme_core.tests.base import CremeTestCase
    from creme_core.utils.dates import get_dt_from_str

    from persons.models import Contact

    from activities.models import Calendar
    from activities.constants import REL_SUB_PART_2_ACTIVITY

    from projects.models import *
    from projects.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class ProjectsTestCase(CremeTestCase):
    ADD_PROJECT_URL = '/projects/project/add'
    ADD_TASK_PARENT_URL = '/projects/task/%s/parent/add'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities', 'projects')

    def login(self, is_superuser=True, *args, **kwargs):
        super(ProjectsTestCase, self).login(is_superuser, allowed_apps=['projects'], *args, **kwargs)

    def _build_add_ask_url(self, project):
        return '/projects/project/%s/task/add' % project.id

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_PROJECT_MANAGER, sub_models=[Contact], obj_models=[Project])

        self.assertGreaterEqual(TaskStatus.objects.count(), 2)
        self.assertTrue(ProjectStatus.objects.exists())

    def test_portal(self):
        self.login()
        self.assertGET200('/projects/')

    def create_project(self, name, status=None, start_date='2010-10-11', end_date='2010-12-31'):
        status = status or ProjectStatus.objects.all()[0]
        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        response = self.client.post(self.ADD_PROJECT_URL, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'status':       status.id,
                                          'start_date':   start_date,
                                          'end_date':     end_date,
                                          'responsibles': manager.id,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Project, name=name), manager

    def test_project_createview01(self):
        self.login()

        self.assertGET200(self.ADD_PROJECT_URL)

        name = 'Eva00'
        status = ProjectStatus.objects.all()[0]
        project, manager = self.create_project(name, status, '2010-10-11', '2010-12-31')
        self.assertEqual(self.user, project.user)
        self.assertEqual(name,      project.name)
        self.assertEqual(status,    project.status)
        self.assertEqual(datetime(year=2010, month=10, day=11), project.start_date)
        self.assertEqual(datetime(year=2010, month=12, day=31), project.end_date)
        self.assertRelationCount(1, project, REL_OBJ_PROJECT_MANAGER, manager)

    def test_project_createview02(self): #credentials error
        self.login(is_superuser=False, creatable_models=[Project])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | \
                        SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | \
                        SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | \
                        SetCredentials.CRED_UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        self.assertFalse(manager.can_link(self.user))

        response = self.client.post(self.ADD_PROJECT_URL, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'Eva00',
                                          'status':       ProjectStatus.objects.all()[0].id,
                                          'start_date':   '2011-10-11',
                                          'end_date':     '2011-12-31',
                                          'responsibles': manager.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'responsibles',
                             [_(u"Some entities are not linkable: %s") % (_(u'Entity #%s (not viewable)') % manager.id)]
                            )

    def test_project_createview03(self): #validation error with start/end
        self.login()

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        response = self.client.post(self.ADD_PROJECT_URL, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         'Eva00',
                                          'status':       ProjectStatus.objects.all()[0].id,
                                          'start_date':   '2012-2-16',
                                          'end_date':     '2012-2-15',
                                          'responsibles': manager.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', None, [_(u'Start must be before end.')])

    def test_project_lisview(self):
        self.login()

        self.create_project('Eva00')
        self.create_project('Eva01')
        self.assertGET200('/projects/projects')

    def test_project_inner_edit01(self):
        self.login()

        project = self.create_project('Eva01', start_date='2012-2-16', end_date='2012-3-26')[0]
        url = '/creme_core/entity/edit/%s/%s/field/%s' % (project.entity_type_id, project.id, 'start_date')
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'entities_lbl': [unicode(project)],
                                               'field_value':  '2012-3-4',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(datetime(year=2012, month=3, day=4), self.refresh(project).start_date)

    def test_project_inner_edit02(self): #validation error
        self.login()

        project = self.create_project('Eva01', start_date='2012-2-16', end_date='2012-3-26')[0]
        response = self.client.post('/creme_core/entity/edit/%s/%s/field/%s' % (project.entity_type_id, project.id, 'start_date'),
                                    data={'entities_lbl': [unicode(project)],
                                          'field_value':  '2012-3-27', #<= after end_date
                                         }
                                   )
        self.assertFormError(response, 'form', None, [_(u'Start must be before end.')])
        self.assertEqual(datetime(year=2012, month=2, day=16), self.refresh(project).start_date)

    def test_task_createview01(self): #create 2 tasks without collisions
        self.login()

        user = self.user
        contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')

        project = self.create_project('Eva01')[0]

        url = self._build_add_ask_url(project)
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'user':               user.id,
                                          'title':              'head',
                                          'start':              '2010-10-11 15:00',
                                          'end':                '2010-10-11 17:00',
                                          'duration':           50,
                                          'tstatus':            TaskStatus.objects.all()[0].id,
                                          'participating_users':user.id,
                                          'busy':               True
                                         }
                                   )
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(1, task1.order)
        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, task1)
        self.assertEqual(1, task1.calendars.count())

        response = self.client.post(url, follow=True,
                                    data={'user':               user.id,
                                          'title':              'torso',
                                          'start':              '2010-10-11 17:01',
                                          'end':                '2010-10-11 17:30',
                                          'duration':           180,
                                          'tstatus':            TaskStatus.objects.all()[0].id,
                                          'parent_tasks':       task1.id,
                                          'participating_users':user.id
                                         }
                                   )
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(2, tasks.count())

        tasks2 = filter(lambda t: t.id != task1.id, tasks)
        task2 = tasks2[0]
        self.assertEqual(1,          len(tasks2))
        self.assertEqual([task1.id], [t.id for t in task2.parent_tasks.all()])

        self.assertEqual(list(tasks), list(project.get_tasks()))
        self.assertEqual(180 + 50,    project.get_expected_duration())

        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, task2)
        self.assertEqual(1, task2.calendars.count())

    def test_task_createview02(self): #can be parented with task of an other project
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Title')
        response = self.client.post(self._build_add_ask_url(project02), #follow=True,
                                    data={'user':         self.user.id,
                                          'title':        'head',
                                          'start':        '2010-10-11',
                                          'end':          '2010-10-30',
                                          'duration':     50,
                                          'tstatus':      TaskStatus.objects.all()[0].id,
                                          'parent_tasks': task01.id,
                                         }
                                   )
        self.assertFormError(response, 'form', 'parent_tasks',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task01.id}]
                            )

    def test_task_createview03(self): #create 2 tasks with a collision
        self.login()

        user = self.user
        contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')

        project = self.create_project('Eva01')[0]

        url = self._build_add_ask_url(project)
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'user':               user.id,
                                          'title':              'head',
                                          'start':              '2010-10-11 15:00',
                                          'end':                '2010-10-11 17:00',
                                          'duration':           50,
                                          'tstatus':            TaskStatus.objects.all()[0].id,
                                          'participating_users':user.id,
                                          'busy':               True,
                                         }
                                    )
        self.assertEqual(200, response.status_code)

        task2_start = get_dt_from_str('2010-10-11 16:59')
        task2_end = get_dt_from_str('2010-10-11 17:30')
        response = self.client.post(url, follow=True,
                                    data={'user':               user.id,
                                          'title':              'torso',
                                          'start':              task2_start,
                                          'end':                task2_end,
                                          'duration':           180,
                                          'tstatus':            TaskStatus.objects.all()[0].id,
                                          'participating_users':user.id
                                         }
                                   )

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, tasks.count())
        task1 = tasks[0]

        self.assertFormError(response, 'form', None,
            [_(u'%(participant)s already participates to the activity «%(activity)s» between %(start)s and %(end)s.') % {
                    'participant': contact,
                    'activity':    task1,
                    'start':       max(task2_start.time(), task1.start.time()),
                    'end':         min(task2_end.time(),   task1.end.time()),
                }
            ]
        )

    def test_task_editview01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')
        url = '/projects/task/edit/%s' % task.id
        self.assertGET200(url)

        title = 'Head'
        duration = 55
        tstatus  = TaskStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':     self.user.id,
                                          'title':    title,
                                          'start':    '2011-5-16',
                                          'end':      '2012-6-17',
                                          'duration': duration,
                                          'tstatus':  tstatus.id,
                                         }
                                   )
        self.assertNoFormError(response)

        task = self.refresh(task)
        self.assertEqual(title,    task.title)
        self.assertEqual(duration, task.duration)
        self.assertEqual(tstatus,  task.tstatus)
        self.assertEqual(date(year=2011, month=5, day=16), task.start.date())
        self.assertEqual(date(year=2012, month=6, day=17), task.end.date())

    def test_task_editview02(self):
        "Popup version"
        self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')
        url = '/projects/task/edit/%s/popup' % task.id
        self.assertGET200(url)

        title = 'Head'
        duration = 55
        response = self.client.post(url, follow=True,
                                    data={'user':     self.user.id,
                                          'title':    title,
                                          'start':    '2011-5-16',
                                          'end':      '2012-6-17',
                                          'duration': duration,
                                          'tstatus':  TaskStatus.objects.all()[0].id,
                                         }
                                   )
        self.assertNoFormError(response)

        task = self.refresh(task)
        self.assertEqual(title,    task.title)
        self.assertEqual(duration, task.duration)
        self.assertEqual(date(year=2011, month=5, day=16), task.start.date())
        self.assertEqual(date(year=2012, month=6, day=17), task.end.date())

    def test_task_add_parent01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Parent01')
        task02 = self.create_task(project, 'Parent02')
        task03 = self.create_task(project, 'Task')

        url = self.ADD_TASK_PARENT_URL % task03.id
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'parents': '%s,%s' % (task01.id, task02.id)}))
        self.assertEqual(set([task01, task02]), set(task03.parent_tasks.all()))

        self.assertPOST200('/projects/task/parent/delete', data={'id': task03.id, 'parent_id': task01.id})
        self.assertEqual([task02], list(task03.parent_tasks.all()))

        #Error: already parent
        self.assertFormError(self.client.post(url, data={'parents': task02.id}),
                             'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task02.id}]
                            )

    def test_task_add_parent02(self): #error task that belong to another project
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Task01')
        task02 = self.create_task(project02, 'Task02')

        response = self.client.post(self.ADD_TASK_PARENT_URL % task02.id,
                                    data={'parents': task01.id}
                                   )
        self.assertFormError(response, 'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task01.id}]
                            )

    def test_task_add_parent03(self): #cycle error
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Task01')
        task02 = self.create_task(project, 'Task02')
        task03 = self.create_task(project, 'Task03')

        self.assertEqual([task01], list(task01.get_subtasks()))

        url = self.ADD_TASK_PARENT_URL
        self.assertNoFormError(self.client.post(url % task02.id, data={'parents': task01.id}))
        self.assertEqual(set([task01, task02]), set(task01.get_subtasks()))

        self.assertNoFormError(self.client.post(url % task03.id, data={'parents': task02.id}))
        self.assertEqual(set([task01, task02, task03]), set(task01.get_subtasks()))

        response = self.client.post(url % task01.id, data={'parents': task03.id})
        self.assertFormError(response, 'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {
                                    'value': task03.id,
                                 }
                             ]
                            )

    def create_task(self, project, title, status=None):
        status = status or TaskStatus.objects.all()[0]
        response = self.client.post(self._build_add_ask_url(project), follow=True,
                                    data={'user':     self.user.id,
                                          'title':    title,
                                          'start':    '2010-10-11',
                                          'end':      '2010-10-30',
                                          'duration': 50,
                                          'tstatus':  status.id,
                                         }
                                   )
        #self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        return self.get_object_or_fail(ProjectTask, project=project, title=title)

    def test_resource_n_period01(self): #createviews
        self.login()

        project = self.create_project('Eva02')[0]
        task    = self.create_task(project, 'legs')
        self.assertFalse(task.resources_set.all())

        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={'user':           self.user.id,
                                          'linked_contact': worker.id,
                                          'hourly_cost':    100,
                                         }
                                   )
        self.assertNoFormError(response)

        resources = list(task.resources_set.all())
        self.assertEqual(1, len(resources))

        resource = resources[0]
        self.assertFalse(resource.workingperiod_set.exists())

        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={'resource':   resource.id,
                                          'start_date': '2010-10-11',
                                          'end_date':   '2010-10-12',
                                          'duration':   8,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, resource.workingperiod_set.count())

        self.assertEqual(8,   task.get_effective_duration())
        self.assertEqual(800, task.get_task_cost()) #8 * 100
        self.assertEqual(-42, task.get_delay()) # 8 - 50
        self.assertTrue(task.is_alive())

        self.assertEqual(8,   project.get_effective_duration())
        self.assertEqual(800, project.get_project_cost()) #8 * 100
        self.assertEqual(0,   project.get_delay())

    def test_resource_n_period02(self): #editviews
        self.login()

        project  = self.create_project('Eva02')[0]
        task     = self.create_task(project, 'arms')
        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={'user':           self.user.id,
                                          'linked_contact': worker.id,
                                          'hourly_cost':    100,
                                         }
                                   )
        resource = task.resources_set.all()[0]
        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={'resource':   resource.id,
                                          'start_date': '2010-10-11',
                                          'end_date':   '2010-10-12',
                                          'duration':   8,
                                         }
                                   )

        url = '/projects/resource/edit/%s' % resource.id
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'user':           self.user.id,
                                          'linked_contact': worker.id,
                                          'hourly_cost':    200,
                                         }
                                   )
        self.assertNoFormError(response)

        resource = self.refresh(resource)
        self.assertEqual(200, resource.hourly_cost)

        wperiods = list(resource.workingperiod_set.all())
        self.assertEqual(1, len(wperiods))

        wperiod = wperiods[0]
        url = '/projects/period/edit/%s' % wperiod.id
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'resource':   resource.id,
                                          'start_date': '2010-10-11',
                                          'end_date':   '2010-10-12',
                                          'duration':   10,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        wperiod = self.refresh(wperiod)
        self.assertEqual(10, wperiod.duration)

    def test_project_close(self):
        self.login()

        project = self.create_project('Eva01')[0]
        self.assertFalse(project.is_closed)
        self.assertIsNone(project.effective_end_date)

        url = '/projects/project/%s/close' % project.id
        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        project = self.refresh(project)
        self.assertTrue(project.is_closed)
        self.assertTrue(project.effective_end_date)

        delta = datetime.combine(date.today(), time()) - project.effective_end_date
        self.assertLess(delta.seconds, 10)

        #already closed
        self.assertEqual(404, self.client.post(url, follow=True).status_code)

    def _create_task(self, title, project, parents=None):
        status = TaskStatus.objects.get_or_create(name='status', description="")[0]
        task = ProjectTask.objects.create(project=project, order=0, duration=0, tstatus=status, user=self.user, title=title)
        if parents is not None:
            task.parent_tasks = parents
        return task

    def _create_resource(self, contact, task):
        return Resource.objects.create(linked_contact=contact, user=self.user, task=task)

    def _create_working_period(self, task, resource):
        return WorkingPeriod.objects.create(task=task, resource=resource)

    def _titles_collections(self, tasks_qs, constructor):
        return constructor(tasks_qs.values_list('title', flat=True))

    _titles_list = lambda self, tasks_qs: self._titles_collections(tasks_qs, list)
    _titles_set  = lambda self, tasks_qs: self._titles_collections(tasks_qs, set)

    def _tasks_pk_set(self, project):
        return set(project.get_tasks().values_list('pk', flat=True))

    def test_project_clone01(self):
        self.login()

        user = self.user
        project = self.create_project('Project')[0]

        create_task = self._create_task
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
        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2']),
                         titles_set(cloned_project.get_tasks())
                        )

        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        get_task = cloned_project.get_tasks().get
        self.assertFalse(get_task(title='1').get_parents())
        self.assertEqual(['1'],     titles_list(get_task(title='1.1').get_parents()))
        self.assertEqual(['1.1'],   titles_list(get_task(title='1.1.1').get_parents()))
        self.assertEqual(['1.1.1'], titles_list(get_task(title='1.1.1.1').get_parents()))
        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1']),
                         titles_set(get_task(title='all 1').get_parents())
                        )
        self.assertFalse(get_task(title='2').get_parents())
        self.assertEqual(set(['1', '1.1', '1.1.1', '1.1.1.1', '2']),
                         titles_set(get_task(title='all 2').get_parents())
                        )

    def test_project_clone02(self):
        self.login()

        user = self.user

        project = self.create_project('Project')[0]
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

        get_task = cloned_project.get_tasks().get
        c_task1 = get_task(title='1')
        c_task2 = get_task(title='2')

        self.assertEqual(set(['1', '2', '3', '4']), self._titles_set(cloned_project.get_tasks()))
        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        self.assertEqual(set(['1', '2']), self._titles_set(get_task(title='3').get_parents()))
        self.assertEqual(['3'],           self._titles_list(get_task(title='4').get_parents()))

        linked_contacts_set = lambda task: set(task.get_resources().values_list('linked_contact', flat=True))
        self.assertEqual(set([contact1.pk, contact2.pk]), linked_contacts_set(c_task1))
        self.assertEqual(set([contact1.pk, contact2.pk]), linked_contacts_set(c_task2))

        resource_set = lambda task: set(task.get_working_periods().values_list('resource', flat=True))
        self.assertEqual(set([resource1.pk, resource2.pk]), resource_set(c_task1))
        self.assertEqual(set([resource3.pk, resource4.pk]), resource_set(c_task2))

    def _delete_project_status(self, status):
        return self.client.post('/creme_config/projects/projectstatus/delete', data={'id': status.pk})

    def test_delete_project_status01(self):
        self.login()

        status = ProjectStatus.objects.create(name='Sinking')
        self.assertEqual(200, self._delete_project_status(status).status_code)
        self.assertFalse(ProjectStatus.objects.filter(pk=status.pk).exists())

    def test_delete_project_status02(self):
        self.login()

        status = ProjectStatus.objects.create(name='Sinking')
        project = self.create_project('Project', status=status)[0]
        self.assertEqual(404, self._delete_project_status(status).status_code)
        self.assertTrue(ProjectStatus.objects.filter(pk=status.pk).exists())

        project = self.get_object_or_fail(Project, pk=project.pk)
        self.assertEqual(status, project.status)

    def _delete_task_status(self, status):
        return self.client.post('/creme_config/projects/taskstatus/delete', data={'id': status.pk})

    def test_delete_task_status01(self):
        self.login()

        status = TaskStatus.objects.create(name='Coming soon')
        self.assertEqual(200, self._delete_task_status(status).status_code)
        self.assertFalse(TaskStatus.objects.filter(pk=status.pk).exists())

    def test_delete_task_status02(self):
        self.login()

        project = self.create_project('Eva01')[0]
        status  = TaskStatus.objects.create(name='Coming soon')
        task    = self.create_task(project, 'Building head', status=status)
        self.assertEqual(404, self._delete_task_status(status).status_code)
        self.assertTrue(TaskStatus.objects.filter(pk=status.pk).exists())

        self.get_object_or_fail(Project, pk=project.pk)
        task = self.get_object_or_fail(ProjectTask, pk=task.pk)
        self.assertEqual(status, task.tstatus)

    #TODO: test better get_project_cost(), get_effective_duration(), get_delay()
