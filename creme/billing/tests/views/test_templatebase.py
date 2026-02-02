from datetime import date
from functools import partial

from django.utils.translation import gettext as _

from creme.billing.models import InvoiceStatus, QuoteStatus
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    Invoice,
    Organisation,
    Quote,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomTemplateBase,
)


@skipIfCustomOrganisation
@skipIfCustomTemplateBase
class TemplateBaseViewsTestCase(_BillingTestCase):
    STATUS_KEY = 'cform_extra-billing_template_status'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        create_orga = partial(Organisation.objects.create, user=cls.get_root_user())
        cls.source = create_orga(name='Source')
        cls.target = create_orga(name='Target')

    def _create_templatebase(self, *, user, model, status_uuid, name=None, comment='', **kwargs):
        return TemplateBase.objects.create(
            user=user,
            ct=model,
            name=name or f'{model._meta.verbose_name} template',
            status_uuid=status_uuid,
            comment=comment,
            source=self.source,
            target=self.target,
            **kwargs
        )

    def test_detail_view(self):
        user = self.login_as_root_and_get()
        invoice_status = InvoiceStatus.objects.filter(is_default=False).first()
        tpl = self._create_templatebase(
            user=user, model=Invoice, status_uuid=invoice_status.uuid,
        )
        response = self.assertGET200(tpl.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_template.html')

    def test_edition(self):
        user = self.login_as_root_and_get()

        invoice_status1, invoice_status2 = InvoiceStatus.objects.filter(
            is_default=False,
        ).order_by('-id')[:2]

        name = 'My template'
        tpl = self._create_templatebase(
            user=user, model=Invoice, status_uuid=invoice_status1.uuid, name=name,
        )

        url = tpl.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            formfields = response1.context['form'].fields
            source_f = formfields[self.SOURCE_KEY]
            target_f = formfields[self.TARGET_KEY]
            status_f = formfields[self.STATUS_KEY]
            number_f = formfields['number']

        self.assertEqual(self.source, source_f.initial)
        self.assertEqual(self.target, target_f.initial)
        self.assertEqual(invoice_status1.id, status_f.initial)
        self.assertEqual(
            _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
            number_f.help_text,
        )

        # POST ---
        name += ' (edited)'

        create_orga = partial(Organisation.objects.create, user=user)
        source2 = create_orga(name='Source Orga 2')
        target2 = create_orga(name='Target Orga 2')

        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2020, 10, 31),
                'expiration_date': self.formfield_value_date(2020, 11, 30),
                self.STATUS_KEY:    invoice_status2.id,
                'currency':        tpl.currency_id,
                'discount':        '0',

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, tpl.get_absolute_url())

        tpl = self.refresh(tpl)
        self.assertEqual(name, tpl.name)
        self.assertEqual(date(year=2020, month=11, day=30), tpl.expiration_date)
        self.assertIsNone(tpl.payment_info)
        self.assertUUIDEqual(invoice_status2.uuid, tpl.status_uuid)

        self.assertEqual(source2, tpl.source)
        self.assertEqual(target2, tpl.target)

    def test_list_view(self):
        user = self.login_as_root_and_get()
        invoice_status = InvoiceStatus.objects.first()
        quote_status   = QuoteStatus.objects.first()

        tpl1 = self._create_templatebase(
            user=user, model=Invoice, status_uuid=invoice_status.uuid,
            name='Invoice template',
        )
        tpl2 = self._create_templatebase(
            user=user, model=Quote, status_uuid=quote_status.uuid,
            name='Quote template',
        )

        response = self.assertGET200(TemplateBase.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['page_obj']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertCountEqual([tpl1, tpl2], quotes_page.paginator.object_list)

    # TODO: test form
