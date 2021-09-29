# -*- coding: utf-8 -*-

from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme import products
from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.models import (
    CremeEntity,
    Currency,
    FakeEmailCampaign,
    FieldsConfig,
    Relation,
    RelationType,
    SetCredentials,
    SettingValue,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.opportunities import constants, setting_keys
from creme.opportunities.models import Origin, SalesPhase
from creme.persons.constants import REL_SUB_PROSPECT
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .base import (
    Contact,
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
class OpportunitiesTestCase(OpportunitiesBaseTestCase):
    TARGET_KEY = 'cform_extra-opportunities_target'
    EMITTER_KEY = 'cform_extra-opportunities_emitter'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        try:
            cls.ADD_URL = reverse('opportunities__create_opportunity')
        except Exception as e:
            print(f'Error in OpportunitiesTestCase.setUpClass(): {e}')

    @staticmethod
    def _build_addrelated_url(entity, popup=False):
        return reverse(
            'opportunities__create_related_opportunity_popup' if popup else
            'opportunities__create_related_opportunity',
            args=(entity.id,)
        )

    def test_populate(self):  # test get_compatible_ones() too
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = RelationType.objects.compatible(ct).in_bulk()

        Product = products.get_product_model()
        Service = products.get_service_model()

        self.assertNotIn(constants.REL_SUB_TARGETS, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_SUB_TARGETS, [Opportunity], [Contact, Organisation],
        )

        self.assertNotIn(constants.REL_SUB_EMIT_ORGA, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation],
        )

        self.assertIn(constants.REL_OBJ_LINKED_PRODUCT, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_PRODUCT, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_PRODUCT, [Opportunity], [Product],
        )

        self.assertIn(constants.REL_OBJ_LINKED_SERVICE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_SERVICE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_SERVICE, [Opportunity], [Service],
        )

        self.assertIn(constants.REL_OBJ_LINKED_CONTACT, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_CONTACT, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_CONTACT, [Opportunity], [Contact],
        )

        self.assertIn(constants.REL_OBJ_RESPONSIBLE, relation_types)
        self.assertNotIn(constants.REL_SUB_RESPONSIBLE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_RESPONSIBLE, [Opportunity], [Contact],
        )

        self.assertTrue(SalesPhase.objects.exists())
        self.assertTrue(Origin.objects.exists())

        def assertSVEqual(key, value):
            with self.assertNoException():
                sv = SettingValue.objects.get_4_key(key)

            self.assertIs(sv.value, value)

        assertSVEqual(setting_keys.quote_key, False)
        assertSVEqual(setting_keys.target_constraint_key, True)
        assertSVEqual(setting_keys.emitter_constraint_key, True)

    @skipIfNotInstalled('creme.activities')
    def test_populate_activities(self):
        "Contribution to activities."
        get_ct = ContentType.objects.get_for_model
        opp_ct = get_ct(Opportunity)

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        self.assertTrue(rtype.subject_ctypes.filter(id=opp_ct.id).exists())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(rtype.symmetric_type.object_ctypes.filter(id=opp_ct.id).exists())

    @skipIfCustomOrganisation
    def test_createview01(self):
        user = self.login()

        url = self.ADD_URL
        self.assertGET200(url)

        target, emitter = self._create_target_n_emitter()
        name = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(
            url, follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'sales_phase':           phase.id,
                'expected_closing_date': '2010-9-20',
                'closing_date':          '2010-10-11',
                'first_action_date':     '2010-7-13',
                'currency':              DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertEqual(target, opportunity.target)

        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertEqual(emitter, opportunity.emitter)

        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        # --
        response = self.assertGET200(opportunity.get_absolute_url())
        self.assertTemplateUsed(response, 'opportunities/view_opportunity.html')

    @skipIfCustomOrganisation
    def test_createview02(self):
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        name = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(
            self.ADD_URL, follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'sales_phase':           phase.id,
                'expected_closing_date': '2010-9-20',
                'closing_date':          '2010-10-11',
                'first_action_date':     '2010-7-13',
                'currency':              DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        with self.assertNumQueries(1):
            prop_emitter = opportunity.emitter
        self.assertEqual(emitter, prop_emitter)

        with self.assertNumQueries(3):
            prop_target = opportunity.target
        self.assertEqual(target, prop_target)

    def test_createview03(self):
        "Only contact & orga models are allowed as target"
        user = self.login()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        target  = create_camp(name='Target')
        emitter = create_camp(name='Emitter')

        name = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(
            self.ADD_URL, follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'sales_phase':           phase.id,
                'expected_closing_date': '2010-9-20',
                'closing_date':          '2010-10-11',
                'first_action_date':     '2010-7-13',
                'currency':              DEFAULT_CURRENCY_PK,

                # 'target': self.formfield_value_generic_entity(target),
                # 'emitter': emitter.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertFormError(
            response, 'form', self.TARGET_KEY,
            _('This content type is not allowed.')
        )
        self.assertFormError(
            response, 'form', self.EMITTER_KEY,
            _('Select a valid choice. That choice is not one of the available choices.')
        )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    @skipIfCustomOrganisation
    def test_createview04(self):
        "LINK credentials error."
        self.login(
            is_superuser=False,
            allowed_apps=['opportunities'],
            creatable_models=[Opportunity],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not LINK
            set_type=SetCredentials.ESET_OWN
        )

        target, emitter = self._create_target_n_emitter()
        response = self.assertPOST200(
            self.ADD_URL, follow=True,
            data={
                'user':         self.user.pk,
                'name':         'My opportunity',
                'sales_phase':  SalesPhase.objects.all()[0].id,
                'closing_date': '2011-03-14',
                'currency':     DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )

        fmt1 = _('You are not allowed to link this entity: {}').format
        fmt2 = _('Entity #{id} (not viewable)').format
        self.assertFormError(
            response, 'form', self.TARGET_KEY,  fmt1(fmt2(id=target.id))
        )
        self.assertFormError(
            response, 'form', self.EMITTER_KEY, fmt1(fmt2(id=emitter.id))
        )

    @skipIfCustomOrganisation
    def test_createview05(self):
        "Emitter not managed by Creme."
        self.login()

        target, emitter = self._create_target_n_emitter(managed=False)
        response = self.assertPOST200(
            self.ADD_URL, follow=True,
            data={
                'user':         self.user.pk,
                'name':         'My opportunity',
                'sales_phase':  SalesPhase.objects.all()[0].id,
                'closing_date': '2011-03-14',

                self.TARGET_KEY:  self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertFormError(
            response, 'form', self.EMITTER_KEY,
            _('Select a valid choice. That choice is not one of the available choices.')
        )

    @skipIfCustomOrganisation
    def test_add_to_orga01(self):
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        url = self._build_addrelated_url(target)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add.html')

        context = response.context
        self.assertEqual(Opportunity.creation_label, context.get('title'))
        self.assertEqual(Opportunity.save_label,     context.get('submit_label'))

        get_initial = context['form'].initial.get
        self.assertIsInstance(get_initial('sales_phase'), SalesPhase)
        self.assertEqual(target, get_initial('target'))
        self.assertEqual(target, get_initial(self.TARGET_KEY))

        # ----
        salesphase = SalesPhase.objects.all()[0]
        name = f'Opportunity linked to {target}'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'currency':     DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         f'Opportunity Two linked to {target}',
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'currency':     DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_add_to_orga02(self):
        "Popup version."
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        url = self._build_addrelated_url(target, popup=True)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New opportunity targeting «{entity}»').format(entity=target),
            context.get('title')
        )
        self.assertEqual(Opportunity.save_label, context.get('submit_label'))

        get_initial = context['form'].initial.get
        self.assertIsInstance(get_initial('sales_phase'), SalesPhase)

        # ---
        salesphase = SalesPhase.objects.all()[0]
        name = f'Opportunity linked to {target}'
        response = self.client.post(
            url,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'currency':     DEFAULT_CURRENCY_PK,

                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_orga03(self):
        "Try to add with wrong credentials (no link credentials)."
        self.login(
            is_superuser=False,
            allowed_apps=['opportunities'],
            creatable_models=[Opportunity],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not LINK
            set_type=SetCredentials.ESET_OWN
        )

        target = Organisation.objects.create(user=self.user, name='Target renegade')
        self.assertGET403(self._build_addrelated_url(target))
        self.assertGET403(self._build_addrelated_url(target, popup=True))

    def test_add_to_orga04(self):
        "User must be allowed to created Opportunity."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'opportunities'],
            # creatable_models=[Opportunity],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL
        )

        target = Organisation.objects.create(user=user, name='Target renegade')

        url = self._build_addrelated_url(target)
        self.assertGET403(url)

        url_popup = self._build_addrelated_url(target, popup=True)
        self.assertGET403(url_popup)

        user.role.creatable_ctypes.add(ContentType.objects.get_for_model(Opportunity))
        self.assertGET200(url)
        self.assertGET200(url_popup)

    @skipIfCustomContact
    def test_add_to_contact01(self):
        "Target is a Contact."
        user = self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = self._build_addrelated_url(target)
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = f'Opportunity linked to {target}'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'currency':     DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         f'Opportunity 2 linked to {target}',
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'currency':     DEFAULT_CURRENCY_PK,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomContact
    def test_add_to_contact02(self):
        "Popup version."
        user = self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = self._build_addrelated_url(target, popup=True)
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = f'Opportunity linked to {target}'
        response = self.client.post(
            url,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  salesphase.id,
                'closing_date': '2011-03-12',
                'target':       self.formfield_value_generic_entity(target),
                'currency':     DEFAULT_CURRENCY_PK,

                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    @skipIfCustomContact
    def test_add_to_contact03(self):
        "User can not link to the Contact target"
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'opportunities'],
            creatable_models=[Opportunity],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # not LINK
            set_type=SetCredentials.ESET_OWN,
        )

        target = Contact.objects.create(
            user=self.user, first_name='Target', last_name='Renegade',
        )
        self.assertGET403(self._build_addrelated_url(target))
        self.assertGET403(self._build_addrelated_url(target, popup=True))

    def test_add_to_something01(self):
        "Target is not a Contact/Organisation."
        user = self.login()

        target = CremeEntity.objects.create(user=user)
        self.assertGET404(self._build_addrelated_url(target))
        self.assertGET404(self._build_addrelated_url(target, popup=True))

    @skipIfCustomOrganisation
    def test_editview01(self):
        user = self.login()

        name = 'opportunity01'
        opp, target, emitter = self._create_opportunity_n_organisations(name)
        url = opp.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            target_f = response.context['form'].fields[self.TARGET_KEY]

        self.assertEqual(target, target_f.initial)

        name = name.title()
        reference = '1256'
        phase = SalesPhase.objects.all()[1]
        currency = Currency.objects.create(
            name='Oolong', local_symbol='0', international_symbol='OOL',
        )
        target_rel = self.get_object_or_fail(
            Relation, subject_entity=opp.id, object_entity=target.id,
        )
        response = self.client.post(
            url, follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'reference':             reference,
                'sales_phase':           phase.id,
                'expected_closing_date': '2011-4-26',
                'closing_date':          '2011-5-15',
                'first_action_date':     '2011-5-1',
                'currency':              currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        opp = self.refresh(opp)
        self.assertEqual(name,                             opp.name)
        self.assertEqual(reference,                        opp.reference)
        self.assertEqual(phase,                            opp.sales_phase)
        self.assertEqual(currency,                         opp.currency)
        self.assertEqual(date(year=2011, month=4, day=26), opp.expected_closing_date)
        self.assertEqual(date(year=2011, month=5, day=15), opp.closing_date)
        self.assertEqual(date(year=2011, month=5, day=1),  opp.first_action_date)

        self.assertEqual(target, opp.target)
        self.assertStillExists(target_rel)
        self.assertRelationCount(1, opp, constants.REL_SUB_TARGETS, target)

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_editview02(self):
        user = self.login()

        name = 'opportunity01'
        opp, target1, emitter = self._create_opportunity_n_organisations(name)
        target2 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        target_rel = self.get_object_or_fail(
            Relation, subject_entity=opp.id, object_entity=target1.id,
        )
        response = self.client.post(
            opp.get_edit_absolute_url(), follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'reference':             '1256',
                'sales_phase':           opp.sales_phase_id,
                'expected_closing_date': '2013-4-26',
                'closing_date':          '2013-5-15',
                'first_action_date':     '2013-5-1',
                'currency':              opp.currency_id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(target2, self.refresh(opp).target)
        self.assertDoesNotExist(target_rel)
        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_listview(self):
        self.login()

        opp1 = self._create_opportunity_n_organisations('Opp1')[0]
        opp2 = self._create_opportunity_n_organisations('Opp2')[0]

        response = self.assertGET200(reverse('opportunities__list_opportunities'))

        with self.assertNoException():
            opps_page = response.context['page_obj']

        self.assertEqual(2, opps_page.paginator.count)
        self.assertSetEqual({opp1, opp2}, {*opps_page.object_list})

    @skipIfCustomOrganisation
    def test_delete01(self):
        "Cannot delete the target & the source."
        self.login()

        opp, target, emitter = self._create_opportunity_n_organisations('My Opp')
        target.trash()
        emitter.trash()

        self.assertPOST409(target.get_delete_absolute_url(), follow=True)
        self.assertStillExists(target)
        self.assertStillExists(opp)
        self.assertEqual(target, self.refresh(opp).target)

        self.assertPOST409(emitter.get_delete_absolute_url(), follow=True)
        self.assertStillExists(emitter)
        self.assertStillExists(opp)
        self.assertEqual(emitter, self.refresh(opp).emitter)

    @skipIfCustomOrganisation
    def test_delete02(self):
        "Can delete the Opportunity."
        self.login()

        opp, target, emitter = self._create_opportunity_n_organisations('My Opp')
        opp.trash()

        self.assertPOST200(opp.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(opp)
        self.assertStillExists(target)
        self.assertStillExists(emitter)

    def test_clone(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        cloned = opportunity.clone()

        self.assertEqual(opportunity.name,         cloned.name)
        self.assertEqual(opportunity.sales_phase,  cloned.sales_phase)
        self.assertEqual(opportunity.closing_date, cloned.closing_date)

        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, cloned)

        self.assertRelationCount(1, target, constants.REL_OBJ_TARGETS, opportunity)
        self.assertRelationCount(1, target, constants.REL_OBJ_TARGETS, cloned)  # <== internal

    @skipIfCustomOrganisation
    def test_get_weighted_sales01(self):
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(
            number_format('0.0', use_l10n=True),
            funf(opportunity, user).for_html()
        )

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   = 10
        self.assertEqual(
            number_format('100.0', use_l10n=True),
            funf(opportunity, user).for_html()
        )

    @skipIfCustomOrganisation
    def test_get_weighted_sales02(self):
        "With field 'estimated_sales' hidden with FieldsConfig."
        user = self.login()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        opportunity = self._create_opportunity_n_organisations()[0]

        FieldsConfig.objects.get_for_model(Opportunity)

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')

        with self.assertNumQueries(0):
            w_sales = funf(opportunity, user).for_html()

        self.assertEqual(_('Error: «Estimated sales» is hidden'), w_sales)

    def test_delete_currency(self):
        user = self.login()

        currency = Currency.objects.create(
            name='Berry', local_symbol='B', international_symbol='BRY',
        )

        create_orga = partial(Organisation.objects.create, user=user)
        Opportunity.objects.create(
            user=user, name='Opp', currency=currency,
            sales_phase=SalesPhase.objects.all()[0],
            emitter=create_orga(name='My society'),
            target=create_orga(name='Target renegade'),
        )

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'currency', currency.id),
        ))
        self.assertFormError(
            response, 'form',
            'replace_opportunities__opportunity_currency',
            _('Deletion is not possible.')
        )
