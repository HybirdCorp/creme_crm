# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import RelationType, Relation, SetCredentials

    from creme.persons.models import Contact

    from .models import Event, EventType
    from .constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class EventsTestCase(CremeTestCase):
    ADD_URL = '/events/event/add'
    format_str    = '[{"rtype": "%s", "ctype": "%s", "entity": "%s"}]'
    format_str_5x = '[{"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"}]'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'events') #'persons' -> HeaderFilters

    def test_populate(self):
        rtypes_pks = [REL_SUB_IS_INVITED_TO,
                      REL_SUB_ACCEPTED_INVITATION, REL_SUB_REFUSED_INVITATION,
                      REL_SUB_CAME_EVENT, REL_SUB_NOT_CAME_EVENT
                     ]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        self.assertTrue(EventType.objects.exists())

    def _create_event(self, name, etype=None):
        etype = etype or EventType.objects.all()[0]
        self.assertNoFormError(self.client.post(self.ADD_URL, follow=True,
                                                data={'user':        self.user.pk,
                                                    'name':        name,
                                                    'type':        etype.pk,
                                                    'start_date':  '2010-11-3',
                                                    }
                                               )
                              )

        return self.get_object_or_fail(Event, name=name)

    def test_event_createview(self):
        self.login()

        self.assertGET200(self.ADD_URL)

        name  = 'Eclipse'
        etype = EventType.objects.all()[0]
        event = self._create_event(name, etype)

        self.assertEqual(1,     Event.objects.count())
        self.assertEqual(name,  event.name)
        self.assertEqual(etype, event.type)

        self.assertEqual(date(2010, 11, 3), event.start_date.date())

    def test_event_editview(self):
        self.login()

        name  = 'Eclipse'
        etype = EventType.objects.all()[0]
        event = self._create_event(name, etype)

        url = '/events/event/edit/%s' % event.id
        self.assertGET200(url)

        name += '_edited'
        self.assertNoFormError(self.client.post(url, follow=True,
                                                data={'user':        self.user.pk,
                                                    'name':        name,
                                                    'type':        etype.pk,
                                                    'start_date':  '2010-11-4',
                                                    }
                                               )
                              )

        event = self.refresh(event)
        self.assertEqual(name, event.name)
        self.assertEqual(4,    event.start_date.day)

    def test_listview(self):
        self.login()

        etype = EventType.objects.all()[0]
        event1 = self._create_event('Eclipse', etype)
        event2 = self._create_event('Show', etype)

        response = self.assertGET200('/events/events')

        with self.assertNoException():
            events_page = response.context['entities']

        self.assertEqual(2, events_page.paginator.count)
        self.assertEqual(set((event1, event2)), set(events_page.object_list))

    def test_stats01(self):
        self.login()

        event = self._create_event('Eclipse')
        stats = event.get_stats()

        self.assertEqual(4, len(stats))

        with self.assertNoException():
            stats_list = [stats['invations_count'],
                          stats['accepted_count'],
                          stats['refused_count'],
                          stats['visitors_count'],
                         ]

        self.assertEqual([0] * 4, stats_list)

    def test_stats02(self):
        self.login()

        event = self._create_event('Eclipse')
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        casca    = create_contact(first_name='Casca',    last_name='Miura')
        judo     = create_contact(first_name='Judo',     last_name='Miura')
        griffith = create_contact(first_name='Griffith', last_name='Miura')
        rickert  = create_contact(first_name='Rickert',  last_name='Miura')
        #carcus   = create_contact(first_name='Carcus',   last_name='Miura', is_deleted=True) TODO ??

        def create_relation(subject, type_id):
            Relation.objects.create(subject_entity=subject,
                                    type_id=type_id,
                                    object_entity=event,
                                    user=user
                                   )

        create_relation(casca,    REL_SUB_IS_INVITED_TO)
        create_relation(judo,     REL_SUB_IS_INVITED_TO)
        create_relation(griffith, REL_SUB_IS_INVITED_TO)
        create_relation(rickert,  REL_SUB_IS_INVITED_TO)

        create_relation(griffith, REL_SUB_ACCEPTED_INVITATION)

        create_relation(casca,    REL_SUB_REFUSED_INVITATION)
        create_relation(judo,     REL_SUB_REFUSED_INVITATION)

        create_relation(casca,    REL_SUB_CAME_EVENT)
        create_relation(judo,     REL_SUB_CAME_EVENT)
        create_relation(griffith, REL_SUB_CAME_EVENT)
        #create_relation(carcus,   REL_SUB_CAME_EVENT)

        stats = event.get_stats()
        self.assertEqual(4, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(2, stats['refused_count'])
        self.assertEqual(3, stats['visitors_count'])

    def _build_invitation_url(self, event, contact):
        return '/events/event/%s/contact/%s/set_invitation_status' % (event.id, contact.id)

    def _set_invitation_status(self, event, contact, status_id):
        self.client.post(self._build_invitation_url(event, contact),
                         data={'status': status_id}
                        )

    def test_set_invitation_status01(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        url = self._build_invitation_url(event, casca)
        self.assertPOST404(url, data={'status': 'not_an_int'})
        self.assertPOST200(url, data={'status': INV_STATUS_NO_ANSWER})

        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        self.assertPOST200(url, data={'status': INV_STATUS_NOT_INVITED})

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

    def test_set_invitation_status02(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        url = self._build_invitation_url(event, casca)
        self.assertPOST200(url, data={'status': INV_STATUS_ACCEPTED})

        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

        self.client.post(url, data={'status': INV_STATUS_NOT_INVITED})
        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status03(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, INV_STATUS_REFUSED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self._set_invitation_status(event, casca, INV_STATUS_NOT_INVITED)
        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status04(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, INV_STATUS_ACCEPTED)
        self._set_invitation_status(event, casca, INV_STATUS_REFUSED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self._set_invitation_status(event, casca, INV_STATUS_NO_ANSWER)
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status05(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self._set_invitation_status(event, casca, INV_STATUS_REFUSED)
        self._set_invitation_status(event, casca, INV_STATUS_ACCEPTED)
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status06(self): #creds errors
        self.login(is_superuser=False, allowed_apps=['persons', 'events'])

        user = self.user
        other_user = self.other_user

        create_creds = partial(SetCredentials.objects.create, role=user.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                           EntityCredentials.DELETE | EntityCredentials.LINK | \
                           EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                           EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                     set_type=SetCredentials.ESET_ALL
                    )

        create_contact = Contact.objects.create

        def _create_event(user, name):
            return Event.objects.create(user=user, name=name, start_date=datetime.now(),
                                        type=EventType.objects.all()[0],
                                       )

        event = _create_event(user=user, name='Eclipse 01')
        casca = create_contact(user=other_user, first_name='Casca', last_name='Miura')
        self.assertTrue(user.has_perm_to_link(event))
        self.assertFalse(user.has_perm_to_link(casca))
        self.assertPOST403(self._build_invitation_url(event, casca),
                           data={'status': INV_STATUS_REFUSED}
                          )

        event = _create_event(user=other_user, name='Eclipse 02')
        guts = create_contact(user=user, first_name='Guts', last_name='Miura')
        self.assertFalse(user.has_perm_to_link(event))
        self.assertTrue(user.has_perm_to_link(guts))
        self.assertPOST403(self._build_invitation_url(event, guts),
                           data={'status': INV_STATUS_REFUSED}
                          )

    def _build_presence_url(self, event, contact):
        return '/events/event/%s/contact/%s/set_presence_status' % (event.id, contact.id)

    def _set_presence_status(self, event, contact, status_id):
        return self.client.post(self._build_presence_url(event, contact),
                                data={'status': status_id}
                               )

    def test_set_presence_status01(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.assertEqual(200, self._set_presence_status(event, casca, PRES_STATUS_COME).status_code)

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(1, stats['visitors_count'])

        self._set_presence_status(event, casca, PRES_STATUS_DONT_KNOW)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, REL_SUB_NOT_CAME_EVENT, event)

    def test_set_presence_status02(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self._set_presence_status(event, casca, PRES_STATUS_COME)
        self.assertEqual(1, event.get_stats()['visitors_count'])

        self._set_presence_status(event, casca, PRES_STATUS_NOT_COME)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(1, casca, REL_SUB_NOT_CAME_EVENT, event)

        self._set_presence_status(event, casca, PRES_STATUS_DONT_KNOW)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, REL_SUB_NOT_CAME_EVENT, event)

    def test_set_presence_status03(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self._set_presence_status(event, casca, PRES_STATUS_NOT_COME)
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertRelationCount(1, casca, REL_SUB_NOT_CAME_EVENT, event)

        self._set_presence_status(event, casca, PRES_STATUS_COME)
        self.assertEqual(1, event.get_stats()['visitors_count'])
        self.assertRelationCount(0, casca, REL_SUB_NOT_CAME_EVENT, event)

    def test_set_presence_status04(self):
        "Credentials errors"
        self.login(is_superuser=False, allowed_apps=['persons', 'events'])

        user = self.user
        other_user = self.other_user

        create_creds = partial(SetCredentials.objects.create, role=user.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                           EntityCredentials.DELETE | EntityCredentials.LINK | \
                           EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                           EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                     set_type=SetCredentials.ESET_ALL
                    )

        etype = EventType.objects.all()[0]
        _create_event = Event.objects.create
        create_contact = Contact.objects.create

        event = _create_event(user=user, name='Eclipse 01', type=etype, start_date=datetime.now())
        casca = create_contact(user=other_user, first_name='Casca', last_name='Miura')
        self.assertTrue(user.has_perm_to_link(event))
        self.assertFalse(user.has_perm_to_link(casca))
        self.assertPOST403(self._build_presence_url(event, casca),
                           data={'status': PRES_STATUS_COME}
                          )

        event = _create_event(user=other_user, name='Eclipse 02', type=etype, start_date=datetime.now())
        guts = create_contact(user=user, first_name='Guts', last_name='Miura')
        self.assertFalse(user.has_perm_to_link(event))
        self.assertTrue(user.has_perm_to_link(guts))
        self.assertPOST403(self._build_presence_url(event, guts),
                           data={'status': PRES_STATUS_COME}
                          )

    def test_list_contacts(self):
        self.login()

        event = self._create_event('Eclipse')

        create_contact = partial(Contact.objects.create, user=self.user)
        casca    = create_contact(first_name='Casca',    last_name='Miura')
        judo     = create_contact(first_name='Judo',     last_name='Miura')
        griffith = create_contact(first_name='Griffith', last_name='Miura')

        self._set_presence_status(event, casca, PRES_STATUS_COME)
        self._set_invitation_status(event, judo, INV_STATUS_NO_ANSWER)
        self._set_invitation_status(event, griffith, INV_STATUS_ACCEPTED)

        response = self.assertGET200('/events/event/%s/contacts' % event.id)

        with self.assertNoException():
            contacts_page = response.context['entities']

        self.assertEqual(3, contacts_page.paginator.count)
        self.assertEqual(set((casca, judo, griffith)), set(contacts_page.object_list))

    @staticmethod
    def relations_types(contact, event):
        return list(Relation.objects
                            .filter(subject_entity=contact, object_entity=event)
                            .values_list('type_id', flat=True)
                   )

    def test_link_contacts01(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        url = '/events/event/%s/link_contacts' % event.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, follow=True,
                                    data={'related_contacts': self.format_str % (
                                                                  REL_OBJ_CAME_EVENT,
                                                                  casca.entity_type_id,
                                                                  casca.id
                                                                ),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual([REL_SUB_CAME_EVENT], self.relations_types(casca, event))

    def test_link_contacts02(self):
        self.login()

        event = self._create_event('Eclipse')

        create_contact = partial(Contact.objects.create, user=self.user)
        casca    = create_contact(first_name='Casca',    last_name='Miura')
        judo     = create_contact(first_name='Judo',     last_name='Miura')
        griffith = create_contact(first_name='Griffith', last_name='Miura')
        rickert  = create_contact(first_name='Rickert',  last_name='Miura')
        carcus   = create_contact(first_name='Carcus',   last_name='Miura')

        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {"related_contacts": self.format_str_5x % (
                                                                    REL_OBJ_IS_INVITED_TO,  ct_id, casca.id,
                                                                    REL_OBJ_CAME_EVENT,     ct_id, judo.id,
                                                                    REL_OBJ_NOT_CAME_EVENT, ct_id, griffith.id,
                                                                    REL_OBJ_IS_INVITED_TO,  ct_id, rickert.id,
                                                                    REL_OBJ_CAME_EVENT,     ct_id, carcus.id,
                                                                ),
                                          }
                                   )
        self.assertNoFormError(response)

        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(casca, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(judo, event))
        self.assertEqual([REL_SUB_NOT_CAME_EVENT], self.relations_types(griffith, event))
        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(rickert, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(carcus, event))

        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {"related_contacts": self.format_str_5x % (
                                                                    REL_OBJ_IS_INVITED_TO,  ct_id, casca.id,
                                                                    REL_OBJ_NOT_CAME_EVENT, ct_id, judo.id,
                                                                    REL_OBJ_CAME_EVENT,     ct_id, griffith.id,
                                                                    REL_OBJ_CAME_EVENT,     ct_id, rickert.id,
                                                                    REL_OBJ_CAME_EVENT,     ct_id, carcus.id,
                                                                ),
                                          }
                                   )
        self.assertNoFormError(response)

        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(casca, event))
        self.assertEqual([REL_SUB_NOT_CAME_EVENT], self.relations_types(judo, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(griffith, event))
        self.assertEqual(set([REL_SUB_IS_INVITED_TO, REL_SUB_CAME_EVENT]),
                         set(self.relations_types(rickert, event))
                        )
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(carcus, event))

    def test_link_contacts03(self):
        self.login()

        event = self._create_event('Eclipse')
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')
        ct_id = ContentType.objects.get_for_model(Contact).id

        response = self.assertPOST200('/events/event/%s/link_contacts' % event.id, follow=True,
                                      data={'related_contacts': '[{"rtype":"%s","ctype":"%s","entity":"%s"},'
                                                                ' {"rtype":"%s","ctype":"%s","entity":"%s"}]' % (
                                                                        REL_OBJ_IS_INVITED_TO, ct_id, casca.id,
                                                                        REL_OBJ_CAME_EVENT,    ct_id, casca.id,
                                                                    ),
                                           }
                                     )
        self.assertFormError(response, 'form', 'related_contacts',
                             [_(u'Contact %s is present twice.') % casca]
                            )

    def test_link_contacts04(self): #link creds error
        self.login(is_superuser=False, allowed_apps=['persons', 'events'])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | \
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        event = Event.objects.create(user=self.user, name='Eclipse',
                                     type=EventType.objects.all()[0],
                                     start_date=datetime.now(),
                                    )
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')
        url = '/events/event/%s/link_contacts' % event.id
        self.assertGET200(url)

        response = self.assertPOST200(url, follow=True,
                                      data={'related_contacts': self.format_str % (
                                                                        REL_OBJ_IS_INVITED_TO,
                                                                        casca.entity_type_id,
                                                                        casca.id,
                                                                    ),
                                           }
                                     )
        self.assertFormError(response, 'form', 'related_contacts',
                             [_(u"Some entities are not linkable: %s") % casca]
                            )

    def test_delete_type(self):
        self.login()

        etype = EventType.objects.create(name='Natural')
        event = self._create_event('Eclipse', etype)

        self.assertPOST404('/creme_config/events/event_type/delete', data={'id': etype.pk})
        self.get_object_or_fail(EventType, pk=etype.pk)

        event = self.get_object_or_fail(Event, pk=event.pk)
        self.assertEqual(etype, event.type)

    #TODO: add a test for related opportunity creation
