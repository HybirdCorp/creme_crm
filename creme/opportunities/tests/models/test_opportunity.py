from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import CremeEntity, Currency
from creme.opportunities import constants
from creme.opportunities.models import SalesPhase
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
class OpportunityTestCase(OpportunitiesBaseTestCase):
    def test_sales_phase_fk(self):
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
