from functools import partial

from django.forms import IntegerField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomField,
    Relation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.mobile.bricks import FavoritePersonsBrick
from creme.mobile.models import MobileFavorite
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .base import Contact, MobileBaseTestCase, Organisation


class MobilePersonsTestCase(BrickTestCaseMixin, MobileBaseTestCase):
    PERSONS_PORTAL_URL = reverse('mobile__directory')
    CREATE_CONTACT_URL = reverse('mobile__create_contact')
    CREATE_ORGA_URL    = reverse('mobile__create_organisation')
    SEARCH_PERSON_URL  = reverse('mobile__search_person')

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_persons(self):
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        may = create_contact(first_name='May', last_name='Shiranui')
        joe = create_contact(first_name='Joe', last_name='Higashi')
        terry = create_contact(first_name='Terry', last_name='Bogard')
        create_contact(first_name='Andy', last_name='Bogard')

        create_orga = partial(Organisation.objects.create, user=user)
        kof = create_orga(name='KingOfFighters')
        create_orga(name='Fatal fury')

        create_fav = partial(MobileFavorite.objects.create, user=user)
        create_fav(entity=may)
        create_fav(entity=joe)
        create_fav(entity=kof)
        create_fav(entity=terry, user=self.create_user())

        response = self.assertGET200(self.PERSONS_PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/directory.html')

        with self.assertNoException():
            contacts = {*response.context['favorite_contacts']}
            orgas = [*response.context['favorite_organisations']]

        self.assertSetEqual({may, joe}, contacts)
        self.assertContains(response, may.last_name)
        self.assertContains(response, may.first_name)

        self.assertListEqual([kof], orgas)
        self.assertContains(response, kof)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_create_contact01(self):
        user = self.login_as_root_and_get()

        url = self.CREATE_CONTACT_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/add_contact.html')

        kof = Organisation.objects.create(user=user, name='KOF')
        first_name = 'May'
        last_name = 'Shiranui'
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,
                'organisation': kof.name,
            },
        )
        self.assertNoFormError(response)

        may = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
        )
        self.assertEqual(user, may.user)
        self.assertHaveRelation(subject=may, type=REL_SUB_EMPLOYED_BY, object=kof)
        self.assertFalse(user.mobile_favorite.all())

        self.assertRedirects(response, self.PERSONS_PORTAL_URL)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_create_contact02(self):
        user = self.login_as_root_and_get()
        first_name = 'May'
        last_name = 'Shiranui'

        url = self.CREATE_CONTACT_URL
        arg = {'last_name': first_name}
        response = self.assertGET200(url, data=arg)
        self.assertEqual(arg, self.get_form_or_fail(response).initial)

        orga_name = 'KOF'
        self.assertFalse(Organisation.objects.filter(name=orga_name))

        phone = '111111'
        mobile = '222222'
        email = 'may.shiranui@kof.org'
        other_user = self.create_user()
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user': other_user.id,
                'first_name': first_name,
                'last_name': last_name,
                'organisation': orga_name,
                'phone': phone,
                'mobile': mobile,
                'email': email,
                'is_favorite': True,
            },
        )
        self.assertNoFormError(response)

        may = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
        )
        self.assertEqual(other_user, may.user)
        self.assertEqual(phone, may.phone)
        self.assertEqual(mobile, may.mobile)
        self.assertEqual(email, may.email)

        kof = self.get_object_or_fail(Organisation, name=orga_name)
        self.assertHaveRelation(subject=may, type=REL_SUB_EMPLOYED_BY, object=kof)

        self.assertListEqual(
            [may],
            [f.entity.get_real_entity() for f in user.mobile_favorite.all()]
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_create_contact03(self):
        user = self.login_as_root_and_get()

        name = 'HP'
        create_cf = partial(CustomField.objects.create, content_type=Contact)
        cfield1 = create_cf(field_type=CustomField.STR, name='Special attacks')
        cfield2 = create_cf(field_type=CustomField.INT, name=name, is_required=True)

        url = self.CREATE_CONTACT_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/add_contact.html')

        with self.assertNoException():
            fields = response.context['form'].fields
            cfield_f2 = fields[f'custom_field-{cfield2.id}']

        self.assertNotIn(f'custom_field-{cfield1.id}', fields)
        self.assertIsInstance(cfield_f2, IntegerField)

        self.assertContains(
            response,
            f'id="id_custom_field-{cfield2.id}"',
        )
        self.assertContains(
            response,
            f'<label class="field-label" for="id_custom_field-{cfield2.id}">{name}',
        )

        first_name = 'May'
        last_name = 'Shiranui'
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,
                f'custom_field-{cfield2.id}': 150,
            },
        )
        self.assertNoFormError(response)

        may = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(
            150,
            cfield2.value_class.objects.get(custom_field=cfield2.id, entity=may.id).value
        )

    def test_create_contact_error01(self):
        "Not logged."
        url = self.CREATE_CONTACT_URL
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('mobile__login'), url))

    def test_create_contact_error02(self):
        "Not allowed."
        self.login_as_mobile_user(creatable_models=[Organisation])

        response = self.assertGET403(self.CREATE_CONTACT_URL)
        self.assertTemplateUsed(response, 'mobile/error.html')
        self.assertEqual(
            response.context['msg'],
            _('You do not have access to this page, please contact your administrator.')
        )

    def test_create_contact_error03(self):
        "Not super-user."
        self.login_as_mobile_user(creatable_models=[Contact])
        self.assertGET200(self.CREATE_CONTACT_URL)

    @skipIfCustomOrganisation
    def test_create_orga01(self):
        user = self.login_as_root_and_get()

        url = self.CREATE_ORGA_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/add_orga.html')

        name = 'KOF'
        phone = '111111'
        response = self.assertPOST200(
            url, follow=True,
            data={
                'user': user.id,
                'name':  name,
                'phone': phone,
            },
        )
        self.assertNoFormError(response)

        kof = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(user,  kof.user)
        self.assertEqual(phone, kof.phone)
        self.assertFalse(user.mobile_favorite.all())

        self.assertRedirects(response, self.PERSONS_PORTAL_URL)

    @skipIfCustomOrganisation
    def test_create_orga02(self):
        user = self.login_as_root_and_get()
        name = 'Fatal Fury Inc.'
        other_user = self.create_user()

        url = self.CREATE_ORGA_URL
        arg = {'name': name}
        response = self.assertGET200(url, data=arg)
        self.assertEqual(arg, self.get_form_or_fail(response).initial)

        response = self.assertPOST200(
            url, follow=True,
            data={
                'user': other_user.id,
                'name': name,
                'is_favorite':  True,
            },
        )
        self.assertNoFormError(response)

        ff = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(other_user, ff.user)
        self.assertListEqual(
            [ff],
            [f.entity.get_real_entity() for f in user.mobile_favorite.all()]
        )

    @skipIfCustomOrganisation
    def test_create_orga03(self):
        user = self.login_as_root_and_get()

        cf_name = 'Prize'
        create_cf = partial(CustomField.objects.create, content_type=Organisation)
        cfield1 = create_cf(field_type=CustomField.STR, name='Baseline')
        cfield2 = create_cf(field_type=CustomField.INT, name=cf_name, is_required=True)

        url = self.CREATE_ORGA_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/add_orga.html')

        with self.assertNoException():
            fields = response.context['form'].fields
            cfield_f2 = fields[f'custom_field-{cfield2.id}']

        self.assertNotIn(f'custom_field-{cfield1.id}', fields)
        self.assertIsInstance(cfield_f2, IntegerField)

        self.assertContains(
            response,
            f'id="id_custom_field-{cfield2.id}"'
        )
        self.assertContains(
            response,
            f'<label class="field-label" for="id_custom_field-{cfield2.id}">{cfield2.name}'
        )

        name = 'Fatal Fury Inc.'
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
                f'custom_field-{cfield2.id}': 150,
            },
        )
        self.assertNoFormError(response)

        ffinc = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(
            150,
            cfield2.value_class.objects.get(custom_field=cfield2.id, entity=ffinc.id).value,
        )

    def test_create_orga_error01(self):
        "Not logged."
        url = self.CREATE_ORGA_URL
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('mobile__login'), url))

    def test_create_orga_error02(self):
        self.login_as_mobile_user(creatable_models=[Contact])

        response = self.assertGET403(self.CREATE_ORGA_URL)
        self.assertTemplateUsed(response, 'mobile/error.html')
        self.assertEqual(
            response.context['msg'],
            _('You do not have access to this page, please contact your administrator.')
        )

    def test_search_persons01(self):
        self.login_as_root()
        url = self.SEARCH_PERSON_URL

        self.assertGET404(url)
        self.assertGET409(url, data={'search': 'Ik'})

        response = self.assertGET200(url, data={'search': 'Ikari'})
        self.assertTemplateUsed(response, 'mobile/search.html')

        with self.assertNoException():
            ctxt = response.context
            contacts = ctxt['contacts']
            orgas    = ctxt['organisations']

        self.assertEqual(0, len(contacts))
        self.assertEqual(0, len(orgas))

    @skipIfCustomContact
    def test_search_persons02(self):
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Rei',   last_name='Ayanami')
        create_contact(first_name='Asuka', last_name='Langley')
        shinji = create_contact(first_name='Shinji', last_name='Ikari', mobile='559966')
        gendo  = create_contact(first_name='Gendo',  last_name='Ikari')
        ikari  = create_contact(first_name='Ikari',  last_name='Warrior')

        response = self.assertGET200(self.SEARCH_PERSON_URL, data={'search': 'Ikari'})

        with self.assertNoException():
            contacts = {*response.context['contacts']}

        self.assertSetEqual({shinji, gendo, ikari}, contacts)
        self.assertContains(response, shinji.first_name)
        self.assertContains(response, shinji.mobile)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_search_persons03(self):
        "Search in organisations which employ ('employed by')."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        kof = create_orga(name='KingOfFighters')
        ff = create_orga(name='Fatal fury')

        create_contact = partial(Contact.objects.create, user=user)
        may = create_contact(first_name='May', last_name='Shiranui')
        create_contact(first_name='Asuka', last_name='Langley')

        create_rel = partial(
            Relation.objects.create,
            type_id=REL_SUB_EMPLOYED_BY, user=user,
        )
        create_rel(subject_entity=may, object_entity=kof)
        create_rel(subject_entity=may, object_entity=ff)  # Can cause duplicates

        url = self.SEARCH_PERSON_URL
        context = self.assertGET200(url, data={'search': kof.name.lower()[1:6]}).context
        self.assertListEqual([may], [*context['contacts']])
        self.assertListEqual([kof], [*context['organisations']])

        response = self.assertGET200(url, data={'search': may.last_name[:4]})
        self.assertListEqual([may], [*response.context['contacts']])

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_search_persons04(self):
        "Search in organisations which employ ('managed by')."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        kof = create_orga(name='KingOfFighters')
        create_orga(name='Fatal fury')

        create_contact = partial(Contact.objects.create, user=user)
        may = create_contact(first_name='May', last_name='Shiranui')
        create_contact(first_name='Asuka', last_name='Langley')

        Relation.objects.create(
            subject_entity=may, object_entity=kof,
            type_id=REL_SUB_MANAGES, user=user,
        )

        response = self.assertGET200(
            self.SEARCH_PERSON_URL,
            data={'search': kof.name.lower()[1:6]},
        )
        self.assertListEqual([may], [*response.context['contacts']])

    @skipIfCustomContact
    def test_mark_as_favorite(self):
        user = self.login_as_root_and_get()
        may = Contact.objects.create(
            user=user, first_name='May', last_name='Shiranui',
        )

        url = reverse('mobile__mark_as_favorite', args=(may.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.get_object_or_fail(MobileFavorite, entity=may, user=user)

        self.assertPOST200(url)
        self.get_object_or_fail(MobileFavorite, entity=may, user=user)  # Not 2 objects

    @skipIfCustomContact
    def test_unmark_favorite(self):
        user = self.login_as_root_and_get()
        may = Contact.objects.create(
            user=user, first_name='May', last_name='Shiranui',
        )
        fav = MobileFavorite.objects.create(entity=may, user=user)

        url = reverse('mobile__unmark_favorite', args=(may.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertDoesNotExist(fav)

    @skipIfCustomContact
    def test_favorite_brick01(self):
        user = self.login_as_root_and_get()
        may = Contact.objects.create(
            user=user, first_name='May', last_name='Shiranui',
        )
        MobileFavorite.objects.create(entity=may, user=user)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=FavoritePersonsBrick,
            order=1,
            zone=BrickDetailviewLocation.TOP,
            model=Contact,
        )

        response = self.assertGET200(may.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=FavoritePersonsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='This contact is a favorite for {count} user',
            plural_title='This contact is a favorite for {count} users',
        )

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasNoButton(
            buttons_node,
            url=reverse('mobile__mark_as_favorite', args=(may.id,)),
        )

    @skipIfCustomContact
    def test_favorite_brick02(self):
        "Favorite of another user."
        user = self.login_as_root_and_get()
        may = Contact.objects.create(
            user=user, first_name='May', last_name='Shiranui',
        )
        MobileFavorite.objects.create(entity=may, user=self.create_user())

        BrickDetailviewLocation.objects.create_if_needed(
            brick=FavoritePersonsBrick,
            order=1,
            zone=BrickDetailviewLocation.TOP,
            model=Contact,
        )

        response = self.assertGET200(may.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=FavoritePersonsBrick,
        )

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasButton(
            buttons_node,
            url=reverse('mobile__mark_as_favorite', args=(may.id,)),
            label=_('Mark as favorite'),
        )

    @skipIfCustomOrganisation
    def test_favorite_brick03(self):
        "Organisation case."
        user = self.login_as_root_and_get()
        kof = Organisation.objects.create(user=user, name='KingOfFighters')
        MobileFavorite.objects.create(entity=kof, user=user)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=FavoritePersonsBrick,
            order=1,
            zone=BrickDetailviewLocation.TOP,
            model=Organisation,
        )

        response = self.assertGET200(kof.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=FavoritePersonsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='This organisation is a favorite for {count} user',
            plural_title='This organisation is a favorite for {count} users',
        )

# TODO: search with smart word splitting ? special chars like " ??
