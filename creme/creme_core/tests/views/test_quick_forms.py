# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from .base import CremeTestCase

    from ..fake_models import FakeContact, FakeOrganisation, FakeInvoice
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class QuickFormTestCase(CremeTestCase):
    def quickform_data(self, count):
        return {'form-INITIAL_FORMS':  '0',
                'form-MAX_NUM_FORMS':  '',
                'form-TOTAL_FORMS':    str(count),
                'csrfmiddlewaretoken': '08b8b225c536b4fd25d16f5ed8be3839',
               }

    def quickform_data_append_contact(self, data, id, first_name='', last_name='', email='', organisation='', phone=''):
        return data.update({
            f'form-{id}-email':        email,
            f'form-{id}-last_name':    last_name,
            f'form-{id}-first_name':   first_name,
            f'form-{id}-organisation': organisation,
            f'form-{id}-phone':        phone,
            f'form-{id}-user':         self.user.id,
        })

    def _build_quickform_url(self, model):
        return reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(model).pk,))

    def test_quickform01(self):
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
                                           }
                                     )
        self.assertEqual(count + 1, FakeContact.objects.count())

        contact = self.get_object_or_fail(FakeContact, last_name=last_name, email=email)
        self.assertEqual({'added': [[contact.id, str(contact)]],
                          'value': contact.id,
                         },
                         response.json()
                        )

    def test_quickform02(self):
        "Not super-user."
        self.login(is_superuser=False, creatable_models=[FakeOrganisation])
        self.assertGET200(self._build_quickform_url(FakeOrganisation))

    def test_quickform03(self):
        "Creation permission needed."
        self.login(is_superuser=False, creatable_models=[FakeContact])
        self.assertGET403(self._build_quickform_url(FakeOrganisation))

    def test_quickform04(self):
        "Model without form."
        self.login()
        self.assertGET404(self._build_quickform_url(FakeInvoice))

    # TODO : test_quickform_with_custom_sync_data
    # TODO : test_add_multiple_from_widget(self)
