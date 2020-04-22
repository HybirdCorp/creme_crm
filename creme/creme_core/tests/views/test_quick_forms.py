# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.forms import IntegerField
    from django.urls import reverse

    from .base import CremeTestCase

    from creme.creme_core.models import (
        CustomField,
        FakeContact, FakeOrganisation, FakeInvoice,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class QuickFormTestCase(CremeTestCase):
    @staticmethod
    # def quickform_data(self, count):
    def quickform_data(count):
        return {
            'form-INITIAL_FORMS':  '0',
            'form-MAX_NUM_FORMS':  '',
            'form-TOTAL_FORMS':    str(count),
            'csrfmiddlewaretoken': '08b8b225c536b4fd25d16f5ed8be3839',
        }

    def quickform_data_append_contact(self, data, id, first_name='', last_name='',
                                      email='', organisation='', phone=''):
        return data.update({
            f'form-{id}-email':        email,
            f'form-{id}-last_name':    last_name,
            f'form-{id}-first_name':   first_name,
            f'form-{id}-organisation': organisation,
            f'form-{id}-phone':        phone,
            f'form-{id}-user':         self.user.id,
        })

    def _build_quickform_url(self, model):
        return reverse('creme_core__quick_form',
                       args=(ContentType.objects.get_for_model(model).pk,),
                      )

    def test_ok01(self):
        user = self.login()
        count = FakeContact.objects.count()

        url = self._build_quickform_url(FakeContact)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(FakeContact.creation_label, context.get('title'))
        self.assertEqual(FakeContact.save_label,     context.get('submit_label'))

        # ---
        last_name = 'Kirika'
        email = 'admin@hello.com'
        response = self.assertPOST200(url,
                                      data={'last_name': last_name,
                                            'email':     email,
                                            'user':      user.id,
                                           },
                                     )
        self.assertEqual(count + 1, FakeContact.objects.count())

        contact = self.get_object_or_fail(FakeContact, last_name=last_name, email=email)
        self.assertDictEqual(
            {'added': [[contact.id, str(contact)]],
             'value': contact.id,
            },
            response.json()
        )

    def test_ok02(self):
        "Not super-user."
        self.login(is_superuser=False, creatable_models=[FakeOrganisation])
        self.assertGET200(self._build_quickform_url(FakeOrganisation))

    def test_error01(self):
        "Creation permission needed."
        self.login(is_superuser=False, creatable_models=[FakeContact])
        self.assertGET403(self._build_quickform_url(FakeOrganisation))

    def test_error02(self):
        "Model without form."
        self.login()
        self.assertGET404(self._build_quickform_url(FakeInvoice))

    def test_customfields(self):
        user = self.login()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cf1 = create_cf(field_type=CustomField.STR, name='Dogtag')
        cf2 = create_cf(field_type=CustomField.INT, name='Eva number', is_required=True)

        url = self._build_quickform_url(FakeContact)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn(f'custom_field_{cf1.id}', fields)

        cf2_f = fields.get(f'custom_field_{cf2.id}')
        self.assertIsInstance(cf2_f, IntegerField)
        self.assertTrue(cf2_f.required)

        # ---
        first_name = 'Rei'
        last_name = 'Ayanami'
        response = self.client.post(url,
                                    data={
                                        'last_name':  last_name,
                                        'first_name': first_name,
                                        'user':       user.id,
                                        f'custom_field_{cf2.id}': 3,
                                    },
                                   )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(FakeContact,
                                          last_name=last_name,
                                          first_name=first_name,
                                         )

        with self.assertNoException():
            cf_value = cf2.value_class.objects.get(custom_field=cf2,
                                                   entity=contact,
                                                  ).value

        self.assertEqual(3, cf_value)

    # TODO: test_quickform_with_custom_sync_data
