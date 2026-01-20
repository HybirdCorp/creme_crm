from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme import products
from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT
from creme.creme_core.models import RelationType, SettingValue, Workflow
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.opportunities import constants, setting_keys
from creme.opportunities.models import Origin, SalesPhase

from .base import Contact, OpportunitiesBaseTestCase, Opportunity, Organisation


class OpportunitiesAppTestCase(OpportunitiesBaseTestCase):
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

    @skipIfNotInstalled('creme.billing')
    def test_populate__billing(self):
        from creme import billing

        Invoice = billing.get_invoice_model()
        Quote = billing.get_quote_model()
        SalesOrder = billing.get_sales_order_model()

        relation_types = RelationType.objects.compatible(Opportunity).in_bulk()

        self.assertIn(constants.REL_OBJ_LINKED_SALESORDER, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_SALESORDER, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder],
        )

        self.assertIn(constants.REL_OBJ_LINKED_INVOICE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_INVOICE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice],
        )

        self.assertIn(constants.REL_OBJ_LINKED_QUOTE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_QUOTE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote],
        )

        self.get_relationtype_or_fail(
            constants.REL_OBJ_CURRENT_DOC,
            [Opportunity],
            [Invoice, Quote, SalesOrder],
        )
