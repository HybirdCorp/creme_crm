# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase

    from persons.models import Civility

    from billing.models import InvoiceStatus
except Exception as e:
    print 'Error:', e


__all__ = ('GenericModelConfigTestCase',)


class GenericModelConfigTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portals(self):
        self.assertEqual(200, self.client.get('/creme_config/persons/portal/').status_code)
        self.assertEqual(404, self.client.get('/creme_config/unexsitingapp/portal/').status_code)

        self.assertEqual(200, self.client.get('/creme_config/persons/civility/portal/').status_code)
        self.assertEqual(404, self.client.get('/creme_config/persons/unexsitingmodel/portal/').status_code)

        self.assertEqual(200, self.client.get('/creme_config/billing/invoice_status/portal/').status_code)

    def test_add01(self):
        self.assertEqual(0, Civility.objects.count())

        url = '/creme_config/persons/civility/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        title = 'Herr'
        response = self.client.post(url, data={'title': title})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            Civility.objects.filter(title=title)
        except Exception as e:
            self.fail(str(e))

    def test_add02(self):
        self.assertEqual(0, InvoiceStatus.objects.count())

        url = '/creme_config/billing/invoice_status/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Okidoki'
        response = self.client.post(url, data={'name': name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            InvoiceStatus.objects.filter(name=name, is_custom=True)
        except Exception as e:
            self.fail(str(e))

    def test_edit(self):
        title = 'herr'
        civ = Civility.objects.create(title=title)

        url = '/creme_config/persons/civility/edit/%s' % civ.id
        self.assertEqual(200, self.client.get(url).status_code)

        title = title.title()
        response = self.client.post(url, data={'title': title})
        self.assertNoFormError(response)
        self.assertEqual(200,   response.status_code)
        self.assertEqual(title, self.refresh(civ).title)

    def test_delete01(self):
        pk = Civility.objects.create(title='Herr').pk
        response = self.client.post('/creme_config/persons/civility/delete', data={'id': pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(Civility.objects.filter(pk=pk).exists())

    def test_delete02(self):
        pk = InvoiceStatus.objects.create(name='Okidoki', is_custom=False).pk
        response = self.client.post('/creme_config/persons/civility/delete', data={'id': pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(InvoiceStatus.objects.filter(pk=pk).exists())

#TODO: (r'^models/(?P<ct_id>\d+)/reload/$', 'generics_views.reload_block'),
