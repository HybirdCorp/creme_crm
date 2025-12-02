from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    BrickDetailviewLocation,
    RelationType,
    SettingValue,
    Vat,
    Workflow,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from .. import bricks, constants, setting_keys
from ..models import (
    CreditNoteStatus,
    InvoiceStatus,
    QuoteStatus,
    SalesOrderStatus,
)
from .base import (
    Contact,
    CreditNote,
    Invoice,
    Organisation,
    Product,
    ProductLine,
    Quote,
    SalesOrder,
    Service,
    ServiceLine,
    TemplateBase,
    _BillingTestCase,
)


class AppTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_populate(self):
        billing_classes = [
            Invoice, Quote, SalesOrder, CreditNote, TemplateBase,
        ]
        lines_classes = [ProductLine, ServiceLine]

        # ---
        self.get_relationtype_or_fail(
            constants.REL_SUB_BILL_ISSUED, billing_classes, [Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_BILL_RECEIVED, billing_classes, [Organisation, Contact],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_HAS_LINE, billing_classes, lines_classes,
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_LINE_RELATED_ITEM, lines_classes, [Product, Service],
        )

        # ---
        self.assertEqual(4, QuoteStatus.objects.count())
        self.assertEqual(1, QuoteStatus.objects.filter(is_default=True).count())

        self.assertEqual(4, SalesOrderStatus.objects.count())
        self.assertEqual(1, SalesOrderStatus.objects.filter(is_default=True).count())

        self.assertEqual(8, InvoiceStatus.objects.count())
        self.assertEqual(1, InvoiceStatus.objects.filter(is_default=True).count())
        self.assertEqual(1, InvoiceStatus.objects.filter(is_validated=True).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pending_payment=True).count())

        self.assertEqual(4, CreditNoteStatus.objects.count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(is_default=True).count())

        self.assertTrue(Vat.objects.exists())  # In creme_core populate...

        # ---
        sv = self.get_object_or_fail(
            SettingValue, key_id=setting_keys.button_redirection_key.id,
        )
        self.assertIs(True, sv.value)

        sv = self.get_object_or_fail(
            SettingValue, key_id=setting_keys.emitter_edition_key.id,
        )
        self.assertIs(False, sv.value)

        # ---
        wf_quote_orga = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_QUOTE_ORGA_TO_PROSPECT,
        )
        self.assertEqual(
            _('The target Organisation becomes a prospect'), wf_quote_orga.title,
        )
        self.assertEqual(wf_quote_orga.content_type.model_class(), Quote)
        self.assertFalse(wf_quote_orga.is_custom)

        wf_quote_contact = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_QUOTE_CONTACT_TO_PROSPECT,
        )
        self.assertEqual(
            _('The target Contact becomes a prospect'), wf_quote_contact.title,
        )
        self.assertEqual(wf_quote_contact.content_type.model_class(), Quote)
        self.assertFalse(wf_quote_contact.is_custom)

        wf_invoice_orga = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_INVOICE_ORGA_TO_CUSTOMER,
        )
        self.assertEqual(
            _('The target Organisation becomes a customer'), wf_invoice_orga.title,
        )
        self.assertEqual(wf_invoice_orga.content_type.model_class(), Invoice)
        self.assertFalse(wf_invoice_orga.is_custom)

        wf_invoice_contact = self.get_object_or_fail(
            Workflow, uuid=constants.UUID_WORKFLOW_INVOICE_CONTACT_TO_CUSTOMER,
        )
        self.assertEqual(
            _('The target Contact becomes a customer'), wf_invoice_contact.title,
        )
        self.assertEqual(wf_invoice_contact.content_type.model_class(), Invoice)
        self.assertFalse(wf_invoice_contact.is_custom)

    @skipIfNotInstalled('creme.activities')
    def test_populate__activities(self):
        # Contribution to activities
        from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(m).id for m in (Invoice, Quote, SalesOrder)]
        self.assertEqual(len(ct_ids), rtype.subject_ctypes.filter(id__in=ct_ids).count())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())

    @skipIfCustomOrganisation
    def test_bricks_for_organisation(self):
        user = self.login_as_root_and_get()

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.payment_info_key.id)
        self.assertIs(True, sv.value)

        orga = Organisation.objects.create(user=user, name='NERV')

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/bricks/orga-payment-information.html'
        self.assertTemplateNotUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/bricks/received-invoices.html')
        self.assertTemplateUsed(response, 'billing/bricks/received-billing-documents.html')

        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    @skipIfCustomOrganisation
    def test_bricks_for_organisation__managed(self):
        "Managed organisation."
        user = self.login_as_root_and_get()

        orga = self._set_managed(Organisation.objects.create(user=user, name='NERV'))

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/bricks/orga-payment-information.html'
        self.assertTemplateUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/bricks/received-invoices.html')
        self.assertTemplateUsed(response, 'billing/bricks/received-billing-documents.html')

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.payment_info_key.id)
        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    @skipIfCustomOrganisation
    def test_bricks_for_organisation__statistics(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='NERV')
        brick_id = bricks.PersonsStatisticsBrick.id

        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id, order=1000,
            zone=BrickDetailviewLocation.LEFT,
            model=Organisation,
        )

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/bricks/persons-statistics.html')

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick_id)
