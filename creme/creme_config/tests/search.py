# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import SearchConfigItem, SearchField
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error:', e


__all__ = ('SearchConfigTestCase',)


class SearchConfigTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/search/portal/').status_code)

    def test_add01(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(0, SearchConfigItem.objects.filter(content_type=ct).count())

        url = '/creme_config/search/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'ct_id': ct.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))
        self.assertIsNone(sc_items[0].user)

    def test_add02(self):
        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_config/search/add/'
        post_data = {'ct_id': ct.id,
                     'user':  self.other_user.id,
                    }
        response = self.client.post(url, post_data)
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))
        self.assertEqual(self.other_user, sc_items[0].user)

        response = self.client.post(url, post_data)
        self.assertFormError(response, 'form', None, [_(u'The pair search configuration/user(s) already exists !')])

    def _find_field_index(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                return i

        self.fail('No "%s" in field' % field_name)

    def assertNoChoice(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                self.fail(field_name + ' in choices')

    def test_edit(self):
        ct = ContentType.objects.get_for_model(Contact)
        sci = SearchConfigItem.objects.create(content_type=ct, user=None)
        url = '/creme_config/search/edit/%s' % sci.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields['fields']
        except KeyError as e:
            self.fail(str(e))

        index1 = self._find_field_index(fields, 'first_name')
        index2 = self._find_field_index(fields, 'last_name')
        self._find_field_index(fields, 'civility__title')
        self.assertNoChoice(fields, 'birthday')

        response = self.client.post(url,
                                    data={
                                            'fields_check_%s' % index1: 'on',
                                            'fields_value_%s' % index1: 'first_name',
                                            'fields_order_%s' % index1: 1,

                                            'fields_check_%s' % index2: 'on',
                                            'fields_value_%s' % index2: 'last_name',
                                            'fields_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        sf = SearchField.objects.filter(search_config_item=sci).order_by('order')
        self.assertEqual(2, len(sf))
        self.assertEqual('first_name', sf[0].field)
        self.assertEqual('last_name',  sf[1].field)

    def test_delete(self):
        ct = ContentType.objects.get_for_model(Contact)
        sci = SearchConfigItem.objects.create(content_type=ct, user=None)
        sf1 = SearchField.objects.create(search_config_item=sci, field='first_name', order=1)
        sf2 = SearchField.objects.create(search_config_item=sci, field='last_name', order=2)

        response = self.client.post('/creme_config/search/delete', data={'id': sci.id})
        self.assertEqual(200, response.status_code)
        self.assertFalse(SearchConfigItem.objects.filter(pk=sci.pk).exists())
        self.assertFalse(SearchField.objects.filter(pk__in=[sf1.pk, sf2.pk]).exists())
