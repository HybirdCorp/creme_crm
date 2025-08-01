from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.models import (
    CremeEntity,
    FakeContact,
    FakeDocument,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    Sandbox,
)
from creme.creme_core.tests.base import CremeTestCase


class EntityViewsTestCase(CremeTestCase):
    CLONE_URL    = reverse('creme_core__clone_entity')
    RESTRICT_URL = reverse('creme_core__restrict_entity_2_superusers')

    def test_json_entity_get01(self):
        user = self.login_as_root_and_get()
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        url = reverse('creme_core__entity_as_json', args=(rei.id,))
        self.assertGET(400, url)

        response = self.assertGET200(url, data={'fields': ['id']})
        self.assertEqual([[rei.id]], response.json())

        response = self.assertGET200(url, data={'fields': ['unicode']})
        self.assertListEqual([[str(rei)]], response.json())

        response = self.assertGET200(
            reverse('creme_core__entity_as_json', args=(nerv.id,)),
            data={'fields': ['id', 'unicode']},
        )
        self.assertEqual([[nerv.id, str(nerv)]], response.json())

        self.assertGET(400, reverse('creme_core__entity_as_json', args=(self.UNUSED_PK,)))
        self.assertGET403(url, data={'fields': ['id', 'unknown']})

    def test_json_entity_get02(self):
        self.login_as_standard()

        nerv = FakeOrganisation.objects.create(user=self.get_root_user(), name='Nerv')
        self.assertGET(400, reverse('creme_core__entity_as_json', args=(nerv.id,)))

    def test_json_entity_get03(self):
        "No credentials for the basic CremeEntity, but real entity is viewable."
        user = self.login_as_standard(
            allowed_apps=['creme_config'],  # Not 'creme_core'
            creatable_models=[FakeConfigEntity],
        )
        self.add_credentials(user.role, all=['VIEW'])

        e = FakeConfigEntity.objects.create(user=user, name='Nerv')
        response = self.assertGET200(
            reverse('creme_core__entity_as_json', args=(e.id,)),
            data={'fields': ['unicode']},
        )
        self.assertListEqual([[str(e)]], response.json())

    def test_get_creme_entities_repr01(self):
        user = self.login_as_root_and_get()

        with self.assertNoException():
            entity = CremeEntity.objects.create(user=user)

        response = self.assertGET200(
            reverse('creme_core__entities_summaries', args=(entity.id,)),
        )
        self.assertEqual('application/json', response['Content-Type'])

        self.assertListEqual(
            [{
                'id':   entity.id,
                'text': f'Creme entity: {entity.id}',
            }],
            response.json(),
        )

    def test_get_creme_entities_repr02(self):
        "Several entities, several ContentTypes, credentials."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        create_c = FakeContact.objects.create
        rei   = create_c(user=user,                 first_name='Rei',   last_name='Ayanami')
        asuka = create_c(user=user,                 first_name='Asuka', last_name='<b>Langley</b>')
        mari  = create_c(user=self.get_root_user(), first_name='Mari',  last_name='Makinami')

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertTrue(user.has_perm_to_view(rei))
        self.assertFalse(user.has_perm_to_view(mari))

        unknown_id = self.UNUSED_PK
        self.assertFalse(CremeEntity.objects.filter(id=unknown_id))

        response = self.assertGET200(reverse(
            'creme_core__entities_summaries',
            args=(f'{mari.id},{rei.id},{nerv.id},{unknown_id},{asuka.id}',),
        ))

        self.assertListEqual(
            [
                {'id': mari.id,  'text': _('Entity #{id} (not viewable)').format(id=mari.id)},
                {'id': rei.id,   'text': str(rei)},
                {'id': nerv.id,  'text': str(nerv)},
                {'id': asuka.id, 'text': 'Asuka &lt;b&gt;Langley&lt;/b&gt;'},
            ],
            response.json(),
        )

    def test_get_sanitized_html_field(self):
        user = self.login_as_root_and_get()
        entity = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertGET409(
            reverse('creme_core__sanitized_html_field', args=(entity.id, 'unknown')),
        )

        # Not an UnsafeHTMLField
        self.assertGET409(
            reverse('creme_core__sanitized_html_field', args=(entity.id, 'name')),
        )

        # NB: test with valid field in 'emails' app.

    @staticmethod
    def _build_test_get_info_fields_url(model):
        ct = ContentType.objects.get_for_model(model)

        return reverse('creme_core__entity_info_fields', args=(ct.id,))

    def test_get_info_fields01(self):
        self.login_as_root()

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeContact))
        json_data = response.json()
        self.assertIsList(json_data)
        self.assertTrue(all(isinstance(elt, list) for elt in json_data))
        self.assertTrue(all(len(elt) == 2 for elt in json_data))
        self.assertCountEqual(
            [
                'created', 'modified', 'first_name', 'last_name', 'description',
                'phone', 'mobile', 'email', 'birthday', 'url_site',
                'is_a_nerd', 'loves_comics',
            ],
            [name for name, vname in json_data],
        )

        json_dict = dict(json_data)
        self.assertEqual(_('First name'), json_dict['first_name'])
        self.assertEqual(
            _('{field} [CREATION]').format(field=_('Last name')),
            json_dict['last_name'],
        )

    def test_get_info_fields02(self):
        self.login_as_root()

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeOrganisation))
        json_data = response.json()
        self.assertCountEqual(
            [
                'created', 'modified', 'name', 'description', 'url_site',
                'phone', 'email', 'creation_date', 'subject_to_vat', 'capital',
            ],
            [name for name, vname in json_data],
        )

        json_dict = dict(json_data)
        self.assertEqual(_('Description'), json_dict['description'])
        self.assertEqual(
            _('{field} [CREATION]').format(field=_('Name')),
            json_dict['name'],
        )

    def test_get_info_fields__several_required_fields(self):
        self.login_as_root()

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeDocument))
        json_data = response.json()
        self.assertCountEqual(
            ['created', 'modified', 'title', 'description', 'filedata'],
            [name for name, vname in json_data],
        )

        json_dict = dict(json_data)
        self.assertEqual(_('Title'), json_dict['title'])
        self.assertEqual(_('File'), json_dict['filedata'])

    def test_get_info_fields__fieldsconfig(self):
        self.login_as_root()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('birthday', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeContact))
        json_data = response.json()
        names = [
            'created', 'modified', 'first_name', 'last_name', 'description',
            'phone', 'mobile', 'email', 'url_site', 'is_a_nerd', 'loves_comics',
            # 'birthday', #<===
        ]
        self.assertFalse({*names}.symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

    def test_clone(self):
        user = self.login_as_root_and_get()
        url = self.CLONE_URL

        first_name = 'Mario'
        mario = FakeContact.objects.create(user=user, first_name=first_name, last_name='Bros')
        count = FakeContact.objects.count()

        self.assertPOST404(url, data={})
        self.assertPOST404(url, data={'id': 0})
        self.assertEqual(count, FakeContact.objects.count())

        # ---
        response = self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertEqual(count + 1, FakeContact.objects.count())

        with self.assertNoException():
            mario, oiram = FakeContact.objects.filter(first_name=first_name).order_by('created')

        self.assertEqual(mario.last_name, oiram.last_name)
        self.assertRedirects(response, oiram.get_absolute_url())

    def test_clone__not_logged(self):
        url = self.CLONE_URL

        mario = FakeContact.objects.create(
            user=self.get_root_user(),
            first_name='Mario', last_name='Bros',
        )

        response = self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertRedirects(
            response, reverse(settings.LOGIN_URL, query={'next': url}),
        )

    def test_clone__standard_user(self):
        "Not superuser with right credentials."
        user = self.login_as_standard(creatable_models=[FakeContact])
        self.add_credentials(user.role, all='*')

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertPOST200(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone__creation_perm(self):
        "Not superuser without creation credentials => error."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='*')

        mario = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Mario', last_name='Bros',
        )
        count = FakeContact.objects.count()
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count, FakeContact.objects.count())

    def test_clone__view_perm(self):
        "Not superuser without VIEW credentials => error."
        user = self.login_as_standard(creatable_models=[FakeContact])
        self.add_credentials(user.role, all='!VIEW')

        mario = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Mario', last_name='Bros',
        )
        count = FakeContact.objects.count()
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count, FakeContact.objects.count())

    def test_clone__not_clonable(self):
        """Not clonable entity type."""
        user = self.login_as_root_and_get()

        image = FakeImage.objects.create(user=user, name='Img1')
        count = FakeImage.objects.count()
        self.assertPOST409(self.CLONE_URL, data={'id': image.id}, follow=True)
        self.assertEqual(count, FakeImage.objects.count())

    def test_clone__ajax(self):
        user = self.login_as_root_and_get()

        first_name = 'Mario'
        mario = FakeContact.objects.create(
            user=user, first_name=first_name, last_name='Bros',
        )
        count = FakeContact.objects.count()

        response = self.assertPOST200(
            self.CLONE_URL,
            data={'id': mario.id}, follow=True,
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertEqual(count + 1, FakeContact.objects.count())

        with self.assertNoException():
            mario, oiram = FakeContact.objects.filter(
                first_name=first_name,
            ).order_by('created')

        self.assertEqual(mario.last_name, oiram.last_name)
        self.assertEqual(oiram.get_absolute_url(), response.text)

    def test_restrict_entity_2_superusers01(self):
        user = self.login_as_root_and_get()
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )

        url = self.RESTRICT_URL
        data = {'id': contact.id}
        self.assertGET405(url, data=data)
        self.assertPOST200(url, data=data)

        sandbox = self.refresh(contact).sandbox
        self.assertIsNotNone(sandbox)
        self.assertUUIDEqual(constants.UUID_SANDBOX_SUPERUSERS, sandbox.uuid)

        # Unset
        self.assertPOST200(url, data={**data, 'set': 'false'})
        self.assertIsNone(self.refresh(contact).sandbox)

    def test_restrict_entity_2_superusers02(self):
        "Entity already in a sandbox."
        user = self.login_as_root_and_get()
        sandbox = Sandbox.objects.create(type_id='creme_core-dont_care', user=user)
        contact = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Eikichi', last_name='Onizuka',
        )

        data = {'id': contact.id}
        self.assertPOST409(self.RESTRICT_URL, data=data)
        self.assertPOST409(self.RESTRICT_URL, data={**data, 'set': 'false'})

        self.assertEqual(sandbox, self.refresh(contact).sandbox)

    def test_restrict_entity_2_superusers03(self):
        "Unset entity with no sandbox."
        user = self.login_as_root_and_get()
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )
        self.assertPOST409(self.RESTRICT_URL, data={'id': contact.id, 'set': 'false'})

    def test_restrict_entity_2_superusers04(self):
        "Not super-user."
        user = self.login_as_standard()
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )
        self.assertPOST403(self.RESTRICT_URL, data={'id': contact.id})
