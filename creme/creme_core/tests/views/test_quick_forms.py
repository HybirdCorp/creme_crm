# -*- coding: utf-8 -*-

try:
    from json import dumps as json_dump

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from .base import CremeTestCase

    from ..fake_models import FakeContact, FakeOrganisation, FakeCivility
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class QuickFormTestCase(CremeTestCase):
    def quickform_data(self, count):
        return {'form-INITIAL_FORMS':  '0',
                'form-MAX_NUM_FORMS':  '',
                'form-TOTAL_FORMS':    '%s' % count,
                'csrfmiddlewaretoken': '08b8b225c536b4fd25d16f5ed8be3839',
                'whoami':              '1335517612234535305',
               }

    def quickform_data_append_contact(self, data, id, first_name='', last_name='', email='', organisation='', phone=''):
        return data.update({
                 'form-%d-email' % id:        email,
                 'form-%d-last_name' % id:    last_name,
                 'form-%d-first_name' % id:   first_name,
                 'form-%d-organisation' % id: organisation,
                 'form-%d-phone' % id:        phone,
                 'form-%d-user' % id:         self.user.id,
               })

    def _build_quickform_url(self, model, count=1):
        return reverse('creme_core__quick_forms', args=(ContentType.objects.get_for_model(model).pk, count))

    def test_add_unknown_ctype(self):
        self.login()

        invalid_id = 10000
        self.assertFalse(ContentType.objects.filter(id=invalid_id))

        url = reverse('creme_core__quick_forms', args=(invalid_id, 1))
        self.assertGET404(url)

        data = self.quickform_data(1)
        self.quickform_data_append_contact(data, 0, last_name='Kirika')

        self.assertPOST404(url, data)

    def test_add_unregistered_ctype(self):
        self.login()
        self.assertGET404(self._build_quickform_url(FakeCivility))

        data = self.quickform_data(1)
        self.quickform_data_append_contact(data, 0, last_name='Kirika')

        self.assertPOST404(self._build_quickform_url(FakeCivility), data)

    def test_add_forbidden(self):
        self.login(is_superuser=False,
                   creatable_models=[FakeOrganisation],
                  )

        self.assertGET403(self._build_quickform_url(FakeContact))
        self.assertGET200(self._build_quickform_url(FakeOrganisation))

        data = self.quickform_data(1)
        self.quickform_data_append_contact(data, 0, last_name='Kirika')

        self.assertPOST403(self._build_quickform_url(FakeContact), data)
        self.assertPOST200(self._build_quickform_url(FakeOrganisation), data)

    def test_add_empty_form(self):
        self.login()
        count = FakeContact.objects.count()

        data = self.quickform_data(1)
        self.quickform_data_append_contact(data, 0)

        response = self.assertPOST200(self._build_quickform_url(FakeContact), data)
        self.assertFormError(response, 'form', 'last_name', _('This field is required.'))
        self.assertFormsetError(response, 'formset', 0, 'last_name', _(u'This field is required.'))

        self.assertEqual(count, FakeContact.objects.count())

    def test_add_multiple_empty_form(self):
        self.login()
        count = FakeContact.objects.count()

        data = self.quickform_data(3)
        self.quickform_data_append_contact(data, 0)
        self.quickform_data_append_contact(data, 1)
        self.quickform_data_append_contact(data, 2)

        response = self.assertPOST200(self._build_quickform_url(FakeContact, 3), data)
        msg = _(u'This field is required.')
        self.assertFormsetError(response, 'formset', 0, 'last_name', msg)
        self.assertFormsetError(response, 'formset', 1, 'last_name', msg)
        self.assertFormsetError(response, 'formset', 2, 'last_name', msg)

        self.assertEqual(count, FakeContact.objects.count())

    def test_add_invalid_form(self):
        self.login()
        count = FakeContact.objects.count()

        data = self.quickform_data(1)
        self.quickform_data_append_contact(data, 0, email='invalid')

        response = self.assertPOST200(self._build_quickform_url(FakeContact), data)
        self.assertFormError(response, 'form', 'last_name', _(u'This field is required.'))
        self.assertFormError(response, 'form', 'email',     _(u'Enter a valid email address.'))

        self.assertFormsetError(response, 'formset', 0, 'last_name', _(u'This field is required.'))
        self.assertEqual(count, FakeContact.objects.count())

    def test_add_multiple_invalid_form(self):
        self.login()
        count = FakeContact.objects.count()

        data = self.quickform_data(3)
        self.quickform_data_append_contact(data, 0, last_name='Kirika', email='admin@hello.com')
        self.quickform_data_append_contact(data, 1, email='invalid')
        self.quickform_data_append_contact(data, 2, last_name='Mireille', email='invalid')

        response = self.assertPOST200(self._build_quickform_url(FakeContact, 3), data)
        self.assertNoFormsetError(response, 'formset', 0)

        self.assertFormsetError(response, 'formset', 1, 'last_name', _(u'This field is required.'))
        self.assertFormsetError(response, 'formset', 1, 'email',     _(u'Enter a valid email address.'))

        self.assertNoFormsetError(response, 'formset', 2, 'last_name')
        self.assertFormsetError(response, 'formset', 2, 'email', _(u'Enter a valid email address.'))

        self.assertEqual(count, FakeContact.objects.count())

    def test_add(self):
        self.login()
        count = FakeContact.objects.count()

        data = self.quickform_data(1)
        last_name = 'Kirika'
        email = 'admin@hello.com'
        self.quickform_data_append_contact(data, 0, last_name=last_name, email=email)

        self.assertPOST200(self._build_quickform_url(FakeContact), data)
        self.assertEqual(count + 1, FakeContact.objects.count())
        self.get_object_or_fail(FakeContact, last_name=last_name, email=email)

    def test_add_multiple(self):
        self.login()
        count = FakeContact.objects.count()

        contacts = [{'last_name': t[0], 'email': t[1]}
                        for t in [('Kirika',   'admin@hello.com'),
                                  ('Mireille', 'admin2@hello.com'),
                                  ('Chloe',    'admin3@hello.com'),
                                 ]
                   ]
        length = len(contacts)
        data = self.quickform_data(length)

        for i, kwargs in enumerate(contacts):
            self.quickform_data_append_contact(data, i, **kwargs)

        self.assertPOST200(self._build_quickform_url(FakeContact, length), data)
        self.assertEqual(count + length, FakeContact.objects.count())

        for kwargs in contacts:
            self.get_object_or_fail(FakeContact, **kwargs)

    def test_add_from_widget(self):
        user = self.login()
        count = FakeContact.objects.count()
        ct_id = ContentType.objects.get_for_model(FakeContact).id

        # Deprecated
        self.assertGET200(reverse('creme_core__quick_form', args=(ct_id, 1)))

        url = reverse('creme_core__quick_form', args=(ct_id,))
        self.assertGET200(url)

        last_name = 'Kirika'
        email = 'admin@hello.com'
        response = self.assertPOST200(url,
                                      data={'last_name': last_name,
                                            'email':     email,
                                            'user':      user.id,
                                           }
                                     )
        self.assertEqual(count + 1, FakeContact.objects.count())

        contact = self.get_object_or_fail(FakeContact, last_name=last_name, email=email)
        self.assertEqual(json_dump({
                             "added": [[contact.id, unicode(contact)]],
                             "value": contact.id
                         }),
                         response.content
                        )

    # TODO : test_quickform_with_custom_sync_data
    # TODO : test_add_multiple_from_widget(self)
