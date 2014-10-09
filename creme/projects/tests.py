# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.formats import date_format
    from django.utils.simplejson.encoder import JSONEncoder
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import SetCredentials
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    #from creme.creme_core.utils.dates import get_dt_from_str

    from creme.persons.models import Contact

    #from creme.activities.models import Calendar
    from creme.activities.constants import (REL_SUB_PART_2_ACTIVITY,
            ACTIVITYTYPE_TASK, ACTIVITYTYPE_MEETING,
            ACTIVITYSUBTYPE_MEETING_MEETING, ACTIVITYSUBTYPE_MEETING_QUALIFICATION) # NARROW

    from .models import *
    from .constants import *
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

    def _build_add_resource_url(self, task):
        return '/projects/task/%s/resource/add' % task.id

    def _build_type_value(self, atype=ACTIVITYTYPE_TASK, sub_type=None):
        return JSONEncoder().encode({'type': atype, 'sub_type': sub_type})

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_PROJECT_MANAGER,
                                      sub_models=[Contact],
                                      obj_models=[Project],
                                     )

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
                                          'responsibles': '[%d]' % manager.id,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Project, name=name), manager

    def create_task(self, project, title, status=None, atype=ACTIVITYTYPE_TASK, sub_type=None):
        status = status or TaskStatus.objects.get(pk=NOT_STARTED_PK)
        response = self.client.post(self._build_add_ask_url(project), follow=True,
                                    data={'user':          self.user.id,
                                          'title':         title,
                                          'start':         '2010-10-11',
                                          'end':           '2010-10-30',
                                          'duration':      50,
                                          'tstatus':       status.id,
                                          'type_selector': self._build_type_value(atype, sub_type),
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ProjectTask, project=project, title=title)

    def test_project_createview01(self):
        self.login()

        self.assertGET200(self.ADD_PROJECT_URL)

        name = 'Eva00'
        status = ProjectStatus.objects.all()[0]
        project, manager = self.create_project(name, status, '2010-10-11', '2010-12-31')
        self.assertEqual(self.user, project.user)
        self.assertEqual(name,      project.name)
        self.assertEqual(status,    project.status)

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2010, month=10, day=11), project.start_date)
        self.assertEqual(create_dt(year=2010, month=12, day=31), project.end_date)

        self.assertRelationCount(1, project, REL_OBJ_PROJECT_MANAGER, manager)

    def test_project_createview02(self):
        "Credentials error"
        self.login(is_superuser=False, creatable_models=[Project])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.LINK |
                        EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        self.assertFalse(self.user.has_perm_to_link(manager))

        response = self.assertPOST200(self.ADD_PROJECT_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'Eva00',
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2011-10-11',
                                            'end_date':     '2011-12-31',
                                            'responsibles': '[%d]' % manager.id,
                                           }
                                     )
        self.assertFormError(response, 'form', 'responsibles',
                             _(u"Some entities are not linkable: %s") % (
                                    _(u'Entity #%s (not viewable)') % manager.id
                                )
                            )

    def test_project_createview03(self):
        "Validation error with start/end"
        self.login()

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        response = self.assertPOST200(self.ADD_PROJECT_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'Eva00',
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2012-2-16',
                                            'end_date':     '2012-2-15',
                                            'responsibles': '[%d]' % manager.id,
                                           }
                                     )
        self.assertFormError(response, 'form', None, _(u'Start (%(start)s) must be before end (%(end)s).') % {
                                                         'start': date_format(self.create_datetime(2012, 2, 16), 'DATE_FORMAT'),
                                                         'end': date_format(self.create_datetime(2012, 2, 15), 'DATE_FORMAT'),
                                                      })

    def test_project_lisview(self):
        self.login()

        self.create_project('Eva00')
        self.create_project('Eva01')
        self.assertGET200('/projects/projects')

    def _build_inner_edit_url(self, entity, field): #TODO: in creme_core ??
        url = '/creme_core/entity/edit/inner/%(ct)s/%(id)s/field/%(field)s'
        return url % {'ct': entity.entity_type_id, 'id': entity.id, 'field': field}

    def test_project_inner_edit01(self):
        self.login()

        project = self.create_project('Eva01', start_date='2012-2-16', end_date='2012-3-26')[0]
        url = self._build_inner_edit_url(project, 'start_date')
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'entities_lbl': [unicode(project)],
                                                           'field_value':  '2012-3-4',
                                                          }
                                                )
                              )
        self.assertEqual(self.create_datetime(year=2012, month=3, day=4),
                         self.refresh(project).start_date
                        )

    def test_project_inner_edit02(self):
        "Validation error"
        self.login()

        project = self.create_project('Eva01', start_date='2012-02-20', end_date='2012-03-25')[0]
        response = self.assertPOST200(self._build_inner_edit_url(project, 'start_date'),
                                      data={'entities_lbl': [unicode(project)],
                                            'field_value':  '2012-03-27', #<= after end_date
                                           }
                                     )

        self.assertFormError(response, 'form', None, _(u'Start (%(start)s) must be before end (%(end)s).') % {
                                                         'start': date_format(self.create_datetime(2012, 3, 27), 'DATE_FORMAT'),
                                                         'end': date_format(self.create_datetime(2012, 3, 25), 'DATE_FORMAT'),
                                                      })

        self.assertEqual(self.create_datetime(year=2012, month=2, day=20),
                         self.refresh(project).start_date
                        )

    def test_task_createview01(self):
        "Create 2 tasks without collisions"
        self.login()

        user = self.user
        #contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')
        #contact = self.get_object_or_fail(Contact, is_user=user)
        contact = user.linked_contact

        project = self.create_project('Eva01')[0]

        url = self._build_add_ask_url(project)
        self.assertGET200(url)

        def post(duration):
            return self.client.post(url, follow=True,
                                    data={'user':                user.id,
                                          'title':               'head',
                                          'start':               '2010-10-11 15:00',
                                          'end':                 '2010-10-11 17:00',
                                          'duration':            duration,
                                          'tstatus':             TaskStatus.objects.all()[0].id,
                                          'participating_users': user.id,
                                          'busy':                True,
                                          'type_selector':       self._build_type_value(),
                                         }
                                    )

        response = post('')
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'duration', _('This field is required.'))

        duration_1 = 50
        response = post(duration_1)
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(1, task1.order)
        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, task1)
        self.assertEqual(1, task1.calendars.count())

        duration_2 = 180
        response = self.client.post(url, follow=True,
                                    data={'user':                user.id,
                                          'title':               'torso',
                                          'start':               '2010-10-11 17:01',
                                          'end':                 '2010-10-11 17:30',
                                          'duration':            duration_2,
                                          'tstatus':             TaskStatus.objects.all()[0].id,
                                          'parent_tasks':        '[%d]' % task1.id,
                                          'participating_users': user.id,
                                          'type_selector':       self._build_type_value(),
                                         }
                                   )
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(2, tasks.count())

        tasks2 = [t for t in tasks if t.id != task1.id]
        self.assertEqual(1, len(tasks2))

        task2 = tasks2[0]
        self.assertEqual([task1.id], [t.id for t in task2.parent_tasks.all()])

        self.assertEqual(set(tasks), set(project.get_tasks()))
        self.assertEqual(duration_1 + duration_2,   project.get_expected_duration())

        self.assertRelationCount(1, contact, REL_SUB_PART_2_ACTIVITY, task2)
        self.assertEqual(1, task2.calendars.count())

    def test_task_createview02(self):
        "Can not be parented with task of an other project"
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Title')
        response = self.client.post(self._build_add_ask_url(project02), #follow=True,
                                    data={'user':          self.user.id,
                                          'title':         'head',
                                          'start':         '2010-10-11',
                                          'end':           '2010-10-30',
                                          'duration':      50,
                                          'tstatus':       TaskStatus.objects.all()[0].id,
                                          'parent_tasks':  '[%d]' % task01.id,
                                          'type_selector': self._build_type_value(),
                                         }
                                   )
        self.assertFormError(response, 'form', 'parent_tasks',
                             _(u"This entity doesn't exist.")
                            )

    def test_task_createview03(self):
        "Create 2 tasks with a collision"
        self.login()

        user = self.user
        #contact = Contact.objects.create(user=user, is_user=user, first_name='Rally', last_name='Vincent')
        #contact = self.get_object_or_fail(Contact, is_user=user)
        contact = user.linked_contact

        project = self.create_project('Eva01')[0]

        url = self._build_add_ask_url(project)
        self.assertGET200(url)
        self.assertPOST200(url, follow=True,
                           data={'user':                user.id,
                                 'title':               'head',
                                 'start':               '2010-10-11 15:00',
                                 'end':                 '2010-10-11 17:00',
                                 'duration':            50,
                                 'tstatus':             TaskStatus.objects.all()[0].id,
                                 'participating_users': user.id,
                                 'busy':                True,
                                 'type_selector':       self._build_type_value(),
                                }
                          )

        #task2_start = get_dt_from_str('2010-10-11 16:59')
        #task2_end = get_dt_from_str('2010-10-11 17:30')
        task2_start = '2010-10-11 16:59'
        task2_end   = '2010-10-11 17:30'
        response = self.client.post(url, follow=True,
                                    data={'user':                user.id,
                                          'title':               'torso',
                                          'start':               task2_start,
                                          'end':                 task2_end,
                                          'duration':            180,
                                          'tstatus':             TaskStatus.objects.all()[0].id,
                                          'participating_users': user.id,
                                          'type_selector':       self._build_type_value(),
                                         }
                                   )

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, len(tasks))
        task1 = tasks[0]

        self.assertFormError(response, 'form', None,
            _(u'%(participant)s already participates to the activity «%(activity)s» between %(start)s and %(end)s.') % {
                    'participant': contact,
                    'activity':    task1,
                    #'start':       max(task2_start.time(), task1.start.time()),
                    #'end':         min(task2_end.time(),   task1.end.time()),
                    'start':       '16:59:00',
                    'end':         '17:00:00',
                }
        )

    def test_task_createview04(self):
        "Create task with 'Meeting' type"
        self.login()

        project = self.create_project('Eva01')[0]
        title = 'Head'
        atype = ACTIVITYTYPE_MEETING
        stype = ACTIVITYSUBTYPE_MEETING_MEETING
        response = self.client.post(self._build_add_ask_url(project), follow=True,
                                    data={'user':          self.user.id,
                                          'title':         title,
                                          'start':         '2013-7-1',
                                          'end':           '2013-7-14',
                                          'duration':      50,
                                          'tstatus':       TaskStatus.objects.all()[0].id,
                                          'type_selector': self._build_type_value(atype, stype),
                                         }
                                   )
        self.assertNoFormError(response)

        task = self.get_object_or_fail(ProjectTask, title=title, project=project)
        self.assertEqual(atype, task.type_id)
        self.assertEqual(stype, task.sub_type_id)

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

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2011, month=5, day=16), task.start)
        self.assertEqual(create_dt(year=2012, month=6, day=17), task.end)

    def test_task_editview02(self):
        "Meeting type"
        self.login()

        atype = ACTIVITYTYPE_MEETING
        task = self.create_task(self.create_project('Eva01')[0],
                                'Title', atype=atype,
                                sub_type=ACTIVITYSUBTYPE_MEETING_MEETING,
                               )

        stype = ACTIVITYSUBTYPE_MEETING_QUALIFICATION
        response = self.client.post('/projects/task/edit/%s' % task.id, follow=True, #TODO: factorise
                                    data={'user':     self.user.id,
                                          'title':    'Head',
                                          'start':    '2013-5-16',
                                          'end':      '2013-6-17',
                                          'duration': 60,
                                          'tstatus':  TaskStatus.objects.all()[1].id,
                                          'sub_type': stype,
                                         }
                                   )
        self.assertNoFormError(response)

        task = self.refresh(task)
        self.assertEqual(atype, task.type_id)
        self.assertEqual(stype, task.sub_type_id)

    def test_task_editview_popup01(self):
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

        create_dt = self.create_datetime
        self.assertEqual(create_dt(year=2011, month=5, day=16), task.start)
        self.assertEqual(create_dt(year=2012, month=6, day=17), task.end)

    def test_task_add_parent01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Parent01')
        task02 = self.create_task(project, 'Parent02')
        task03 = self.create_task(project, 'Task')

        url = self.ADD_TASK_PARENT_URL % task03.id
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'parents': '[%d,%d]' % (task01.id, task02.id)}))
        self.assertEqual({task01, task02}, set(task03.parent_tasks.all()))

        self.assertPOST200('/projects/task/parent/delete', data={'id': task03.id, 'parent_id': task01.id})
        self.assertEqual([task02], list(task03.parent_tasks.all()))

        #Error: already parent
        self.assertFormError(self.client.post(url, data={'parents': '[%d]' % task02.id}),
                             'form', 'parents',
                             _(u"This entity doesn't exist.")
                            )

    def test_task_add_parent02(self):
        "Error task that belongs to another project"
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Task01')
        task02 = self.create_task(project02, 'Task02')

        response = self.client.post(self.ADD_TASK_PARENT_URL % task02.id,
                                    data={'parents': '[%d]' % task01.id}
                                   )
        self.assertFormError(response, 'form', 'parents',
                             _(u"This entity doesn't exist.")
                            )

    def test_task_add_parent03(self):
        "Cycle error"
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Task01')
        task02 = self.create_task(project, 'Task02')
        task03 = self.create_task(project, 'Task03')

        self.assertEqual([task01], list(task01.get_subtasks()))

        url = self.ADD_TASK_PARENT_URL
        self.assertNoFormError(self.client.post(url % task02.id, data={'parents': '[%d]' % task01.id}))
        self.assertEqual({task01, task02}, set(task01.get_subtasks()))

        self.assertNoFormError(self.client.post(url % task03.id, data={'parents': '[%d]' % task02.id}))
        self.assertEqual({task01, task02, task03}, set(task01.get_subtasks()))

        response = self.client.post(url % task01.id, data={'parents': '[%d]' % task03.id})
        self.assertFormError(response, 'form', 'parents',
                             [_(u"This entity doesn't exist.")]
                            )

    def test_duration01(self):
        self.login()
        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')

        self.assertEqual(50, task.duration)
        self.assertEqual(50, task.safe_duration)

        self.assertEqual(0, task.get_effective_duration())
        self.assertEqual(0, task.get_effective_duration('%'))

        self.assertEqual(-50, task.get_delay())
        self.assertEqual(50, project.get_expected_duration())

    def test_duration02(self):
        self.login()
        project = self.create_project('Eva01')[0]

        task = self.create_task(project, 'Title')
        task.duration = None #can be edited as an Activity...
        task.save()

        self.assertEqual(0, task.safe_duration)

        self.assertEqual(0,   task.get_effective_duration())
        self.assertEqual(100, task.get_effective_duration('%'))

        self.assertEqual(0, task.get_delay())
        self.assertEqual(0, project.get_expected_duration())

    def test_resource_n_period01(self):
        "Creation views"
        self.login()

        project = self.create_project('Eva02')[0]
        task    = self.create_task(project, 'legs')
        self.assertFalse(task.resources_set.all())

        url = self._build_add_resource_url(task)
        self.assertGET200(url)

        worker = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post(url, follow=True,
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

    def test_resource_n_period02(self):
        "Edition views"
        self.login()

        project  = self.create_project('Eva02')[0]
        task     = self.create_task(project, 'arms')
        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        self.client.post(self._build_add_resource_url(task), follow=True,
                         data={'user':           self.user.id,
                               'linked_contact': worker.id,
                               'hourly_cost':    100,
                              }
                        )
        resource = task.resources_set.all()[0]
        self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                         data={'resource':   resource.id,
                               'start_date': '2010-10-11',
                               'end_date':   '2010-10-12',
                               'duration':   8,
                              }
                        )

        #url = '/projects/resource/edit/%s' % resource.id
        url = resource.get_edit_absolute_url()
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
        #url = '/projects/period/edit/%s' % wperiod.id
        url = wperiod.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'resource':   resource.id,
                                          'start_date': '2010-10-11',
                                          'end_date':   '2010-10-12',
                                          'duration':   10,
                                         }
                                   )
        self.assertNoFormError(response)

        wperiod = self.refresh(wperiod)
        self.assertEqual(10, wperiod.duration)

    def test_resource_n_period03(self):
        "Not alive task"
        self.login()

        project = self.create_project('Eva02')[0]
        status  = self.get_object_or_fail(TaskStatus, id=COMPLETED_PK)
        task    = self.create_task(project, 'legs', status=status)

        url = self._build_add_resource_url(task)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/error.html')

        worker = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post(url, follow=True,
                                    data={'user':           self.user.id,
                                          'linked_contact': worker.id,
                                          'hourly_cost':    100,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertFalse(task.resources_set.all())
        self.assertTemplateUsed(response, 'creme_core/generics/error.html')

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

        self.assertDatetimesAlmostEqual(now(), project.effective_end_date)

        #already closed
        self.assertPOST404(url, follow=True)

    def _create_parented_task(self, title, project, parents=None):
        status = TaskStatus.objects.get_or_create(name='status', description="")[0]
        task = ProjectTask.objects.create(project=project, order=0, duration=0,
                                          tstatus=status, user=self.user,
                                          title=title, type_id=ACTIVITYTYPE_TASK,
                                         )

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
        self.assertEqual({'1', '1.1', '1.1.1', '1.1.1.1', 'all 1', '2', 'all 2'},
                         titles_set(cloned_project.get_tasks())
                        )

        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        get_task = cloned_project.get_tasks().get
        self.assertFalse(get_task(title='1').get_parents())
        self.assertEqual(['1'],     titles_list(get_task(title='1.1').get_parents()))
        self.assertEqual(['1.1'],   titles_list(get_task(title='1.1.1').get_parents()))
        self.assertEqual(['1.1.1'], titles_list(get_task(title='1.1.1.1').get_parents()))
        self.assertEqual({'1', '1.1', '1.1.1', '1.1.1.1'},
                         titles_set(get_task(title='all 1').get_parents())
                        )
        self.assertFalse(get_task(title='2').get_parents())
        self.assertEqual({'1', '1.1', '1.1.1', '1.1.1.1', '2'},
                         titles_set(get_task(title='all 2').get_parents())
                        )

    def test_project_clone02(self):
        self.login()

        user = self.user
        project = self.create_project('Project')[0]
        contact1 = Contact.objects.create(user=user)
        contact2 = Contact.objects.create(user=user)

        task1 = self._create_parented_task('1', project)
        resource1 = self._create_resource(contact1, task1)
        resource2 = self._create_resource(contact2, task1)
        self._create_working_period(task1, resource1)
        self._create_working_period(task1, resource2)

        task2 = self._create_parented_task('2', project)
        resource3 = self._create_resource(contact1, task2)
        resource4 = self._create_resource(contact2, task2)
        self._create_working_period(task2, resource3)
        self._create_working_period(task2, resource4)

        task3 = self._create_parented_task('3', project, [task1, task2])
        self._create_parented_task('4', project, [task3])

        cloned_project = project.clone()

        for attr in ['name', 'description', 'status', 'start_date', 'end_date', 'effective_end_date']:
            self.assertEqual(getattr(project, attr), getattr(cloned_project, attr))

        get_task = cloned_project.get_tasks().get
        c_task1 = get_task(title='1')
        c_task2 = get_task(title='2')

        self.assertEqual({'1', '2', '3', '4'}, self._titles_set(cloned_project.get_tasks()))
        self.assertFalse(self._tasks_pk_set(project) & self._tasks_pk_set(cloned_project))

        self.assertEqual({'1', '2'}, self._titles_set(get_task(title='3').get_parents()))
        self.assertEqual(['3'],           self._titles_list(get_task(title='4').get_parents()))

        linked_contacts_set = lambda task: set(task.get_resources().values_list('linked_contact', flat=True))
        self.assertEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task1))
        self.assertEqual({contact1.pk, contact2.pk}, linked_contacts_set(c_task2))

        resource_set = lambda task: set(task.get_working_periods().values_list('resource', flat=True))
        self.assertEqual({resource1.pk, resource2.pk}, resource_set(c_task1))
        self.assertEqual({resource3.pk, resource4.pk}, resource_set(c_task2))

    def _delete_project_status(self, status):
        return self.client.post('/creme_config/projects/projectstatus/delete', data={'id': status.pk})

    def test_delete_project_status01(self):
        self.login()

        status = ProjectStatus.objects.create(name='Sinking')
        self.assertEqual(200, self._delete_project_status(status).status_code)
        self.assertDoesNotExist(status)

    def test_delete_project_status02(self):
        self.login()

        status = ProjectStatus.objects.create(name='Sinking')
        project = self.create_project('Project', status=status)[0]
        self.assertEqual(404, self._delete_project_status(status).status_code)
        #self.assertTrue(ProjectStatus.objects.filter(pk=status.pk).exists())
        self.get_object_or_fail(ProjectStatus, pk=status.pk)

        project = self.get_object_or_fail(Project, pk=project.pk)
        self.assertEqual(status, project.status)

    def _delete_task_status(self, status):
        return self.client.post('/creme_config/projects/taskstatus/delete', data={'id': status.pk})

    def test_delete_task_status01(self):
        self.login()

        status = TaskStatus.objects.create(name='Coming soon')
        self.assertEqual(200, self._delete_task_status(status).status_code)
        self.assertDoesNotExist(status)

    def test_delete_task_status02(self):
        self.login()

        project = self.create_project('Eva01')[0]
        status  = TaskStatus.objects.create(name='Coming soon')
        task    = self.create_task(project, 'Building head', status=status)
        self.assertEqual(404, self._delete_task_status(status).status_code)
        self.assertStillExists(status)

        self.assertStillExists(project)
        task = self.assertStillExists(task)
        self.assertEqual(status, task.tstatus)

    #TODO: test better get_project_cost(), get_effective_duration(), get_delay()
