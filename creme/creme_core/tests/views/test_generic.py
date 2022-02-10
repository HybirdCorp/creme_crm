# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.sessions.models import Session
from django.http import Http404
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.custom_form import (
    CustomFormDescriptor,
    FieldGroup,
    FieldGroupList,
)
from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.models import (
    CremePropertyType,
    CustomFormConfigItem,
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    Imprint,
    RelationType,
    SemiFixedRelationType,
    SetCredentials,
)
from creme.creme_core.tests.fake_custom_forms import (
    FAKEACTIVITY_CREATION_CFORM,
)
from creme.creme_core.views.generic import EntityCreation

from .. import fake_forms
from .base import BrickTestCaseMixin, ViewsTestCase


class MiscTestCase(ViewsTestCase):
    def test_placeholder_view01(self):
        self.login()
        response = self.client.get(reverse('creme_core__fake_removed_view', args=[1]))
        self.assertContains(response, 'Custom error message', status_code=409)

    def test_placeholder_view02(self):
        "Not logged."
        url = reverse('creme_core__fake_removed_view', args=(1,))
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))


class DetailTestCase(ViewsTestCase, BrickTestCaseMixin):
    # TODO: factorise with tests.gui.test_misc.GuiTestCase
    class FakeRequest:
        def __init__(self, user):
            user_id = str(user.id)
            sessions = [
                d
                for d in (s.get_decoded() for s in Session.objects.all())
                if d.get('_auth_user_id') == user_id
            ]
            assert 1 == len(sessions)
            self.session = sessions[0]

    def test_entity_detail(self):
        user = self.login()
        self.assertFalse(LastViewedItem.get_all(self.FakeRequest(user)))
        self.assertFalse(Imprint.objects.all())

        fox = FakeContact.objects.create(user=user, first_name='Fox', last_name='McCloud')
        url = fox.get_absolute_url()
        self.assertPOST405(url)  # TODO: specific template for 405 errors ?

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/view_entity.html')

        # -----
        last_items = LastViewedItem.get_all(self.FakeRequest(user))
        self.assertEqual(1, len(last_items))

        last_item = last_items[0]
        self.assertEqual(fox.id,             last_item.pk)
        self.assertEqual(fox.entity_type_id, last_item.ctype_id)
        self.assertEqual(url,                last_item.url)
        self.assertEqual(str(fox),           last_item.name)

        # -----
        imprints = Imprint.objects.all()
        self.assertEqual(1, len(imprints))
        self.assertEqual(imprints[0].entity.get_real_entity(), fox)

        # -----
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, PropertiesBrick.id_)
        self.get_brick_node(tree, MODELBRICK_ID)

    def test_entity_detail_no_object(self):
        self.login()

        response = self.assertGET404(
            reverse('creme_core__view_fake_contact', args=[self.UNUSED_PK]),
        )
        self.assertTemplateUsed(response, '404.html')

    def test_entity_detail_not_super_user(self):
        user = self.login(is_superuser=False)
        fox = FakeContact.objects.create(
            user=user, first_name='Fox', last_name='McCloud',
        )
        self.assertGET200(fox.get_absolute_url())

    def test_entity_detail_not_logged(self):
        user = self.login()
        fox = FakeContact.objects.create(
            user=user, first_name='Fox', last_name='McCloud',
        )
        url = fox.get_absolute_url()

        self.client.logout()
        response = self.assertGET(302, url)
        self.assertRedirects(
            response, '{}?next={}'.format(reverse('creme_login'), url),
        )

    def test_entity_detail_permission01(self):
        "Viewing is not allowed (model credentials)."
        self.login(is_superuser=False)
        fox = FakeContact.objects.create(
            user=self.other_user, first_name='Fox', last_name='McCloud',
        )

        response = self.client.get(fox.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertContains(
            response,
            _('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=fox.id)
            ),
            status_code=403,
            html=True,
        )

    def test_entity_detail_permission02(self):
        "Viewing is not allowed (app credentials)."
        # NB: not need to create an instance, the "app" permission must be
        #     checked before the SQL query.
        self.login(is_superuser=False, allowed_apps=['creme_config'])  # Not "creme_core"

        response = self.client.get(
            reverse('creme_core__view_fake_contact', args=[self.UNUSED_PK])
        )
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertContains(
            response,
            _('You are not allowed to access to the app: {}').format(_('Core')),
            status_code=403,
            html=True,
        )


class CreationTestCase(ViewsTestCase):
    def test_entity_creation(self):
        user = self.login()

        url = reverse('creme_core__create_fake_contact')
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add.html')

        get_ctxt = response1.context.get
        self.assertIsInstance(get_ctxt('form'), fake_forms.FakeContactForm)
        self.assertEqual(_('Create a contact'), get_ctxt('title'))
        self.assertEqual(_('Save the contact'), get_ctxt('submit_label'))
        self.assertNotIn('callback_url_name', response1.context)

        count = FakeContact.objects.count()
        first_name = 'Spike'
        last_name = 'Spiegel'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(count + 1, FakeContact.objects.count())
        contact = self.get_object_or_fail(
            FakeContact, first_name=first_name, last_name=last_name,
        )
        self.assertRedirects(response2, contact.get_absolute_url())

        self.assertFalse(contact.properties.all())
        self.assertFalse(contact.relations.all())

    def test_entity_creation_validation_error(self):
        "ValidationError + cancel_url."
        user = self.login()

        url = reverse('creme_core__create_fake_contact')
        lv_url = FakeContact.get_lv_absolute_url()
        response = self.assertGET200(url, HTTP_REFERER='http://testserver' + lv_url)
        self.assertEqual(lv_url, response.context.get('cancel_url'))

        response = self.client.post(
            url, follow=True,
            data={
                'user': user.id,
                # 'last_name': name,  # NB: Missing
                'cancel_url': lv_url,
            },
        )
        self.assertFormError(response, 'form', 'last_name', _('This field is required.'))
        self.assertEqual(lv_url, response.context.get('cancel_url'))

    def test_entity_creation_permission01(self):
        "Not app credentials."
        self.login(is_superuser=False, allowed_apps=['creme_config'])

        response = self.client.get(reverse('creme_core__create_fake_contact'))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertContains(
            response,
            _('You are not allowed to access to the app: {}').format(_('Core')),
            status_code=403,
            html=True,
        )

    def test_entity_creation_permission02(self):
        "Not creation credentials."
        self.login(is_superuser=False, creatable_models=[FakeOrganisation])  # Not FakeContact

        response = self.assertGET403(reverse('creme_core__create_fake_contact'))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')

    def test_entity_creation_not_logged(self):
        url = reverse('creme_core__create_fake_contact')
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))

    def test_entity_creation_not_super_user(self):
        self.login(is_superuser=False, creatable_models=[FakeContact])
        self.assertGET200(reverse('creme_core__create_fake_contact'))

    def test_entity_creation_callback_url01(self):
        user = self.login()

        url = reverse('creme_core__create_fake_contact')
        callback_url = FakeContact.get_lv_absolute_url()
        response1 = self.assertGET200(f'{url}?callback_url={callback_url}')

        get_ctxt = response1.context.get
        self.assertEqual('callback_url', get_ctxt('callback_url_name'))
        self.assertEqual(callback_url,   get_ctxt('callback_url'))

        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'first_name': 'Spike',
                'last_name':  'Spiegel',

                'callback_url': callback_url,
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, callback_url)

    def test_entity_creation_callback_url02(self):
        "Unsafe URL."
        self.login()

        url = reverse('creme_core__create_fake_contact')

        def assertNoCallback(callback_url):
            response = self.assertGET200(f'{url}?callback_url={callback_url}')
            self.assertFalse(response.context.get('callback_url'))

        assertNoCallback('http://test.com')
        assertNoCallback('https://test.com')
        assertNoCallback('www.test.com')
        assertNoCallback('//www.test.com')

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_entity_creation_properties(self):
        user = self.login()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_smokes',  text='Smokes')
        ptype02 = create_ptype(str_pk='test-prop_glasses', text='Wears glasses')
        ptype03 = create_ptype(
            str_pk='test-prop_gun', text='Has a gun', subject_ctypes=[FakeContact],
        )
        ptype04 = create_ptype(
            str_pk='test-prop_ship', text='Is a ship', subject_ctypes=[FakeOrganisation],
        )

        ptype05 = create_ptype(str_pk='test-prop_disabled', text='Disabled')
        ptype05.enabled = False
        ptype05.save()

        url = reverse('creme_core__create_fake_contact')

        # GET ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            ptypes_choices = response1.context['form'].fields['property_types'].choices

        # Choices are sorted with 'text'
        choices = [(choice[0].value, choice[1]) for choice in ptypes_choices]
        i1 = self.assertIndex((ptype03.id, ptype03.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype02.id, ptype02.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotInChoices(ptype04.id, choices)
        self.assertNotInChoices(ptype05.id, choices)

        # POST ---
        first_name = 'Spike'
        last_name = 'Spiegel'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
                'property_types': [ptype01.id, ptype03.id],
            },
        )
        self.assertNoFormError(response2)

        contact = self.get_object_or_fail(
            FakeContact, first_name=first_name, last_name=last_name,
        )
        self.assertSetEqual(
            {ptype01, ptype03},
            {p.type for p in contact.properties.all()},
        )

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_entity_creation_relations(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Julia', last_name='??')
        contact2 = create_contact(first_name='Faye', last_name='Valentine')

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Bebop')
        orga2 = create_orga(user=user, name='Swordfish II')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loves',  'is loved'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_pilots', 'pilots',     [FakeContact]),
            ('test-object_pilots',  'is piloted', [FakeOrganisation]),
        )[0]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(
            predicate='Pilots the Swordfish',
            relation_type=rtype2,
            object_entity=orga2,
        )
        sfrt2 = create_strt(
            predicate='Loves Faye',
            relation_type=rtype1,
            object_entity=contact2,
        )

        url = reverse('creme_core__create_fake_contact')

        # GET ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertNotIn('rtypes_info', fields)
        self.assertIn('relation_types', fields)

        self.assertInChoices(value=sfrt1.id, label=sfrt1.predicate, choices=sf_choices)
        self.assertInChoices(value=sfrt2.id, label=sfrt2.predicate, choices=sf_choices)

        # POST ---
        first_name = 'Spike'
        last_name = 'Spiegel'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype1.id, contact1),
                    (rtype2.id, orga1),
                    (rtype2.id, orga1),  # Duplicates
                ),
                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertNoFormError(response2)

        subject = self.get_object_or_fail(
            FakeContact, first_name=first_name, last_name=last_name,
        )

        self.assertEqual(4, subject.relations.count())
        self.assertRelationCount(1, subject, rtype1, contact1)
        self.assertRelationCount(1, subject, rtype1, contact2)
        self.assertRelationCount(1, subject, rtype2, orga1)
        self.assertRelationCount(1, subject, rtype2, orga2)

    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_entity_creation_no_relation_field(self):
        self.login()

        response = self.assertGET200(reverse('creme_core__create_fake_contact'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('property_types',   fields)
        self.assertNotIn('rtypes_info',      fields)
        self.assertNotIn('relation_types',   fields)
        self.assertNotIn('semifixed_rtypes', fields)

    def test_entity_creation_customform01(self):
        user = self.login()

        url = reverse('creme_core__create_fake_activity')
        self.assertGET200(url)

        # TODO: test HTML

        title = 'My activity'
        place = 'Mars'
        atype = FakeActivityType.objects.first()
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':        user.id,
                'title':       title,
                'description': 'Trip on Mars',  # should not be used see FAKEACTIVITY_CFORM
                'type':        atype.id,
                'place':       place,
                # 'minutes':   ...,

                'cform_extra-fakeactivity_start': '26-08-2020',
                'cform_extra-fakeactivity_end':   '26-09-2020',
            },
        ))

        activity = self.get_object_or_fail(FakeActivity, title=title)
        self.assertEqual(title,   activity.title)
        self.assertEqual('',      activity.description)
        self.assertEqual(place,   activity.place)
        self.assertEqual(atype,   activity.type)
        self.assertEqual('',      activity.minutes)
        self.assertEqual(
            self.create_datetime(year=2020, month=8, day=26), activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2020, month=9, day=26), activity.end,
        )

    def test_entity_creation_customform02(self):
        user = self.login()

        cfci = self.get_object_or_fail(
            # CustomFormConfigItem, cform_id=FAKEACTIVITY_CREATION_CFORM.id,
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=FAKEACTIVITY_CREATION_CFORM.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='My fields',
                        cells=[
                            *(
                                build_cell(name=name)
                                for name in ('user', 'title', 'place', 'type')
                            ),
                            fake_forms.FakeActivityStartSubCell().into_cell(),
                            # fake_forms.FakeActivityEndSubCell().into_cell(),
                        ],
                    ),
                ],
            )
        )
        cfci.save()

        url = reverse('creme_core__create_fake_activity')
        self.assertGET200(url)

        # TODO: test HTML (or in model tests ?)

        title = 'My meeting'
        place = 'Mars capital'
        atype = FakeActivityType.objects.get(name='Meeting')
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':  user.id,
                'title': title,
                'place': place,
                'type':  atype.id,

                'cform_extra-fakeactivity_start': '28-09-2020',

                # Should not be used
                'cform_extra-fakeactivity_end': '30-09-2020',
                'minutes': 'Should not be used',
            },
        ))

        activity = self.get_object_or_fail(FakeActivity, title=title)
        self.assertEqual(title, activity.title)
        self.assertEqual(place, activity.place)
        self.assertEqual(atype, activity.type)
        self.assertEqual(
            self.create_datetime(year=2020, month=9, day=28), activity.start,
        )
        self.assertIsNone(activity.end)
        self.assertFalse(activity.minutes)

    def test_entity_creation_customform03(self):
        "Super-user's form."
        self.login()

        cfci = CustomFormConfigItem.objects.create(
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=True,
        )
        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=FAKEACTIVITY_CREATION_CFORM.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='My fields',
                        cells=[
                            *(
                                build_cell(name=name)
                                for name in ('user', 'title', 'place', 'type', 'minutes')
                            ),
                            fake_forms.FakeActivityStartSubCell().into_cell(),
                            fake_forms.FakeActivityEndSubCell().into_cell(),
                        ],
                    ),
                ],
            )
        )
        cfci.save()

        url = reverse('creme_core__create_fake_activity')
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn('user', fields)
        self.assertIn('minutes', fields)
        self.assertIn('cform_extra-fakeactivity_end', fields)

    def test_entity_creation_customform04(self):
        "No item exists."
        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakeorga',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        class NoItemContactCreation(EntityCreation):
            model = FakeOrganisation
            form_class = form_desc

        view = NoItemContactCreation.as_view()
        request = RequestFactory().get(reverse('creme_core__create_fake_organisation'))
        request.user = self.create_user()

        with self.assertRaises(Http404) as cm:
            view(request)

        self.assertEqual(
            _(
                'No default form has been created in DataBase for the '
                'model «{model}». Contact your administrator.'
            ).format(model='Test Organisation'),
            str(cm.exception),
        )

    def test_adding_to_entity(self):
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        url = reverse('creme_core__create_fake_address', args=(nerv.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        get_ctxt  = response.context.get
        self.assertEqual(f'Adding address to <{nerv}>', get_ctxt('title'))
        self.assertEqual(_('Save the address'),         get_ctxt('submit_label'))

        # POST ---
        city = 'Tokyo'
        self.assertNoFormError(self.client.post(url, data={'city': city}))
        self.get_object_or_fail(FakeAddress, city=city, entity=nerv.id)


class EditionTestCase(ViewsTestCase):
    def test_entity_edition(self):
        user = self.login()
        contact = FakeContact.objects.create(
            user=user, first_name='Spik', last_name='Spiege',
        )
        url = contact.get_edit_absolute_url()

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit.html')

        get_ctxt = response1.context.get
        self.assertIsInstance(get_ctxt('form'), fake_forms.FakeContactForm)
        self.assertEqual(_('Edit «{object}»').format(object=contact), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),                 get_ctxt('submit_label'))
        self.assertIsNone(get_ctxt('cancel_url', -1))
        self.assertNotIn('callback_url_name', response1.context)

        first_name = 'Spike'
        last_name = 'Spiegel'
        description = 'DESCRIPTION'

        # from creme.creme_core.utils.profiling import QueriesPrinter
        # with QueriesPrinter():
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.id,
                'first_name':  first_name,
                'last_name':   last_name,
                'description': description,
            },
        )

        self.assertNoFormError(response2)

        contact = self.refresh(contact)
        self.assertEqual(last_name,   contact.last_name)
        self.assertEqual(first_name,  contact.first_name)
        self.assertEqual(description, contact.description)

        self.assertRedirects(response2, contact.get_absolute_url())

    def test_entity_edition_no_object(self):
        "Invalid ID."
        self.login()
        self.assertGET404(reverse('creme_core__edit_fake_contact', args=[self.UNUSED_PK]))

    def test_entity_edition_validation_error(self):
        "ValidationError + cancel_url."
        user = self.login()
        contact = FakeContact.objects.create(
            user=user, first_name='Spik', last_name='Spiegel',
        )
        url = contact.get_edit_absolute_url()

        lv_url = FakeContact.get_lv_absolute_url()
        response = self.assertGET200(url, HTTP_REFERER='http://testserver' + lv_url)
        self.assertEqual(lv_url, response.context.get('cancel_url'))

        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'first_name': 'Spike',
                # 'last_name': last_name,  # NB: Missing
                'cancel_url': lv_url,
            },
        )
        self.assertFormError(response, 'form', 'last_name', _('This field is required.'))
        self.assertEqual(lv_url, response.context.get('cancel_url'))

    def test_entity_edition_permission01(self):
        "Not app credentials."
        self.login(is_superuser=False, allowed_apps=['creme_config'])

        response = self.client.get(
            reverse('creme_core__edit_fake_contact', args=[self.UNUSED_PK]),
        )
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertContains(
            response,
            _('You are not allowed to access to the app: {}').format(_('Core')),
            status_code=403,
            html=True,
        )

    def test_entity_edition_permission02(self):
        "Not edition credentials."
        self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),  # Not EntityCredentials.CHANGE
            set_type=SetCredentials.ESET_ALL,
        )

        contact = FakeContact.objects.create(
            user=self.other_user, first_name='Spike', last_name='Spiegel',
        )

        response = self.assertGET403(contact.get_edit_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')

    def test_entity_edition_not_logged(self):
        url = reverse('creme_core__edit_fake_contact', args=[self.UNUSED_PK])
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))

    def test_entity_edition_not_super_user(self):
        user = self.login(is_superuser=False)
        contact = FakeContact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        self.assertGET200(contact.get_edit_absolute_url())

    def test_entity_edition_callback_url(self):
        user = self.login()
        contact = FakeContact.objects.create(
            user=user, first_name='Spik', last_name='Spiege',
        )
        url = contact.get_edit_absolute_url()
        callback_url = FakeContact.get_lv_absolute_url()

        response1 = self.assertGET200(f'{url}?callback_url={callback_url}')

        get_ctxt = response1.context.get
        self.assertEqual('callback_url', get_ctxt('callback_url_name'))
        self.assertEqual(callback_url,   get_ctxt('callback_url'))

        # ---
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'first_name': 'Spike',
                'last_name':  'Spiegel',

                'callback_url': callback_url,
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, callback_url)

    def test_entity_edition_customform(self):
        user = self.login()

        atype1, atype2 = FakeActivityType.objects.all()[:2]
        activity = FakeActivity.objects.create(
            user=user, title='my activity', place='Mars sea', type=atype1,
        )

        url = reverse('creme_core__edit_fake_activity', args=[activity.id])
        self.assertGET200(url)

        title = activity.title.title()
        place = f'{activity.place} #2'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':  user.id,
                'title': title,

                # Should not be used ; see FAKEACTIVITY_CFORM
                'description': 'Trip on Mars',

                'type':  atype2.id,
                'place': place,

                'cform_extra-fakeactivity_start': '26-08-2020',
                'cform_extra-fakeactivity_end':   '26-09-2020',
            },
        ))

        activity = self.refresh(activity)
        self.assertEqual(title,  activity.title)
        self.assertEqual('',     activity.description)
        self.assertEqual(place,  activity.place)
        self.assertEqual(atype2, activity.type)
        self.assertEqual(
            self.create_datetime(year=2020, month=8, day=26), activity.start,
        )
        self.assertEqual(
            self.create_datetime(year=2020, month=9, day=26), activity.end,
        )

    def test_related_to_entity_edition01(self):
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        address = FakeAddress.objects.create(
            entity=nerv,
            value='26 angel street',
        )
        url = reverse('creme_core__edit_fake_address', args=[address.id])

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(f'Address for <{nerv}>',     get_ctxt('title'))
        self.assertEqual(_('Save the modifications'), get_ctxt('submit_label'))

        # ---
        city = 'Tokyo'
        value = address.value + ' (edited)'
        response = self.client.post(url, data={'value': value, 'city': city})
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(nerv.id, address.entity_id)
        self.assertEqual(value,   address.value)
        self.assertEqual(city,     address.city)

    def test_related_to_entity_edition02(self):
        "Edition credentials on related entity needed."
        user = self.login(is_superuser=False)

        nerv = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        self.assertFalse(user.has_perm_to_change(nerv))

        address = FakeAddress.objects.create(
            entity=nerv,
            value='26 angel street',
        )
        url = reverse('creme_core__edit_fake_address', args=(address.id,))

        response = self.client.get(url)
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertContains(
            response,
            _('You are not allowed to edit this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=nerv.id)
            ),
            status_code=403,
            html=True,
        )

        # ---
        nerv.user = user
        nerv.save()
        self.assertGET200(url)
