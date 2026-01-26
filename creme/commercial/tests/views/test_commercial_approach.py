from datetime import timedelta
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities.constants import UUID_SUBTYPE_MEETING_QUALIFICATION
from creme.activities.custom_forms import ACTIVITY_CREATION_CFORM
from creme.activities.models import ActivitySubType, Calendar, Status
from creme.activities.tests.base import skipIfCustomActivity
from creme.commercial.bricks import ApproachesBrick
from creme.commercial.forms.activity import IsCommercialApproachSubCell
from creme.commercial.models import CommercialApproach
from creme.commercial.setting_keys import orga_approaches_key
from creme.creme_core.forms import LAYOUT_REGULAR
from creme.creme_core.gui.custom_form import FieldGroup, FieldGroupList
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    CustomFormConfigItem,
    FakeOrganisation,
    Relation,
    SettingValue,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.opportunities.models import SalesPhase
from creme.opportunities.tests.base import skipIfCustomOpportunity
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..base import Activity, Contact, Opportunity, Organisation


class CommercialApproachViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login_as_root_and_get()

    def _get_commap_brick_node(self, response):
        tree = self.get_html_tree(response.content)
        return self.get_brick_node(tree, brick=ApproachesBrick)

    def _get_commap_titles(self, response):
        brick_node = self._get_commap_brick_node(response)

        return {elt.text for elt in brick_node.findall('.//td[@data-table-primary-column]')}

    def test_creation(self):
        entity = FakeOrganisation.objects.create(user=self.user, name='NERV')
        url = reverse('commercial__create_approach', args=(entity.id,))

        context = self.assertGET200(url).context
        self.assertEqual(
            _('New commercial approach for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the commercial approach'), context.get('submit_label'))

        title = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post(url, data={'title': title, 'description': description})
        self.assertNoFormError(response)

        commapp = self.get_alone_element(CommercialApproach.objects.all())
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        self.assertDatetimesAlmostEqual(now(), commapp.creation_date)
        self.assertEqual(title, str(commapp))

    def _add_approach_extra_cell(self):
        cfci = CustomFormConfigItem.objects.get(descriptor_id=ACTIVITY_CREATION_CFORM.id)
        old_groups = ACTIVITY_CREATION_CFORM.groups(item=cfci)
        new_groups = FieldGroupList(
            model=old_groups.model,
            cell_registry=old_groups.cell_registry,
            groups=[
                *old_groups,
                FieldGroup(
                    name='Commercial approach',
                    cells=[
                        IsCommercialApproachSubCell(model=Activity).into_cell(),
                    ],
                    layout=LAYOUT_REGULAR,
                ),
            ],
        )
        cfci.store_groups(new_groups)
        cfci.save()

    @skipIfCustomActivity
    def test_creation_from_activity__no_subject(self):
        self._add_approach_extra_cell()

        user = self.user
        url = reverse('activities__create_activity')

        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn('cform_extra-commercial_is_commercial_approach', fields)

        # ---
        title = 'Meeting #01'
        my_calendar = Calendar.objects.get_default_calendar(user)
        sub_type = self.get_object_or_fail(
            ActivitySubType, uuid=UUID_SUBTYPE_MEETING_QUALIFICATION,
        )
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':   user.id,
                'title':  title,
                'status': Status.objects.all()[0].pk,

                'cform_extra-activities_start_0': self.formfield_value_date(2011, 5, 18),

                'cform_extra-activities_subtype': sub_type.id,

                'cform_extra-activities_my_participation_0': True,
                'cform_extra-activities_my_participation_1': my_calendar.id,

                'cform_extra-commercial_is_commercial_approach': True,
            },
        )
        self.assertNoFormError(response2)
        self.get_object_or_fail(Activity, sub_type_id=sub_type.id, title=title)
        self.assertFalse(CommercialApproach.objects.all())

    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomActivity
    def test_creation_from_activity__subjects(self):
        self._add_approach_extra_cell()

        user = self.user

        create_contact = partial(Contact.objects.create, user=user)
        ranma = create_contact(first_name='Ranma', last_name='Saotome')
        genma = create_contact(first_name='Genma', last_name='Saotome')

        dojo = Organisation.objects.create(user=user, name='Dojo')

        title = 'Meeting #01'
        description = 'Stuffs about the fighting'
        my_calendar = Calendar.objects.get_default_calendar(user)
        sub_type = self.get_object_or_fail(
            ActivitySubType, uuid=UUID_SUBTYPE_MEETING_QUALIFICATION,
        )
        response = self.client.post(
            reverse('activities__create_activity'),
            follow=True,
            data={
                'user':        user.id,
                'title':       title,
                'description': description,
                'status':      Status.objects.all()[0].pk,

                'cform_extra-activities_start_0': self.formfield_value_date(2011, 5, 18),

                'cform_extra-activities_subtype': sub_type.id,

                'cform_extra-activities_my_participation_0': True,
                'cform_extra-activities_my_participation_1': my_calendar.id,

                'cform_extra-activities_others_participants':
                    self.formfield_value_multi_creator_entity(genma),
                'cform_extra-activities_subjects':
                    self.formfield_value_multi_generic_entity(ranma),
                'cform_extra-activities_linked':
                    self.formfield_value_multi_generic_entity(dojo),

                'cform_extra-commercial_is_commercial_approach': True,
            },
        )
        self.assertNoFormError(response)

        meeting = self.get_object_or_fail(Activity, sub_type=sub_type, title=title)

        comapps = CommercialApproach.objects.filter(related_activity=meeting)
        self.assertCountEqual(
            [genma, ranma, dojo],
            [comapp.creme_entity for comapp in comapps],
        )

        now_value = now()

        for comapp in comapps:
            self.assertEqual(title,       comapp.title)
            self.assertEqual(description, comapp.description)
            self.assertAlmostEqual(
                now_value, comapp.creation_date, delta=timedelta(seconds=10),
            )

    # @override_settings(BLOCK_SIZE=5)
    #  => useless, because the setting value is already read when we override this
    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomOpportunity
    def test_brick(self):
        ApproachesBrick.page_size = 5  # TODO: ugly (page_size has a brick instance attribute ?)

        sv = SettingValue.objects.get(key_id=orga_approaches_key.id)
        self.assertTrue(sv.value)

        # See populate.py
        self.assertFalse(
            BrickDetailviewLocation.objects
                                   .filter_for_model(Organisation)
                                   .filter(brick_id=ApproachesBrick.id)
        )
        BrickDetailviewLocation.objects.create(
            content_type=ContentType.objects.get_for_model(Organisation),
            brick_id=ApproachesBrick.id,
            order=10,
            zone=BrickDetailviewLocation.RIGHT,
        )

        user = self.user
        orga = Organisation.objects.create(user=user, name='NERV')
        mngd_orga = Organisation.objects.filter_managed_by_creme()[0]

        create_contact = partial(Contact.objects.create, user=user)
        manager  = create_contact(last_name='Hikari')
        employee = create_contact(last_name='Katsuragi')

        create_rel = partial(Relation.objects.create, user=user, object_entity=orga)
        create_rel(subject_entity=manager,  type_id=REL_SUB_MANAGES)
        create_rel(subject_entity=employee, type_id=REL_SUB_EMPLOYED_BY)

        opp = Opportunity.objects.create(
            user=user, name='Opp custo',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=mngd_orga, target=orga,
        )

        create_commapp = CommercialApproach.objects.create
        commapp1 = create_commapp(title='Commapp - orga',     creme_entity=orga)
        commapp2 = create_commapp(title='Commapp - manager',  creme_entity=manager)
        commapp3 = create_commapp(title='Commapp - employee', creme_entity=employee)
        commapp4 = create_commapp(title='Commapp - opp',      creme_entity=opp)

        url = orga.get_absolute_url()
        response1 = self.assertGET200(url)

        titles = self._get_commap_titles(response1)
        self.assertIn(commapp1.title, titles)
        self.assertNotIn(commapp2.title, titles)
        self.assertNotIn(commapp3.title, titles)
        self.assertNotIn(commapp4.title, titles)

        # -------
        sv.value = False
        sv.save()

        response2 = self.assertGET200(url)
        titles = self._get_commap_titles(response2)
        self.assertIn(commapp1.title, titles)
        self.assertIn(commapp2.title, titles)
        self.assertIn(commapp3.title, titles)
        self.assertIn(commapp4.title, titles)

    def test_brick__home(self):
        BrickHomeLocation.objects.create(brick_id=ApproachesBrick.id, order=100)

        response = self.assertGET200(reverse('creme_core__home'))
        self._get_commap_brick_node(response)
