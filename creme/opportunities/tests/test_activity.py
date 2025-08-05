from datetime import timedelta
from functools import partial
from uuid import uuid4

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities import constants as act_constants
from creme.activities import get_activity_model
from creme.activities import setting_keys as act_skeys
from creme.activities.models import ActivitySubType, Calendar, Status
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.models import (
    ButtonMenuItem,
    Relation,
    RelationType,
    SettingValue,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views import base as view_base
from creme.persons.tests.base import skipIfCustomContact

from .. import buttons
from ..bricks import LinkedContactsBrick
from ..constants import REL_SUB_LINKED_CONTACT
from ..setting_keys import unsuccessful_key
from .base import (
    Contact,
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)

Activity = get_activity_model()


@skipIfNotInstalled('creme.activities')
@skipIfCustomOpportunity
@skipIfCustomActivity
@skipIfCustomContact
class UnsuccessfulPhoneCallTestCase(view_base.BrickTestCaseMixin,
                                    view_base.ButtonTestCaseMixin,
                                    OpportunitiesBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.get_root_user()
        create_contact = partial(Contact.objects.create, user=user)
        cls.contact1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        cls.contact2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        cls.opp, cls.target, cls.emitter = cls._create_opportunity_n_organisations(
            user=user, name='My Opp',
        )
        create_rel = partial(
            Relation.objects.create,
            user=user,
            type=RelationType.objects.get(id=REL_SUB_LINKED_CONTACT),
            object_entity=cls.opp,
        )
        create_rel(subject_entity=cls.contact1)
        create_rel(subject_entity=cls.contact2)

    def _build_add_url(self, opportunity):
        return reverse('opportunities__create_unsuccessful_phone_call', args=(opportunity.id,))

    def test_creation__default(self):
        user = self.login_as_root_and_get()
        activities_count = Activity.objects.count()

        opp = self.opp
        deleted = Contact.objects.create(
            user=user,
            first_name='Seijuro', last_name='Yoshioka',
            is_deleted=True,
        )
        Relation.objects.create(
            user=user,
            subject_entity=deleted, type_id=REL_SUB_LINKED_CONTACT, object_entity=opp,
        )

        add_url = self._build_add_url(opp)
        self.assertGET405(add_url)

        # ---
        self.assertPOST200(add_url)
        self.assertEqual(activities_count + 1, Activity.objects.count())

        sub_type = ActivitySubType.objects.get(uuid=act_constants.UUID_SUBTYPE_PHONECALL_OUTGOING)
        activity = self.get_object_or_fail(
            Activity, type=sub_type.type, sub_type=sub_type, title=_('Unsuccessful call'),
        )
        self.assertEqual(
            self.get_object_or_fail(Status, uuid=act_constants.UUID_STATUS_UNSUCCESSFUL),
            activity.status,
        )
        # self.assertEqual(act_constants.NARROW, activity.floating_type)
        self.assertEqual(Activity.FloatingType.NARROW, activity.floating_type)

        end = activity.end
        self.assertDatetimesAlmostEqual(end, now())
        self.assertEqual(end - timedelta(minutes=3), activity.start)

        self.assertHaveRelation(
            subject=opp, type=act_constants.REL_SUB_ACTIVITY_SUBJECT, object=activity,
        )

        PART_2_ACTIVITY = act_constants.REL_SUB_PART_2_ACTIVITY
        self.assertHaveRelation(subject=user.linked_contact, type=PART_2_ACTIVITY, object=activity)
        self.assertHaveRelation(subject=self.contact1,       type=PART_2_ACTIVITY, object=activity)
        self.assertHaveRelation(subject=self.contact2,       type=PART_2_ACTIVITY, object=activity)
        self.assertHaveNoRelation(subject=deleted, type=PART_2_ACTIVITY, object=activity)

        self.assertListEqual(
            [Calendar.objects.get_default_calendar(user)],
            [*activity.calendars.all()],
        )

    def test_creation__custom(self):
        "Custom values stored in SettingValues."
        user = self.login_as_standard(
            allowed_apps=['persons', 'activities', 'opportunities'],
            creatable_models=[Activity],
        )
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        sub_type = ActivitySubType.objects.get(
            uuid=act_constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
        )
        SettingValue.objects.set_4_key(
            key=act_skeys.unsuccessful_subtype_key, value=str(sub_type.uuid),
        )

        title = 'Damn it'
        SettingValue.objects.set_4_key(key=act_skeys.unsuccessful_title_key, value=title)

        status = self.get_object_or_fail(Status, uuid=act_constants.UUID_STATUS_DELAYED)
        SettingValue.objects.set_4_key(
            key=act_skeys.unsuccessful_status_key, value=str(status.uuid),
        )

        duration = 2
        SettingValue.objects.set_4_key(
            key=act_skeys.unsuccessful_duration_key, value=duration,
        )

        self.assertPOST200(self._build_add_url(self.opp))

        activity = self.get_object_or_fail(
            Activity, type=sub_type.type, sub_type=sub_type, title=title,
        )
        self.assertEqual(status, activity.status)

        end = activity.end
        self.assertDatetimesAlmostEqual(end, now())
        self.assertEqual(end - timedelta(minutes=duration), activity.start)

    def test_creation__relation_duplicate(self):
        user = self.login_as_root_and_get()
        opp = self.opp
        user_contact = user.linked_contact

        Relation.objects.create(
            user=user,
            subject_entity=user_contact,
            type=RelationType.objects.get(id=REL_SUB_LINKED_CONTACT),
            object_entity=opp,
        )

        self.assertPOST200(self._build_add_url(opp), follow=True)

        activity = self.get_object_or_fail(Activity, title=_('Unsuccessful call'))
        self.assertHaveRelation(
            subject=opp, type=act_constants.REL_SUB_ACTIVITY_SUBJECT, object=activity,
        )

        SUB_PART_2_ACTIVITY = act_constants.REL_SUB_PART_2_ACTIVITY
        self.assertHaveRelation(subject=user_contact,  type=SUB_PART_2_ACTIVITY, object=activity)
        self.assertHaveRelation(subject=self.contact1, type=SUB_PART_2_ACTIVITY, object=activity)
        self.assertHaveRelation(subject=self.contact2, type=SUB_PART_2_ACTIVITY, object=activity)

    def test_creation__type_error(self):
        self.login_as_root()

        sub_type_uuid = uuid4()
        self.assertFalse(ActivitySubType.objects.filter(uuid=sub_type_uuid))
        SettingValue.objects.set_4_key(
            key=act_skeys.unsuccessful_subtype_key, value=str(sub_type_uuid),
        )

        response = self.client.post(self._build_add_url(self.opp))
        self.assertContains(
            response,
            _(
                'The configuration of the button is broken; '
                'fix it in the configuration of «Activities».'
            ),
            status_code=409,
            html=True,
        )

    def test_creation__status_error(self):
        self.login_as_root()

        status_uuid = uuid4()
        self.assertFalse(Status.objects.filter(uuid=status_uuid))
        SettingValue.objects.set_4_key(
            key=act_skeys.unsuccessful_status_key, value=str(status_uuid),
        )

        response = self.client.post(self._build_add_url(self.opp))
        self.assertContains(
            response,
            _(
                'The configuration of the button is broken; '
                'fix it in the configuration of «Activities».'
            ),
            status_code=409,
            html=True,
        )

    def test_creation__long_title(self):
        self.login_as_root()

        self.assertEqual(100, Activity._meta.get_field('title').max_length)

        title = (
            'A very very very very very long title which will cause an '
            'integrity error if it is not truncated by the view'
        )
        self.assertGreater(len(title), 100)
        SettingValue.objects.set_4_key(key=act_skeys.unsuccessful_title_key, value=title)

        self.assertPOST200(self._build_add_url(self.opp))

        activity = Activity.objects.order_by('-id').first()
        self.assertIsNotNone(activity)
        self.assertEqual(
            'A very very very very very long title which will cause an '
            'integrity error if it is not truncated by…',
            activity.title,
        )

    def test_creation__app_perm(self):
        # Not 'opportunities'
        user = self.login_as_standard(allowed_apps=['persons', 'activities'])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])
        self.assertPOST403(self._build_add_url(self.opp))

    def test_creation__creation_perm(self):
        user = self.login_as_standard(allowed_apps=['persons', 'activities', 'opportunities'])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])
        self.assertPOST403(self._build_add_url(self.opp))

    def test_creation__link_perm(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'activities', 'opportunities'],
            creatable_models=[Activity],
        )
        self.add_credentials(user.role, all='!LINK')
        self.assertPOST403(self._build_add_url(self.opp))

    def test_creation__bad_ctype(self):
        user = self.login_as_root_and_get()
        self.assertPOST404(self._build_add_url(
            Organisation.objects.create(user=user, name='Miyamoto')
        ))

    def test_creation__no_linked_contact(self):
        user = self.login_as_root_and_get()
        opp1 = self.opp
        opp2 = Opportunity.objects.create(
            user=user, name='Opp #2',
            sales_phase=opp1.sales_phase,
            emitter=self.emitter, target=self.target,
        )
        url = self._build_add_url(opp2)
        self.assertPOST409(url)

        # ---
        # Should be ignored
        Relation.objects.create(
            user=user,
            subject_entity=user.linked_contact,
            type_id=REL_SUB_LINKED_CONTACT,
            object_entity=opp2,
        )
        self.assertPOST409(url)

    def test_creation__narrowed(self):
        user = self.login_as_root_and_get()
        opp = self.opp
        user_contact = user.linked_contact

        self.assertPOST200(
            self._build_add_url(opp),
            follow=True, data={'participant': [self.contact1.id]},
        )

        activity = self.get_object_or_fail(Activity, title=_('Unsuccessful call'))
        self.assertHaveRelation(
            subject=opp, type=act_constants.REL_SUB_ACTIVITY_SUBJECT, object=activity,
        )

        SUB_PART_2_ACTIVITY = act_constants.REL_SUB_PART_2_ACTIVITY
        self.assertHaveRelation(subject=user_contact,  type=SUB_PART_2_ACTIVITY, object=activity)
        self.assertHaveRelation(subject=self.contact1, type=SUB_PART_2_ACTIVITY, object=activity)
        self.assertHaveNoRelation(subject=self.contact2, type=SUB_PART_2_ACTIVITY, object=activity)

    def test_creation__narrowed__invalid_participants(self):
        self.login_as_root()
        self.assertPOST409(
            self._build_add_url(self.opp),
            follow=True, data={'participant': [self.UNUSED_PK]},
        )

    def test_creation__narrowed__invalid_participant_ids(self):
        self.login_as_root()
        self.assertPOST409(
            self._build_add_url(self.opp),
            follow=True, data={'participant': ['not_int']},
        )

    def test_creation__narrowed__deleted_participants(self):
        user = self.login_as_root_and_get()

        deleted = Contact.objects.create(
            user=user,
            first_name='Seijuro', last_name='Yoshioka',
            is_deleted=True,
        )
        Relation.objects.create(
            user=user,
            subject_entity=deleted,
            type_id=REL_SUB_LINKED_CONTACT,
            object_entity=self.opp,
        )
        self.assertPOST409(
            self._build_add_url(self.opp),
            follow=True, data={'participant': [deleted.id]},
        )

    def test_creation__narrowed__unrelated_participants(self):
        self.login_as_root()
        unrelated = Contact.objects.create(
            user=self.contact1.user,
            first_name='Seijuro', last_name='Yoshioka',
        )
        self.assertPOST409(
            self._build_add_url(self.opp),
            follow=True, data={'participant': [unrelated.id]},
        )

    def test_creation__narrowed__participant_is_self(self):
        user = self.login_as_root_and_get()
        user_contact = user.linked_contact
        Relation.objects.create(
            user=user,
            subject_entity=user_contact,
            type_id=REL_SUB_LINKED_CONTACT,
            object_entity=self.opp,
        )
        self.assertPOST409(
            self._build_add_url(self.opp),
            follow=True, data={'participant': [user_contact.id]},
        )

    def test_button(self):
        self.login_as_root()
        ButtonMenuItem.objects.create(
            content_type=Opportunity, order=1,
            button=buttons.AddUnsuccessfulPhoneCallButton,
        )

        opp = self.opp
        add_url = self._build_add_url(self.opp)
        response = self.assertGET200(opp.get_absolute_url())
        self.assertTrue(
            [*self.iter_button_nodes(
                self.get_instance_buttons_node(self.get_html_tree(response.content)),
                tags=['a'], href=add_url,
            )],
            msg='<Add call> button not found!',
        )

    def test_brick_action__enabled(self):
        self.login_as_root()
        SettingValue.objects.set_4_key(key=unsuccessful_key, value=True)

        opp = self.opp
        response = self.assertGET200(opp.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=LinkedContactsBrick,
        )
        self.assertInstanceLink(brick_node=brick_node, entity=self.contact1)

        add_url = self._build_add_url(self.opp)
        # TODO: better test (display on N lines...)
        self.assertBrickHasAction(brick_node=brick_node, url=add_url, action_type='update')

    def test_brick_action__disabled(self):
        self.login_as_root()
        self.assertSettingValueEqual(key=unsuccessful_key, value=False)

        opp = self.opp
        response = self.assertGET200(opp.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=LinkedContactsBrick,
        )
        self.assertInstanceLink(brick_node=brick_node, entity=self.contact1)
        self.assertBrickHasNoAction(brick_node=brick_node, url=self._build_add_url(self.opp))
