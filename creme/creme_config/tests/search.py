# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import SearchConfigItem
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SearchConfigTestCase',)


class SearchConfigTestCase(CremeTestCase):
    ADD_URL = '/creme_config/search/add/'

    @classmethod
    def setUpClass(cls):
        SearchConfigItem.objects.all().delete()

        cls.populate('creme_core', 'creme_config')

        cls.ct_contact = ContentType.objects.get_for_model(Contact)

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertGET200('/creme_config/search/portal/')

    def test_add01(self):
        ct = self.ct_contact
        self.assertEqual(0, SearchConfigItem.objects.filter(content_type=ct).count())

        url = self.ADD_URL
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'content_type': ct.id}))

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))
        self.assertIsNone(sc_items[0].user)

    def test_add02(self):
        post = partial(self.client.post, self.ADD_URL, data={'content_type': self.ct_contact.id,
                                                             'user':         self.other_user.id,
                                                            }
                      )
        self.assertNoFormError(post())

        sc_items = SearchConfigItem.objects.filter(content_type=self.ct_contact)
        self.assertEqual(1, len(sc_items))
        self.assertEqual(self.other_user, sc_items[0].user)

        self.assertFormError(post(), 'form', None,
                             [_(u'The pair search configuration/user(s) already exists !')]
                            )

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
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact, user=None)
        url = '/creme_config/search/edit/%s' % sci.id

        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        index1 = self._find_field_index(fields, 'first_name')
        index2 = self._find_field_index(fields, 'last_name')
        self._find_field_index(fields, 'civility__title')
        self.assertNoChoice(fields, 'birthday')

        response = self.client.post(url,
                                    data={'fields_check_%s' % index1: 'on',
                                          'fields_value_%s' % index1: 'first_name',
                                          'fields_order_%s' % index1: 1,

                                          'fields_check_%s' % index2: 'on',
                                          'fields_value_%s' % index2: 'last_name',
                                          'fields_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(['first_name', 'last_name'], [sf.name for sf in self.refresh(sci).searchfields])

    def test_delete(self):
        sci = SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self.assertPOST200('/creme_config/search/delete', data={'id': sci.id})
        self.assertDoesNotExist(sci)
