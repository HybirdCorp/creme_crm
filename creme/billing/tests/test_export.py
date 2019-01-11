# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial
    from os.path import basename, dirname, exists, join

    from django.conf import settings
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials, FileRef

    from creme.persons.tests.base import skipIfCustomOrganisation

    from .base import (_BillingTestCase, skipIfCustomInvoice, skipIfCustomQuote,
            skipIfCustomProductLine, skipIfCustomServiceLine, Organisation,
            Invoice, ProductLine, ServiceLine)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomOrganisation
class ExportTestCase(_BillingTestCase):
    def _build_export_url(self, entity):
        return reverse('billing__export', args=(entity.id,))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_invoice(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('My Invoice', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user,
                              related_document=invoice,
                             )
        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        existing_fileref_ids = list(FileRef.objects.values_list('id', flat=True))

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual(u'{}_{}.pdf'.format(_(u'Invoice'), invoice.id), fileref.basename)
        # self.assertEqual(user, fileref.user) TODO

        fullpath = fileref.filedata.path
        self.assertTrue(exists(fullpath), '<{}> does not exists ?!'.format(fullpath))
        self.assertEqual(join(settings.MEDIA_ROOT, 'upload', 'billing'), dirname(fullpath))
        self.assertEqual('attachment; filename={}'.format(basename(fullpath)), response['Content-Disposition'])

    @skipIfCustomQuote
    @skipIfCustomServiceLine
    def test_quote(self):
        user = self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        create_line = partial(ServiceLine.objects.create, user=user,
                              related_document=quote,
                             )
        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

    def test_bad_ct(self):
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Laputa')
        self.assertGET409(self._build_export_url(orga))

    @skipIfCustomInvoice
    def test_credentials01(self):
        "Billing entity credentials"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Organisation],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        invoice.user = self.other_user
        invoice.save()

        self.assertFalse(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))

    @skipIfCustomInvoice
    def test_credentials02(self):
        "Source credentials"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Organisation],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        source.user = self.other_user
        source.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertFalse(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))

    @skipIfCustomInvoice
    def test_credentials03(self):
        "Target credentials"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Organisation],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        target.user = self.other_user
        target.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertFalse(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))
