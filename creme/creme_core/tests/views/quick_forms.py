# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _
    from django.forms.formsets import BaseFormSet

    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Civility, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('QuickFormTestCase',)


class QuickFormTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def quickform_data(self, count):
        return {
                'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   '%s' % count,
                'csrfmiddlewaretoken': '08b8b225c536b4fd25d16f5ed8be3839',
                'whoami': '1335517612234535305',
               }

    def quickform_data_append(self, data, id, first_name='', last_name='', email='', organisation='', phone=''):
        return data.update({
                 'form-%d-email' % id:        email,
                 'form-%d-last_name' % id:    last_name,
                 'form-%d-first_name' % id:   first_name,
                 'form-%d-organisation' % id: organisation,
                 'form-%d-phone' % id:        phone,
                 'form-%d-user' % id:         '1',
               })

    # warning : this method has not same behaviour as assertFormError. do both error and no error tests
    def assertFormSetError(self, response, form, index, fieldname, expected_errors=None):
        self.assertIn(form, response.context)

        self.assertIsInstance(response.context[form], BaseFormSet, "context field '%s' is not a FormSet")
        self.assertGreaterEqual(index, 0)
        self.assertLess(index, len(response.context[form].errors))

        errors = response.context[form].errors[index]

        has_field_error = fieldname in errors.keys()

        if not has_field_error and not expected_errors:
            return

        if not has_field_error and expected_errors:
            self.fail("The field '%s' on formset '%s' number %d contains no errors, expected:%s" % (fieldname, form, index, expected_errors))

        if has_field_error and not expected_errors:
            self.fail("The field '%s' on formset '%s' number %d contains errors:%s, expected none" % (fieldname, form, index, errors[fieldname]))

        self.assertItemsEqual(expected_errors, errors[fieldname],
                              "The field '%s' on formset '%s' number %d errors are:%s, expected:%s" % (fieldname, form, index, errors[fieldname], expected_errors))

    def _build_quickform_url(self, model, count):
        return '/creme_core/quickforms/%d/%d' % (ContentType.objects.get_for_model(model).pk, count)

    def test_add_unknown_ctype(self):
        self.login()
        self.assertEqual(404, self.client.get('/creme_core/quickforms/10000/1').status_code)

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, last_name='Kirika')

        self.assertEqual(404, self.client.post('/creme_core/quickforms/10000/1', data).status_code)

    def test_add_unregistered_ctype(self):
        self.login()
        self.assertEqual(404, self.client.get(self._build_quickform_url(Civility, 1)).status_code)

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, last_name='Kirika')

        self.assertEqual(404, self.client.post(self._build_quickform_url(Civility, 1), data).status_code)

    def test_add_unallowed(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons'), creatable_models=(Organisation,))

        self.assertEqual(403, self.client.get(self._build_quickform_url(Contact, 1)).status_code)
        self.assertEqual(200, self.client.get(self._build_quickform_url(Organisation, 1)).status_code)

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, last_name='Kirika')

        self.assertEqual(403, self.client.post(self._build_quickform_url(Contact, 1), data).status_code)
        self.assertEqual(200, self.client.post(self._build_quickform_url(Organisation, 1), data).status_code)

    def test_add_empty_form(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0)

        response = self.client.post(self._build_quickform_url(Contact, 1), data)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'last_name', [_('This field is required.')])
        self.assertFormSetError(response, 'formset', 0, 'last_name', [_(u'This field is required.')])

        self.assertEqual(count, Contact.objects.count())

    def test_add_multiple_empty_form(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(3)
        self.quickform_data_append(data, 0)
        self.quickform_data_append(data, 1)
        self.quickform_data_append(data, 2)

        response = self.client.post(self._build_quickform_url(Contact, 3), data)
        self.assertEqual(200, response.status_code)
        self.assertFormSetError(response, 'formset', 0, 'last_name', [_(u'This field is required.')])
        self.assertFormSetError(response, 'formset', 1, 'last_name', [_(u'This field is required.')])
        self.assertFormSetError(response, 'formset', 2, 'last_name', [_(u'This field is required.')])

        self.assertEqual(count, Contact.objects.count())

    def test_add_invalid_form(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, email='invalid')

        response = self.client.post(self._build_quickform_url(Contact, 1), data)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'last_name', [_(u'This field is required.')])
        self.assertFormError(response, 'form', 'email', [_(u'Enter a valid e-mail address.')])

        self.assertFormSetError(response, 'formset', 0, 'last_name', [_(u'This field is required.')])

        self.assertEqual(count, Contact.objects.count())

    def test_add_multiple_invalid_form(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(3)
        self.quickform_data_append(data, 0, last_name='Kirika', email='admin@hello.com')
        self.quickform_data_append(data, 1, email='invalid')
        self.quickform_data_append(data, 2, last_name='Mireille', email='invalid')

        response = self.client.post(self._build_quickform_url(Contact, 3), data)
        self.assertEqual(200, response.status_code)
        self.assertFormSetError(response, 'formset', 0, 'last_name')
        self.assertFormSetError(response, 'formset', 0, 'email')

        self.assertFormSetError(response, 'formset', 1, 'last_name', [_(u'This field is required.')])
        self.assertFormSetError(response, 'formset', 1, 'email', [_(u'Enter a valid e-mail address.')])

        self.assertFormSetError(response, 'formset', 2, 'last_name')
        self.assertFormSetError(response, 'formset', 2, 'email', [_(u'Enter a valid e-mail address.')])

        self.assertEqual(count, Contact.objects.count())

    def test_add(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, last_name='Kirika', email='admin@hello.com')

        response = self.client.post(self._build_quickform_url(Contact, 1), data)
        self.assertEqual(200, response.status_code)

        self.assertEqual(count + 1, Contact.objects.count())
        contact = self.get_object_or_fail(Contact, email='admin@hello.com')
        self.assertEqual('admin@hello.com', contact.email)
        self.assertEqual('Kirika', contact.last_name)

    def test_add_multiple(self):
        self.login()
        count = Contact.objects.count()

        data = self.quickform_data(3)
        self.quickform_data_append(data, 0, last_name='Kirika', email='admin@hello.com')
        self.quickform_data_append(data, 1, last_name='Mireille', email='admin2@hello.com')
        self.quickform_data_append(data, 2, last_name='Lain', email='admin3@hello.com')

        response = self.client.post(self._build_quickform_url(Contact, 3), data)
        self.assertEqual(200, response.status_code)

        self.assertEqual(count + 3, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, email='admin@hello.com')
        self.assertEqual('admin@hello.com', contact.email)
        self.assertEqual('Kirika', contact.last_name)

        contact = self.get_object_or_fail(Contact, email='admin2@hello.com')
        self.assertEqual('admin2@hello.com', contact.email)
        self.assertEqual('Mireille', contact.last_name)

        contact = self.get_object_or_fail(Contact, email='admin3@hello.com')
        self.assertEqual('admin3@hello.com', contact.email)
        self.assertEqual('Lain', contact.last_name)
