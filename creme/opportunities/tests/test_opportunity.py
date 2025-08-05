from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme import products
from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeEntity,
    Currency,
    FakeEmailCampaign,
    FieldsConfig,
    Relation,
    RelationType,
    SettingValue,
    Workflow,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.opportunities import constants, setting_keys
from creme.opportunities.models import Origin, SalesPhase
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER, REL_SUB_PROSPECT
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

        wf1 = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_TARGET_ORGA_BECOMES_PROSPECT,
        )
        self.assertEqual(_('The target Organisation becomes a prospect'), wf1.title)
        self.assertEqual(wf1.content_type.model_class(), Opportunity)
        self.assertFalse(wf1.is_custom)

        wf2 = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_TARGET_CONTACT_BECOMES_PROSPECT,
        )
        self.assertEqual(_('The target Contact becomes a prospect'), wf2.title)
        self.assertEqual(wf2.content_type.model_class(), Opportunity)
        self.assertFalse(wf2.is_custom)

    @skipIfNotInstalled('creme.activities')
    def test_populate_activities(self):
        "Contribution to activities."
        get_ct = ContentType.objects.get_for_model
        opp_ct = get_ct(Opportunity)

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        self.assertTrue(rtype.subject_ctypes.filter(id=opp_ct.id).exists())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(rtype.symmetric_type.object_ctypes.filter(id=opp_ct.id).exists())

    def test_sales_phase(self):
        user = self.create_user()
        phase = SalesPhase.objects.create(name='OK', color='00FF00')
        ctxt = {
            'user': user,
            'opportunity': Opportunity(user=user, name='Opp', sales_phase=phase),
        }
        template = Template(
            r'{% load creme_core_tags %}'
            r'{% print_field object=opportunity field="sales_phase" tag=tag %}'
        )
        self.assertEqual(
            phase.name,
            template.render(Context({**ctxt, 'tag': ViewTag.TEXT_PLAIN})).strip(),
        )
        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{phase.color};" />'
            f' <span>{phase.name}</span>'
            f'</div>',
            template.render(Context({**ctxt, 'tag': ViewTag.HTML_DETAIL})),
        )

    @skipIfCustomOrganisation
    def test_related_properties(self):
        user = self.login_as_root_and_get()
        target, emitter = self._create_target_n_emitter(user=user)

        opportunity = self.refresh(Opportunity.objects.create(
            user=user, name='My Opp',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=emitter,
            target=target,
        ))

        self.assertHaveRelation(target,  type=constants.REL_OBJ_TARGETS,   object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)

        with self.assertNumQueries(2):
            prop_emitter1 = opportunity.emitter
        self.assertEqual(emitter, prop_emitter1)

        with self.assertNumQueries(2):
            prop_target1 = opportunity.target
        self.assertEqual(target, prop_target1)

        # ---
        opportunity = self.refresh(opportunity)
        opportunity.populate_relations(
            entities=[opportunity],
            relation_type_ids=[constants.REL_OBJ_EMIT_ORGA, constants.REL_SUB_TARGETS],
        )

        ContentType.objects.get_for_model(CremeEntity)  # Fill cache
        with self.assertNumQueries(0):
            prop_emitter2 = opportunity.emitter
        self.assertEqual(emitter, prop_emitter2)

        with self.assertNumQueries(0):
            prop_target2 = opportunity.target
        self.assertEqual(target, prop_target2)

    @skipIfCustomOrganisation
    def test_createview01(self):
        user = self.login_as_root_and_get()
        target, emitter = self._create_target_n_emitter(user=user)

        url = self.ADD_URL
        self.assertGET200(url)

        # ---
        name = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'sales_phase':           phase.id,
                'expected_closing_date': self.formfield_value_date(2010, 9, 20),
                'closing_date':          self.formfield_value_date(2010, 10, 11),
                'first_action_date':     self.formfield_value_date(2010, 7, 13),
                'currency':              currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        ))

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertHaveRelation(target, type=constants.REL_OBJ_TARGETS, object=opportunity)
        self.assertEqual(target, opportunity.target)

        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertEqual(emitter, opportunity.emitter)

        self.assertHaveRelation(target, type=REL_SUB_PROSPECT, object=emitter)

        # --
        response = self.assertGET200(opportunity.get_absolute_url())
        self.assertTemplateUsed(response, 'opportunities/view_opportunity.html')

    def test_createview__invalid_related(self):
        "Only contact & orga models are allowed as target."
        user = self.login_as_root_and_get()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        target  = create_camp(name='Target')
        emitter = create_camp(name='Emitter')

        name = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        response = self.assertPOST200(
            self.ADD_URL,
            follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'sales_phase':           phase.id,
                'expected_closing_date': self.formfield_value_date(2010, 9, 20),
                'closing_date':          self.formfield_value_date(2010, 10, 11),
                'first_action_date':     self.formfield_value_date(2010, 7, 13),
                'currency':              currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )

        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field=self.TARGET_KEY,
            errors=_('This content type is not allowed.'),
        )
        self.assertFormError(
            form,
            field=self.EMITTER_KEY,
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    @skipIfCustomOrganisation
    def test_createview__link_perms(self):
        "LINK credentials error."
        user = self.login_as_standard(
            allowed_apps=['opportunities'],
            creatable_models=[Opportunity],
        )
        self.add_credentials(user.role, own='!LINK')

        target, emitter = self._create_target_n_emitter(user=user)
        response = self.assertPOST200(
            self.ADD_URL,
            follow=True,
            data={
                'user':         user.pk,
                'name':         'My opportunity',
                'sales_phase':  SalesPhase.objects.first().id,
                'closing_date': self.formfield_value_date(2011, 3, 14),
                'currency':     Currency.objects.first().id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )

        form = self.get_form_or_fail(response)
        fmt1 = _('You are not allowed to link this entity: {}').format
        fmt2 = _('Entity #{id} (not viewable)').format
        self.assertFormError(
            form, field=self.TARGET_KEY,  errors=fmt1(fmt2(id=target.id)),
        )
        self.assertFormError(
            form, field=self.EMITTER_KEY, errors=fmt1(fmt2(id=emitter.id)),
        )

    @skipIfCustomOrganisation
    def test_createview__not_managed_emitter(self):
        "Emitter not managed by Creme."
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user, managed=False)
        response = self.assertPOST200(
            self.ADD_URL, follow=True,
            data={
                'user':         user.pk,
                'name':         'My opportunity',
                'sales_phase':  SalesPhase.objects.all()[0].id,
                'closing_date': self.formfield_value_date(2011, 3, 14),

                self.TARGET_KEY:  self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=self.EMITTER_KEY,
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

    @skipIfCustomOrganisation
    def test_add_to_orga(self):
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user)
        url = self._build_addrelated_url(target)

        # GET --
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add.html')

        context1 = response1.context
        self.assertEqual(Opportunity.creation_label, context1.get('title'))
        self.assertEqual(Opportunity.save_label,     context1.get('submit_label'))

        get_initial = context1['form'].initial.get
        self.assertIsInstance(get_initial('sales_phase'), SalesPhase)
        self.assertEqual(target, get_initial('target'))
        self.assertEqual(target, get_initial(self.TARGET_KEY))

        # POST ---
        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        name = f'Opportunity linked to {target}'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'currency':     currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        ))

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase, opportunity.sales_phase)

        self.assertHaveRelation(target,  type=constants.REL_OBJ_TARGETS,   object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertHaveRelation(target,  type=REL_SUB_PROSPECT,            object=emitter)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         f'Opportunity Two linked to {target}',
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'currency':     currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        ))
        self.assertHaveRelation(subject=target, type=REL_SUB_PROSPECT, object=emitter)

    @skipIfCustomOrganisation
    def test_add_to_orga__popup(self):
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user)
        url = self._build_addrelated_url(target, popup=True)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(
            _('New opportunity targeting «{entity}»').format(entity=target),
            context.get('title'),
        )
        self.assertEqual(Opportunity.save_label, context.get('submit_label'))

        get_initial = context['form'].initial.get
        self.assertIsInstance(get_initial('sales_phase'), SalesPhase)

        # POST ---
        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        name = f'Opportunity linked to {target}'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'currency':     currency.id,

                self.EMITTER_KEY: emitter.id,
            },
        ))

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase, opportunity.sales_phase)

        self.assertHaveRelation(target,  type=constants.REL_OBJ_TARGETS,   object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertHaveRelation(target,  type=REL_SUB_PROSPECT,            object=emitter)

    def test_add_to_orga__link_perms(self):
        "Try to add with wrong credentials (no link credentials)."
        user = self.login_as_standard(
            allowed_apps=['opportunities'],
            creatable_models=[Opportunity],
        )
        self.add_credentials(user.role, own='!LINK')

        target = Organisation.objects.create(user=user, name='Target renegade')
        self.assertGET403(self._build_addrelated_url(target))
        self.assertGET403(self._build_addrelated_url(target, popup=True))

    def test_add_to_orga__creation_perms(self):
        "User must be allowed to created Opportunity."
        user = self.login_as_standard(
            allowed_apps=['persons', 'opportunities'],
            # creatable_models=[Opportunity],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        target = Organisation.objects.create(user=user, name='Target renegade')

        url = self._build_addrelated_url(target)
        self.assertGET403(url)

        url_popup = self._build_addrelated_url(target, popup=True)
        self.assertGET403(url_popup)

        user.role.creatable_ctypes.add(ContentType.objects.get_for_model(Opportunity))
        self.assertGET200(url)
        self.assertGET200(url_popup)

    @skipIfCustomContact
    def test_add_to_contact(self):
        "Target is a Contact."
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user, contact=True)
        url = self._build_addrelated_url(target)
        self.assertGET200(url)

        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        name = f'Opportunity linked to {target}'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'currency':     currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        ))

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase, opportunity.sales_phase)

        self.assertHaveRelation(target,  type=constants.REL_OBJ_TARGETS,   object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertHaveRelation(target,  type=REL_SUB_PROSPECT,            object=emitter)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         f'Opportunity 2 linked to {target}',
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'currency':     currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
                self.EMITTER_KEY: emitter.id,
            },
        ))
        self.assertHaveRelation(subject=target, type=REL_SUB_PROSPECT, object=emitter)

    @skipIfCustomContact
    def test_add_to_contact__popup(self):
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user, contact=True)
        url = self._build_addrelated_url(target, popup=True)
        self.assertGET200(url)

        phase = SalesPhase.objects.all()[0]
        currency = Currency.objects.all()[0]
        name = f'Opportunity linked to {target}'
        response = self.client.post(
            url,
            data={
                'user':         user.pk,
                'name':         name,
                'sales_phase':  phase.id,
                'closing_date': self.formfield_value_date(2011, 3, 12),
                'target':       self.formfield_value_generic_entity(target),
                'currency':     currency.id,

                self.EMITTER_KEY: emitter.id,
            },
        )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase, opportunity.sales_phase)

        self.assertHaveRelation(target,  type=constants.REL_OBJ_TARGETS,   object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertHaveRelation(target,  type=REL_SUB_PROSPECT,            object=emitter)

    @skipIfCustomContact
    def test_add_to_contact__link_perms(self):
        "User can not link to the Contact target."
        user = self.login_as_standard(
            allowed_apps=['persons', 'opportunities'],
            creatable_models=[Opportunity],
        )
        self.add_credentials(user.role, own='!LINK')

        target = Contact.objects.create(
            user=user, first_name='Target', last_name='Renegade',
        )
        self.assertGET403(self._build_addrelated_url(target))
        self.assertGET403(self._build_addrelated_url(target, popup=True))

    def test_add_to_something(self):
        "Target is not a Contact/Organisation."
        user = self.login_as_root_and_get()

        target = CremeEntity.objects.create(user=user)
        self.assertGET404(self._build_addrelated_url(target))
        self.assertGET404(self._build_addrelated_url(target, popup=True))

    @skipIfCustomOrganisation
    def test_editview(self):
        user = self.login_as_root_and_get()

        name = 'opportunity01'
        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name=name)
        url = opp.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            target_f = response1.context['form'].fields[self.TARGET_KEY]

        self.assertEqual(target, target_f.initial)

        # ---
        name = name.title()
        reference = '1256'
        phase = SalesPhase.objects.all()[1]
        currency = Currency.objects.create(
            name='Oolong', local_symbol='0', international_symbol='OOL',
        )
        target_rel = self.get_object_or_fail(
            Relation, subject_entity=opp.id, object_entity=target.id,
        )
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'reference':             reference,
                'sales_phase':           phase.id,
                'expected_closing_date': self.formfield_value_date(2011, 4, 26),
                'closing_date':          self.formfield_value_date(2011, 5, 15),
                'first_action_date':     self.formfield_value_date(2011, 5, 1),
                'currency':              currency.id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        ))

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
        self.assertHaveRelation(subject=opp, type=constants.REL_SUB_TARGETS, object=target)

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_editview__target_changes(self):
        user = self.login_as_root_and_get()

        name = 'opportunity01'
        opp, target1, emitter = self._create_opportunity_n_organisations(user=user, name=name)
        target2 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        target_rel = self.get_object_or_fail(
            Relation, subject_entity=opp.id, object_entity=target1.id,
        )
        self.assertNoFormError(self.client.post(
            opp.get_edit_absolute_url(),
            follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'reference':             '1256',
                'sales_phase':           opp.sales_phase_id,
                'expected_closing_date': self.formfield_value_date(2013, 4, 26),
                'closing_date':          self.formfield_value_date(2013, 5, 15),
                'first_action_date':     self.formfield_value_date(2013, 5, 1),
                'currency':              opp.currency_id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        ))
        self.assertEqual(target2, self.refresh(opp).target)
        self.assertDoesNotExist(target_rel)
        self.assertHaveRelation(subject=target2, type=REL_SUB_PROSPECT, object=emitter)

    @parameterized.expand([False, True])
    @skipIfCustomOrganisation
    def test_editview__won_workflow(self, target_is_contact):
        user = self.login_as_root_and_get()

        name = 'Opportunity #01'
        opp, target, emitter = self._create_opportunity_n_organisations(
            user=user, name=name, contact=target_is_contact,
        )
        self.assertFalse(opp.sales_phase.won)

        phase = SalesPhase.objects.filter(won=True)[0]
        self.assertNoFormError(self.client.post(
            opp.get_edit_absolute_url(),
            follow=True,
            data={
                'user':                  user.pk,
                'name':                  name,
                'reference':             '1256',
                'sales_phase':           phase.id,
                'expected_closing_date': self.formfield_value_date(2011, 4, 26),
                'closing_date':          self.formfield_value_date(2011, 5, 15),
                'first_action_date':     self.formfield_value_date(2011, 5, 1),
                'currency':              opp.currency_id,

                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        ))

        opp = self.refresh(opp)
        self.assertEqual(phase, opp.sales_phase)
        self.assertHaveRelation(target, type=REL_SUB_CUSTOMER_SUPPLIER, object=emitter)

    @skipIfCustomOrganisation
    def test_listview(self):
        user = self.login_as_root_and_get()

        opp1 = self._create_opportunity_n_organisations(user=user, name='Opp1')[0]
        opp2 = self._create_opportunity_n_organisations(user=user, name='Opp2')[0]

        response = self.assertGET200(reverse('opportunities__list_opportunities'))

        with self.assertNoException():
            opps_page = response.context['page_obj']

        self.assertEqual(2, opps_page.paginator.count)
        self.assertCountEqual([opp1, opp2], opps_page.object_list)

    @skipIfCustomOrganisation
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete__related(self):
        "Cannot delete the target & the source."
        user = self.login_as_root_and_get()

        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name='My Opp')
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
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete(self):
        "Can delete the Opportunity."
        user = self.login_as_root_and_get()

        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name='My Opp')
        opp.trash()

        self.assertPOST200(opp.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(opp)
        self.assertStillExists(target)
        self.assertStillExists(emitter)

    def test_clone(self):
        user = self.login_as_root_and_get()

        opportunity, target, emitter = self._create_opportunity_n_organisations(user=user)
        clone = self.clone(opportunity)

        self.assertEqual(opportunity.name,         clone.name)
        self.assertEqual(opportunity.sales_phase,  clone.sales_phase)
        self.assertEqual(opportunity.closing_date, clone.closing_date)

        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
        self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=clone)

        self.assertHaveRelation(target, type=constants.REL_OBJ_TARGETS, object=opportunity)
        # Internal
        self.assertHaveRelation(target, type=constants.REL_OBJ_TARGETS, object=clone)

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     opportunity, target, emitter = self._create_opportunity_n_organisations(user=user)
    #     cloned = opportunity.clone()
    #
    #     self.assertEqual(opportunity.name,         cloned.name)
    #     self.assertEqual(opportunity.sales_phase,  cloned.sales_phase)
    #     self.assertEqual(opportunity.closing_date, cloned.closing_date)
    #
    #     self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=opportunity)
    #     self.assertHaveRelation(emitter, type=constants.REL_SUB_EMIT_ORGA, object=cloned)
    #
    #     self.assertHaveRelation(target, type=constants.REL_OBJ_TARGETS, object=opportunity)
    #     # Internal
    #     self.assertHaveRelation(target, type=constants.REL_OBJ_TARGETS, object=cloned)

    @skipIfCustomOrganisation
    def test_get_weighted_sales(self):
        user = self.login_as_root_and_get()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(number_format('0.0'), funf(opportunity, user).render(ViewTag.HTML_LIST))

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   = 10
        self.assertEqual(
            number_format('100.0'),
            funf(opportunity, user).render(ViewTag.HTML_LIST),
        )

    @skipIfCustomOrganisation
    def test_get_weighted_sales__hidden(self):
        "With field 'estimated_sales' hidden with FieldsConfig."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        opportunity = self._create_opportunity_n_organisations(user=user)[0]

        FieldsConfig.objects.get_for_model(Opportunity)

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')

        with self.assertNumQueries(0):
            w_sales = funf(opportunity, user).render(ViewTag.HTML_LIST)

        self.assertEqual(_('Error: «Estimated sales» is hidden'), w_sales)

    def test_delete_currency(self):
        user = self.login_as_root_and_get()

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
            self.get_form_or_fail(response),
            field='replace_opportunities__opportunity_currency',
            errors=_('Deletion is not possible.'),
        )

    def test_bulk_edit(self):
        "Bulk edit 2 Opportunities."
        user = self.login_as_root_and_get()
        target, emitter = self._create_target_n_emitter(user=user)
        phase1, phase2, phase3 = SalesPhase.objects.all()[:3]

        create_opport = partial(
            Opportunity.objects.create, user=user,
            emitter=emitter,
            target=target,
        )
        opport1 = create_opport(name='Opp#1', sales_phase=phase1)
        opport2 = create_opport(name='Opp#2', sales_phase=phase2)

        field_name = 'sales_phase'
        url = self.build_bulkupdate_uri(
            model=Opportunity, field=field_name, entities=[opport1, opport2],
        )
        response = self.assertPOST200(
            url,
            data={
                'entities': [opport1.id, opport2.id],
                field_name: phase3.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(phase3, getattr(self.refresh(opport1), field_name))
        self.assertEqual(phase3, getattr(self.refresh(opport2), field_name))

    def test_bulk_edit__user(self):
        "Bulk edit the field 'user' for 2 Opportunities (bugfix)."
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()
        target, emitter = self._create_target_n_emitter(user=user1)
        phase = SalesPhase.objects.first()

        create_opport = partial(
            Opportunity.objects.create,
            user=user1, emitter=emitter, target=target, sales_phase=phase,
        )
        opport1 = create_opport(name='Opp #1')
        opport2 = create_opport(name='Opp #2')

        field_name = 'user'
        url = self.build_bulkupdate_uri(
            model=Opportunity, field=field_name, entities=[opport1, opport2],
        )
        response = self.assertPOST200(
            url,
            data={
                'entities': [opport1.id, opport2.id],
                field_name: user2.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(user2, getattr(self.refresh(opport1), field_name))
        self.assertEqual(user2, getattr(self.refresh(opport2), field_name))
