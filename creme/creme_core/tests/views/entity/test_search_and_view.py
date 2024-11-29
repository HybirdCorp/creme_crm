from functools import partial
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.urls import reverse

from creme.creme_core.models import FakeContact, FakeOrganisation, FieldsConfig
from creme.creme_core.tests.base import CremeTestCase


class SearchAndViewTestCase(CremeTestCase):
    SEARCHNVIEW_URL  = reverse('creme_core__search_n_view_entities')

    def assertDetailview(self, response, entity):
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, entity.get_absolute_url())

    def test_value_error(self):
        self.login_as_root()

        url = self.SEARCHNVIEW_URL
        data = {'models': 'creme_core-fakecontact', 'fields': 'phone'}
        response1 = self.client.get(url, data=data)
        self.assertContains(
            response1,
            text='No GET argument with this key: &quot;value&quot;',
            status_code=404,
        )

        # ---
        response2 = self.client.get(url, data={**data, 'value': ''})
        self.assertContains(
            response2, text='Void &quot;value&quot; arg', status_code=404,
        )

    def test_one_model_one_field(self):
        user = self.login_as_root_and_get()

        phone = '123456789'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone',
            'value':  phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654', mobile=phone)
        self.assertGET404(url, data=data)

        onizuka.phone = phone
        onizuka.save()
        self.assertPOST405(url, data=data)
        self.assertDetailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_one_model_two_fields(self):
        user = self.login_as_root_and_get()

        phone = '999999999'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone,mobile',
            'value':  phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka  = create_contact(first_name='Eikichi', last_name='Onizuka', mobile=phone)
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')
        self.assertDetailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_two_models_two_fields(self):
        user = self.login_as_root_and_get()

        phone = '696969'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'phone,mobile',
            'value': phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')

        onibaku = FakeOrganisation.objects.create(user=user, name='Onibaku', phone=phone)
        self.assertDetailview(self.client.get(url, data=data, follow=True), onibaku)

        onizuka.mobile = phone
        onizuka.save()
        self.assertDetailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_errors(self):
        user = self.login_as_root_and_get()

        url = self.SEARCHNVIEW_URL
        base_data = {
            'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'mobile,phone',
            'value':  '696969',
        }
        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma', phone='987654')
        FakeOrganisation.objects.create(user=user, name='Onibaku', phone='54631357')

        self.assertGET404(url, data={**base_data, 'models': 'foo-bar'})
        self.assertGET404(url, data={**base_data, 'models': 'foobar'})
        self.assertGET404(url, data={**base_data, 'values': ''})
        self.assertGET404(url, data={**base_data, 'models': ''})
        self.assertGET404(url, data={**base_data, 'fields': ''})
        # Not CremeEntity
        self.assertGET404(url, data={**base_data, 'models': 'persons-civility'})

    def test_credentials(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        phone = '44444'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'phone,mobile',
            'value':  phone,
        }

        create_contact = FakeContact.objects.create
        # Phone is OK but not readable
        onizuka = create_contact(
            user=self.get_root_user(), first_name='Eikichi', last_name='Onizuka', mobile=phone,
        )
        # Phone is KO
        ryuji = create_contact(
            user=user, first_name='Ryuji', last_name='Danma', phone='987654',
        )

        onibaku = FakeOrganisation.objects.create(
            user=user, name='Onibaku', phone=phone,
        )  # Phone OK and readable

        has_perm = user.has_perm_to_view
        self.assertFalse(has_perm(onizuka))
        self.assertTrue(has_perm(ryuji))
        self.assertTrue(has_perm(onibaku))
        self.assertDetailview(self.client.get(url, data=data, follow=True), onibaku)

    def test_app_credentials(self):
        user = self.login_as_standard(allowed_apps=['documents'])  # Not 'creme_core'

        phone = '31337'
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone',
            'value':  phone,
        }
        # Would match if apps was allowed
        FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka', phone=phone,
        )
        self.assertGET403(self.SEARCHNVIEW_URL, data=data)

    def test_fields_config(self):
        "Phone field is hidden."
        self.login_as_root()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone',  {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(
            self.SEARCHNVIEW_URL,
            data={
                'models': 'creme_core-fakecontact',
                'fields': 'phone',
                'value':  '123456789',
            },
        )

    def test_not_logged(self):
        url = self.SEARCHNVIEW_URL
        models = 'creme_core-fakecontact'
        fields = 'phone'
        value = '123456789'
        response = self.assertGET200(
            url, follow=True,
            data={
                'models': models,
                'fields': fields,
                'value':  value,
            },
        )
        # NB: problem with order (only python3.5- ?)
        # self.assertRedirects(
        #     response,
        #     '{login_url}?next={search_url}'
        #     '%3Fmodels%3Dcreme_core-fakecontact'
        #     '%26fields%3Dphone'
        #     '%26value%3D123456789'.format(
        #         login_url=reverse(settings.LOGIN_URL),
        #         search_url=url,
        #     )
        # )
        self.assertEqual(1, len(response.redirect_chain))

        parsed_url = urlparse(response.redirect_chain[0][0])
        self.assertEqual(reverse(settings.LOGIN_URL), parsed_url.path)

        next_param = parsed_url.query
        self.assertStartsWith(next_param, 'next=')
        self.assertURLEqual(
            f'{url}?models={models}&fields={fields}&value={value}',
            unquote(next_param.removeprefix('next=')),
        )
