# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial
    from json import dumps as json_dump

    from django.conf import settings
    from django.core import mail
    from django.core.mail.backends.locmem import EmailBackend
    from django.urls import reverse
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeOrganisation
    from creme.creme_core.tests.views.base import BrickTestCaseMixin
    from creme.creme_core.models import (CremeEntity, Relation,
            BrickHomeLocation, SettingValue, Job, JobResult)
    from creme.creme_core.models.history import HistoryLine, TYPE_DELETION

    from creme.persons.constants import (REL_SUB_CUSTOMER_SUPPLIER,
            REL_SUB_MANAGES, REL_SUB_EMPLOYED_BY)
    from creme.persons.tests.base import skipIfCustomOrganisation, skipIfCustomContact

    from creme.activities.models import Status, Calendar
    from creme.activities.constants import (REL_SUB_PART_2_ACTIVITY,
            ACTIVITYTYPE_MEETING, ACTIVITYSUBTYPE_MEETING_QUALIFICATION)
    from creme.activities.tests.base import skipIfCustomActivity

    from creme.opportunities.models import SalesPhase
    from creme.opportunities.tests import skipIfCustomOpportunity

    from ..bricks import ApproachesBrick
    from ..constants import DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW
    from ..creme_jobs import com_approaches_emails_send_type
    from ..models import CommercialApproach
    from .base import Organisation, Contact, Activity, Opportunity
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CommercialApproachTestCase(CremeTestCase, BrickTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        super(CommercialApproachTestCase, cls).setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def setUp(self):
        self.login()

    def tearDown(self):
        super(CommercialApproachTestCase, self).tearDown()
        EmailBackend.send_messages = self.original_send_messages

    # def _build_entity_field(self, entity):
    #     return '[{"ctype": {"id": "%s"}, "entity":"%s"}]' % (entity.entity_type_id, entity.id)

    def _get_commap_brick_node(self, response):
        tree = self.get_html_tree(response.content)
        return self.get_brick_node(tree, ApproachesBrick.id_)

    def _get_commap_titles(self, response):
        brick_node = self._get_commap_brick_node(response)

        return {elt.text for elt in brick_node.findall('.//td[@data-table-primary-column]')}

    def test_createview(self):
        entity = CremeEntity.objects.create(user=self.user)
        url = reverse('commercial__create_approach', args=(entity.id,))
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

        self.assertDatetimesAlmostEqual(now(), commapp.creation_date)
        self.assertEqual(title, unicode(commapp))

    def test_merge(self):
        user = self.user

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='NERV')
        orga02 = create_orga(name='Nerv')

        create_commapp = partial(CommercialApproach.objects.create, description='...')
        create_commapp(title='Commapp01', creme_entity=orga01)
        create_commapp(title='Commapp02', creme_entity=orga02)
        self.assertEqual(2, CommercialApproach.objects.count())

        old_count = HistoryLine.objects.count()

        response = self.client.post(self.build_merge_url(orga01, orga02),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,

                                          'subject_to_vat_merged': orga01.subject_to_vat,
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga02)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(2, len(commapps))

        for commapp in commapps:
            self.assertEqual(orga01, commapp.creme_entity)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))  # No edition for 'entity_id'

        hline = hlines[-1]
        self.assertEqual(TYPE_DELETION, hline.type)
        self.assertEqual(unicode(orga02), hline.entity_repr)

    @skipIfCustomActivity
    def test_create_from_activity01(self):
        "No subjects"
        user = self.user
        url = reverse('activities__create_activity')

        self.assertGET200(url)

        title = 'Meeting #01'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(url, follow=True,
                                    data={'user':   user.pk,
                                          'title':  title,
                                          'status': Status.objects.all()[0].pk,
                                          'start':  '2011-5-18',

                                          'type_selector': json_dump({
                                                'type': ACTIVITYTYPE_MEETING,
                                                'sub_type': ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                          }),

                                          'my_participation_0': True,
                                          'my_participation_1': my_calendar.id,

                                          'is_comapp': True,
                                         }
                                   )
        self.assertNoFormError(response)
        self.get_object_or_fail(Activity, type=ACTIVITYTYPE_MEETING, title=title)
        self.assertFalse(CommercialApproach.objects.all())

    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomActivity
    def test_create_from_activity02(self):
        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        title = 'Meeting #01'
        description = 'Stuffs about the fighting'
        my_calendar = Calendar.get_user_default_calendar(user)
        response = self.client.post(reverse('activities__create_activity'), follow=True,
                                    data={'user':             user.pk,
                                          'title':            title,
                                          'type_selector':    json_dump({
                                                'type': ACTIVITYTYPE_MEETING,
                                                'sub_type': ACTIVITYSUBTYPE_MEETING_QUALIFICATION,
                                          }),
                                          'description':      description,
                                          'status':           Status.objects.all()[0].pk,
                                          'start':            '2011-5-18',

                                          'my_participation_0': True,
                                          'my_participation_1': my_calendar.id,

                                          'other_participants': self.formfield_value_multi_creator_entity(genma),
                                          'subjects':           self.formfield_value_multi_generic_entity(ranma),
                                          'linked_entities':    self.formfield_value_multi_generic_entity(dojo),

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

    @skipIfCustomActivity
    def test_sync_with_activity(self):
        user = self.user
        title = 'meeting #01'
        description = 'Stuffs about the fighting'
        create_dt = self.create_datetime
        meeting = Activity.objects.create(user=user, title=title, description=description,
                                          type_id=ACTIVITYTYPE_MEETING,
                                          start=create_dt(year=2011, month=5, day=18, hour=14, minute=0),
                                          end=create_dt(year=2011,   month=6, day=1,  hour=15, minute=0),
                                         )
        contact = user.linked_contact

        Relation.objects.create(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
                                object_entity=meeting, user=user
                               )

        comapp = CommercialApproach.objects.create(title=title,
                                                   description=description,
                                                   related_activity_id=meeting.id,  # TODO: related_activity=instance after activities refactoring ?
                                                   creme_entity=contact,
                                                  )

        title = title.upper()
        meeting.title = title
        meeting.save()
        self.assertEqual(title, self.refresh(comapp).title)

    def test_delete(self):
        orga = FakeOrganisation.objects.create(user=self.user, name='NERV')
        comapp = CommercialApproach.objects.create(title='Commapp01',
                                                   description='A commercial approach',
                                                   creme_entity=orga,
                                                  )

        orga.delete()
        self.assertDoesNotExist(comapp)

    # @override_settings(BLOCK_SIZE=5) useless, because the setting value is already read when we override this
    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_brick01(self):
        ApproachesBrick.page_size = 5  # TODO: ugly (page_size has a brick instance attribute ?)

        sv = SettingValue.objects.get(key_id=DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW)
        self.assertTrue(sv.value)

        user = self.user
        orga = Organisation.objects.create(user=user, name='NERV')
        mngd_orga = Organisation.get_all_managed_by_creme()[0]

        create_contact = partial(Contact.objects.create, user=user)
        manager  = create_contact(last_name='Hikari')
        employee = create_contact(last_name='Katsuragi')

        create_rel     = partial(Relation.objects.create, user=user, object_entity=orga)
        create_rel(subject_entity=manager,  type_id=REL_SUB_MANAGES)
        create_rel(subject_entity=employee, type_id=REL_SUB_EMPLOYED_BY)

        opp = Opportunity.objects.create(user=user, name='Opp custo',
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=mngd_orga, target=orga,
                                        )

        create_commapp = CommercialApproach.objects.create
        commapp1 = create_commapp(title='Commapp - orga',     creme_entity=orga)
        commapp2 = create_commapp(title='Commapp - manager',  creme_entity=manager)
        commapp3 = create_commapp(title='Commapp - employee', creme_entity=employee)
        commapp4 = create_commapp(title='Commapp - opp',      creme_entity=opp)

        url = orga.get_absolute_url()
        response = self.assertGET200(url)

        titles = self._get_commap_titles(response)
        self.assertIn(commapp1.title, titles)
        self.assertNotIn(commapp2.title, titles)
        self.assertNotIn(commapp3.title, titles)
        self.assertNotIn(commapp4.title, titles)

        # -------
        sv.value = False
        sv.save()

        response = self.assertGET200(url)
        titles = self._get_commap_titles(response)
        self.assertIn(commapp1.title, titles)
        self.assertIn(commapp2.title, titles)
        self.assertIn(commapp3.title, titles)
        self.assertIn(commapp4.title, titles)

    def test_brick02(self):
        "Home"
        # BlockPortalLocation.create_or_update(app_name='creme_core', brick_id=ApproachesBrick.id_, order=100)
        BrickHomeLocation.objects.create(brick_id=ApproachesBrick.id_, order=100)

        response = self.assertGET200('/')
        self._get_commap_brick_node(response)

    # def test_brick03(self):
    #     "Commercial portal"
    #     BlockPortalLocation.create_or_update(app_name='commercial', brick_id=ApproachesBrick.id_, order=100)
    #
    #     response = self.assertGET200(reverse('commercial__portal'))
    #     self._get_commap_brick_node(response)

    def _send_mails(self):
        job = self.get_object_or_fail(Job, type_id=com_approaches_emails_send_type.id)
        self.assertIsNone(job.user)

        com_approaches_emails_send_type.execute(job)

        return job

    def _build_orgas(self):
        user = self.user
        mngd_orga = Organisation.get_all_managed_by_creme()[0]
        customer  = Organisation.objects.create(user=user, name='NERV')

        Relation.objects.create(user=user, subject_entity=customer,
                                type_id=REL_SUB_CUSTOMER_SUPPLIER,
                                object_entity=mngd_orga,
                               )

        return mngd_orga, customer

    @skipIfCustomOrganisation
    def test_job01(self):
        "Customer has no CommercialApproach"
        self._send_mails()
        self.assertFalse(mail.outbox)

        mngd_orga, customer = self._build_orgas()

        self._send_mails()
        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual(_(u"[CremeCRM] The organisation «{}» seems neglected").format(customer),
                         message.subject
                        )
        self.assertEqual(_(u"It seems you haven't created a commercial approach "
                           u"for the organisation «{orga}» since {delay} days.").format(
                                orga=customer,
                                delay=30,
                            ),
                         message.body
                        )
        self.assertEqual(settings.EMAIL_SENDER, message.from_email)
        self.assertFalse(hasattr(message, 'alternatives'))
        self.assertFalse(message.attachments)
        self.assertEqual([self.user.email],
                         [recipient for msg in messages for recipient in msg.recipients()]
                        )

    @skipIfCustomOrganisation
    def test_job02(self):
        "A commapp is linked to the customer"
        mngd_orga, customer = self._build_orgas()

        CommercialApproach.objects.create(title='Commapp01',
                                          description='A commercial approach',
                                          creme_entity=customer,
                                         )

        self._send_mails()
        self.assertFalse(mail.outbox)

    @skipIfCustomOrganisation
    def test_job03(self):
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

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_job04(self):
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

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_job05(self):
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

    @skipIfCustomOrganisation
    @skipIfCustomOpportunity
    def test_job06(self):
        "A commapp is linked to an Opportunity"
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

    @skipIfCustomOrganisation
    def test_job07(self):
        "Ignore the managed orga that are customer of another managed organisation"
        mngd_orga, customer = self._build_orgas()

        customer.is_managed = True
        customer.save()

        self._send_mails()
        self.assertFalse(mail.outbox)

    @skipIfCustomOrganisation
    def test_job08(self):
        "Sending error"
        self._build_orgas()

        self.send_messages_called = False
        err_msg = 'Sent error'

        def send_messages(this, messages):
            self.send_messages_called = True
            raise Exception(err_msg)

        EmailBackend.send_messages = send_messages

        job = self._send_mails()
        self.assertFalse(mail.outbox)

        jresults = JobResult.objects.filter(job=job)
        self.assertEqual(1, len(jresults))

        jresult = jresults[0]
        self.assertEqual([_(u'An error has occurred while sending emails'),
                          _(u'Original error: {}').format(err_msg),
                         ],
                         jresult.messages
                        )
