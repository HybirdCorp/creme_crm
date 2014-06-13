# -*- coding: utf-8 -*-

try:
    from datetime import timedelta #datetime
    from functools import partial

    from django.conf import settings
    from django.core import mail
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.models import CremeEntity, Relation, CremeProperty
    from creme.creme_core.tests.base import CremeTestCase

    from creme.creme_config.models import SettingValue

    from creme.persons.constants import (REL_SUB_CUSTOMER_SUPPLIER, 
            REL_SUB_MANAGES, REL_SUB_EMPLOYED_BY)
    from creme.persons.models import Organisation, Contact

    from creme.activities.models import Activity, Status, Calendar
    from creme.activities.constants import (REL_SUB_PART_2_ACTIVITY,
            ACTIVITYTYPE_MEETING, ACTIVITYSUBTYPE_MEETING_QUALIFICATION)

    from creme.opportunities.models import Opportunity, SalesPhase

    from ..constants import DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW
    from ..management.commands.com_approaches_emails_send import Command as EmailsSendCommand
    from ..models import CommercialApproach
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('CommercialApproachTestCase',)


class CommercialApproachTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities', 'opportunities', 'commercial')

    def setUp(self):
        self.login()

    def _build_entity_field(self, entity):
        return '[{"ctype":"%s", "entity":"%s"}]' % (entity.entity_type_id, entity.id)

    def test_createview(self):
        #self.login()
        entity = CremeEntity.objects.create(user=self.user)
        url = '/commercial/approach/add/%s/' % entity.id
        self.assertGET200(url)

        title       = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post(url, data={'title':       title,
                                               'description': description,
                                              }
                                   )
        self.assertNoFormError(response)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(1, len(commapps))

        commapp = commapps[0]
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        self.assertLess((now() - commapp.creation_date).seconds, 10)
        self.assertEqual(title, unicode(commapp))

    def test_merge(self):
        #self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_commapp = partial(CommercialApproach.objects.create, description='...')
        create_commapp(title='Commapp01', creme_entity=orga01)
        create_commapp(title='Commapp02', creme_entity=orga02)
        self.assertEqual(2, CommercialApproach.objects.count())

        response = self.client.post(self.build_merge_url(orga01, orga02),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertFalse(Organisation.objects.filter(pk=orga02).exists())

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(2, len(commapps))

        for commapp in commapps:
            self.assertEqual(orga01, commapp.creme_entity)

    def test_create_from_activity01(self):
        "No subjects"
        #self.login()

        user = self.user
        url = '/activities/activity/add'
        self.assertGET200(url)

        #Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user) #me

        title = 'Meeting #01'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    '{"type": "%s", "sub_type": "%s"}' % (
                                                                    ACTIVITYTYPE_MEETING,
                                                                    ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                ),
                                          'status':           Status.objects.all()[0].pk,
                                          'start':            '2011-5-18',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'is_comapp': True,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=ACTIVITYTYPE_MEETING, title=title)
        self.assertFalse(CommercialApproach.objects.all())

    def test_create_from_activity02(self):
        #self.login()
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        #create_contact(first_name='Ryoga', last_name='Hibiki', is_user=user) #me
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        title = 'Meeting #01'
        description = 'Stuffs about the fighting'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post('/activities/activity/add', follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    '{"type": "%s", "sub_type": "%s"}' % (
                                                                    ACTIVITYTYPE_MEETING,
                                                                    ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                                                ),
                                          'description':      description,
                                          'status':           Status.objects.all()[0].pk,
                                          'start':            '2011-5-18',
                                          'my_participation': True,
                                          'my_calendar':      my_calendar.pk,

                                          'other_participants': '[%d]' % genma.id,
                                          'subjects':           self._build_entity_field(ranma),
                                          'linked_entities':    self._build_entity_field(dojo),

                                          'is_comapp': True,
                                         }
                                   )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, type=ACTIVITYTYPE_MEETING, title=title)

        comapps = CommercialApproach.objects.filter(related_activity=meeting)
        self.assertEqual(3, len(comapps))
        self.assertEqual({genma, ranma, dojo}, {comapp.creme_entity for comapp in comapps})

        now_value = now()

        for comapp in comapps:
            self.assertEqual(title,       comapp.title)
            self.assertEqual(description, comapp.description)
            self.assertAlmostEqual(now_value, comapp.creation_date, delta=timedelta(seconds=10))

    def test_sync_with_activity(self):
        #self.login()

        user = self.user
        title = 'meeting #01'
        description = 'Stuffs about the fighting'
        create_dt = self.create_datetime
        meeting = Activity.objects.create(user=user, title=title, description=description,
                                          type_id=ACTIVITYTYPE_MEETING,
                                          start=create_dt(year=2011, month=5, day=18, hour=14, minute=0),
                                          end=create_dt(year=2011,   month=6, day=1,  hour=15, minute=0),
                                         )
        #ryoga = Contact.objects.create(user=user, first_name='Ryoga', last_name='Hibiki', is_user=user)
        #contact = self.get_object_or_fail(Contact, is_user=user)
        contact = user.linked_contact

        #Relation.objects.create(subject_entity=ryoga, type_id=REL_SUB_PART_2_ACTIVITY,
        Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                object_entity=meeting, user=user
                               )

        comapp = CommercialApproach.objects.create(title=title,
                                                   description=description,
                                                   related_activity_id=meeting.id, #TODO: related_activity=instance after activities refactoring ?
                                                   #creme_entity=ryoga,
                                                   creme_entity=contact,
                                                  )

        title = title.upper()
        meeting.title = title
        meeting.save()
        self.assertEqual(title, self.refresh(comapp).title)

    def test_delete(self):
        #self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        comapp = CommercialApproach.objects.create(title='Commapp01',
                                                   description='A commercial approach',
                                                   creme_entity=orga
                                                  )

        orga.delete()
        self.assertDoesNotExist(comapp)

    def _send_mails(self):
        EmailsSendCommand().handle(verbosity=0)

    def _build_orgas(self):
        user = self.user
        mngd_orga = Organisation.get_all_managed_by_creme()[0]
        customer  = Organisation.objects.create(user=user, name='NERV')

        Relation.objects.create(user=user, subject_entity=customer,
                                type_id=REL_SUB_CUSTOMER_SUPPLIER,
                                object_entity=mngd_orga,
                               )

        return mngd_orga, customer

    def test_command01(self):
        "Customer has no CommercialApproach"
        self._send_mails()
        self.assertFalse(mail.outbox)

        mngd_orga, customer = self._build_orgas()

        self._send_mails()
        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(_(u"[CremeCRM] The organisation <%s> seems neglected") % customer,
                         message.subject
                        )
        self.assertEqual(_(u"It seems you haven't created a commercial approach "
                           u"for the organisation «%(orga)s» since %(delay)s days.") % {
                                'orga':  customer,
                                'delay': 30,
                            },
                         message.body
                        )
        self.assertEqual(settings.EMAIL_SENDER, message.from_email)
        self.assertFalse(hasattr(message, 'alternatives'))
        self.assertFalse(message.attachments)
        self.assertEqual([self.user.email],
                         [recipient for message in messages
                                    for recipient in message.recipients()
                         ]
                        )

    def test_command02(self):
        "A commapp is linked to the customer"
        mngd_orga, customer = self._build_orgas()

        CommercialApproach.objects.create(title='Commapp01',
                                          description='A commercial approach',
                                          creme_entity=customer,
                                         )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_command03(self):
        "The linked Commapp is to old"
        mngd_orga, customer = self._build_orgas()

        commapp = CommercialApproach.objects.create(title='Commapp01',
                                                    description='A commercial approach',
                                                    creme_entity=customer,
                                                   )

        CommercialApproach.objects.filter(id=commapp.id) \
                                  .update(creation_date=commapp.creation_date - timedelta(days=31))

        self._send_mails()
        self.assertEqual(1, len(mail.outbox))

    def test_command04(self):
        "A commapp is linked to a manager"
        mngd_orga, customer = self._build_orgas()

        manager = Contact.objects.create(user=self.user, first_name='Ryoga', last_name='Hibiki')
        Relation.objects.create(user=self.user, subject_entity=manager,
                                type_id=REL_SUB_MANAGES,
                                object_entity=customer,
                               )

        CommercialApproach.objects.create(title='Commapp01',
                                          description='A commercial approach',
                                          creme_entity=manager,
                                         )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_command05(self):
        "A commapp is linked to a employee"
        mngd_orga, customer = self._build_orgas()

        employee = Contact.objects.create(user=self.user, first_name='Ryoga', last_name='Hibiki')
        Relation.objects.create(user=self.user, subject_entity=employee,
                                type_id=REL_SUB_EMPLOYED_BY,
                                object_entity=customer,
                               )

        CommercialApproach.objects.create(title='Commapp01',
                                          description='A commercial approach',
                                          creme_entity=employee,
                                         )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_command06(self):
        "A commapp is linked to an Opportunity*"
        mngd_orga, customer = self._build_orgas()

        opp = Opportunity.objects.create(user=self.user, name='Opp custo',
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=mngd_orga, target=customer,
                                        )

        CommercialApproach.objects.create(title='Commapp01',
                                          description='A commercial approach',
                                          creme_entity=opp,
                                         )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_command07(self):
        "Ignore the managed orga that are customer of another managed orga"
        mngd_orga, customer = self._build_orgas()

        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME,
                                     creme_entity=customer,
                                    )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_command08(self):
        "DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW setting"
        sv = self.get_object_or_fail(SettingValue, key=DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW)
        sv.value = False
        sv.save()

        mngd_orga, customer = self._build_orgas()

        self._send_mails()
        self.assertFalse(mail.outbox)
