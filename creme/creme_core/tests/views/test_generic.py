# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.sessions.models import Session
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.html import escape
    from django.utils.translation import gettext as _

    from .base import ViewsTestCase, BrickTestCaseMixin
    from .. import fake_forms

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.bricks import PropertiesBrick
    from creme.creme_core.constants import MODELBRICK_ID
    from creme.creme_core.gui.last_viewed import LastViewedItem
    from creme.creme_core.models import (SetCredentials, Imprint,
            CremePropertyType, RelationType, SemiFixedRelationType,
            FakeOrganisation, FakeContact, FakeAddress)
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class MiscTestCase(ViewsTestCase):
    def test_placeholder_view01(self):
        self.login()
        response = self.client.get(reverse('creme_core__fake_removed_view', args=(1,)))
        self.assertContains(response, 'Custom error message', status_code=409)

    def test_placeholder_view02(self):
        "Not logged"
        url = reverse('creme_core__fake_removed_view', args=(1,))
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))


class DetailTestCase(ViewsTestCase, BrickTestCaseMixin):
    # TODO: factorise with tests.gui.test_misc.GuiTestCase
    class FakeRequest:
        def __init__(self, user):
            user_id = str(user.id)
            sessions = [d for d in (s.get_decoded() for s in Session.objects.all())
                            if d.get('_auth_user_id') == user_id
                       ]
            assert 1 == len(sessions)
            self.session = sessions[0]

    def test_detail01(self):
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
        self.assertEqual(fox.id, last_items[0].pk)

        # -----
        imprints = Imprint.objects.all()
        self.assertEqual(1, len(imprints))
        self.assertEqual(imprints[0].entity.get_real_entity(), fox)

        # -----
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, PropertiesBrick.id_)
        self.get_brick_node(tree, MODELBRICK_ID)

    def test_detail02(self):
        "Object does not exist"
        self.login()

        response = self.assertGET404(reverse('creme_core__view_fake_contact', args=(self.UNUSED_PK,)))
        self.assertTemplateUsed(response, '404.html')

    def test_detail03(self):
        "Not super-user"
        user = self.login(is_superuser=False)
        fox = FakeContact.objects.create(user=user, first_name='Fox', last_name='McCloud')
        self.assertGET200(fox.get_absolute_url())

    def test_detail04(self):
        "Not logged"
        user = self.login()
        fox = FakeContact.objects.create(user=user, first_name='Fox', last_name='McCloud')
        url = fox.get_absolute_url()

        self.client.logout()
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))

    def test_detail05(self):
        "Viewing is not allowed (model credentials)"
        self.login(is_superuser=False)
        fox = FakeContact.objects.create(user=self.other_user, first_name='Fox', last_name='McCloud')

        response = self.assertGET403(fox.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertIn(escape(_('You are not allowed to view this entity: {}').format(
                                _('Entity #{id} (not viewable)').format(id=fox.id)
                            )),
                      response.content.decode()
                     )

    def test_detail06(self):
        "Viewing is not allowed (app credentials)"
        # NB: not need to create an instance, the "app" permission must be checked before the SQL query.
        self.login(is_superuser=False, allowed_apps=('creme_config',))  # Not "creme_core"

        response = self.assertGET403(reverse('creme_core__view_fake_contact', args=(self.UNUSED_PK,)))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertIn(escape(_('You are not allowed to access to the app: {}').format(_('Core'))),
                      response.content.decode()
                     )


class CreationTestCase(ViewsTestCase):
    def test_entity_creation01(self):
        user = self.login()

        url = reverse('creme_core__create_fake_contact')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add.html')

        context = response.context
        self.assertIsInstance(context.get('form'), fake_forms.FakeContactForm)
        self.assertEqual(_('Create a contact'), context.get('title'))
        self.assertEqual(_('Save the contact'), context.get('submit_label'))

        count = FakeContact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(url, follow=True,
                                    data={'user':       user.id,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         },
                                   )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, FakeContact.objects.count())
        contact = self.get_object_or_fail(FakeContact,
                                          first_name=first_name,
                                          last_name=last_name,
                                         )
        self.assertRedirects(response, contact.get_absolute_url())

        self.assertFalse(contact.properties.all())
        self.assertFalse(contact.relations.all())

    def test_entity_creation02(self):
        "ValidationError + cancel_url."
        user = self.login()

        url = reverse('creme_core__create_fake_contact')
        lv_url = FakeContact.get_lv_absolute_url()
        response = self.assertGET200(url, HTTP_REFERER='http://testserver' + lv_url)
        self.assertEqual(lv_url, response.context.get('cancel_url'))

        response = self.client.post(url, follow=True,
                                    data={'user': user.id,
                                          # 'last_name': name,  # NB: Missing
                                          'cancel_url': lv_url,
                                         },
                                   )
        self.assertFormError(response, 'form', 'last_name', _('This field is required.'))
        self.assertEqual(lv_url, response.context.get('cancel_url'))

    def test_entity_creation03(self):
        "Not app credentials."
        self.login(is_superuser=False, allowed_apps=['creme_config'])

        response = self.assertGET403(reverse('creme_core__create_fake_contact'))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertIn(
            escape(_('You are not allowed to access to the app: {}').format(_('Core'))),
            response.content.decode()
        )

    def test_entity_creation04(self):
        "Not creation credentials"
        self.login(is_superuser=False, creatable_models=[FakeOrganisation])  # Not FakeContact

        response = self.assertGET403(reverse('creme_core__create_fake_contact'))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')

    def test_entity_creation05(self):
        "Not logged."
        url = reverse('creme_core__create_fake_contact')
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))

    def test_entity_creation06(self):
        "Not super-user."
        self.login(is_superuser=False, creatable_models=[FakeContact])
        self.assertGET200(reverse('creme_core__create_fake_contact'))

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_entity_creation_properties(self):
        user = self.login()

        create_ptype = CremePropertyType.create
        ptype01 = create_ptype(str_pk='test-prop_smokes',  text='Smokes')
        ptype02 = create_ptype(str_pk='test-prop_glasses', text='Wears glasses')
        ptype03 = create_ptype(str_pk='test-prop_gun',     text='Has a gun',
                               subject_ctypes=[FakeContact],
                              )
        ptype04 = create_ptype(str_pk='test-prop_ship', text='Is a ship',
                               subject_ctypes=[FakeOrganisation],
                              )

        url = reverse('creme_core__create_fake_contact')

        # GET ---
        response = self.assertGET200(url)

        with self.assertNoException():
            ptypes_choices = response.context['form'].fields['property_types'].choices

        # Choices are sorted with 'text'
        choices = [(choice[0].value, choice[1]) for choice in ptypes_choices]
        i1 = self.assertIndex((ptype03.id, ptype03.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype02.id, ptype02.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotIn((ptype04.id, ptype04.text), choices)

        # POST ---
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(
            url,
            follow=True,
            data={'user':       user.id,
                  'first_name': first_name,
                  'last_name':  last_name,
                  'property_types': [ptype01.id, ptype03.id],
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(FakeContact,
                                          first_name=first_name,
                                          last_name=last_name,
                                         )
        self.assertSetEqual({ptype01, ptype03},
                            {p.type for p in contact.properties.all()}
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

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_loves', 'loves'),
                              ('test-object_loves',  'is loved'),
                             )[0]
        rtype2 = create_rtype(('test-subject_pilots', 'pilots',     [FakeContact]),
                              ('test-object_pilots',  'is piloted', [FakeOrganisation]),
                             )[0]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(predicate='Pilots the Swordfish',
                            relation_type=rtype2,
                            object_entity=orga2,
                           )
        sfrt2 = create_strt(predicate='Loves Faye',
                            relation_type=rtype1,
                            object_entity=contact2,
                           )

        url = reverse('creme_core__create_fake_contact')

        # GET ---
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            sf_choices = fields['semifixed_rtypes'].choices

        self.assertNotIn('rtypes_info', fields)
        self.assertIn('relation_types', fields)

        self.assertInChoices(value=sfrt1.id, label=sfrt1.predicate, choices=sf_choices)
        self.assertInChoices(value=sfrt2.id, label=sfrt2.predicate, choices=sf_choices)

        # POST ---
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(
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
        self.assertNoFormError(response)

        subject = self.get_object_or_fail(FakeContact,
                                          first_name=first_name,
                                          last_name=last_name,
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

    def test_adding_to_entity(self):
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        url = reverse('creme_core__create_fake_address', args=(nerv.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(f'Adding address to <{nerv}>', context.get('title'))
        self.assertEqual(_('Save the address'),         context.get('submit_label'))

        city = 'Tokyo'
        response = self.client.post(url, data={'city': city})
        self.assertNoFormError(response)
        self.get_object_or_fail(FakeAddress, city=city, entity=nerv.id)


class EditionTestCase(ViewsTestCase):
    def test_entity_edition01(self):
        user = self.login()
        contact = FakeContact.objects.create(user=user,
                                             first_name='Spik',
                                             last_name='Spiege',
                                            )
        url = contact.get_edit_absolute_url()

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit.html')

        context = response.context
        self.assertIsInstance(context.get('form'), fake_forms.FakeContactForm)
        self.assertEqual(_('Edit «{object}»').format(object=contact), context.get('title'))
        self.assertEqual(_('Save the modifications'),                 context.get('submit_label'))
        self.assertIsNone(context.get('cancel_url', -1))

        first_name = 'Spike'
        last_name = 'Spiegel'
        description = 'DESCRIPTION'

        # from creme.creme_core.utils.profiling import QueriesPrinter
        # with QueriesPrinter():
        response = self.client.post(url, follow=True,
                                    data={'user':        user.id,
                                          'first_name':  first_name,
                                          'last_name':   last_name,
                                          'description': description,
                                         },
                                   )

        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(last_name,   contact.last_name)
        self.assertEqual(first_name,  contact.first_name)
        self.assertEqual(description, contact.description)

        self.assertRedirects(response, contact.get_absolute_url())

    def test_entity_edition02(self):
        "Invalid ID"
        self.login()
        self.assertGET404(reverse('creme_core__edit_fake_contact', args=(self.UNUSED_PK,)))

    def test_entity_edition03(self):
        "ValidationError + cancel_url"
        user = self.login()
        contact = FakeContact.objects.create(user=user,
                                             first_name='Spik',
                                             last_name='Spiegel',
                                            )
        url = contact.get_edit_absolute_url()

        lv_url = FakeContact.get_lv_absolute_url()
        response = self.assertGET200(url, HTTP_REFERER='http://testserver' + lv_url)
        self.assertEqual(lv_url, response.context.get('cancel_url'))

        response = self.client.post(url, follow=True,
                                    data={'user': user.id,
                                          'first_name': 'Spike',
                                          # 'last_name': last_name,  # NB: Missing
                                          'cancel_url': lv_url,
                                         },
                                   )
        self.assertFormError(response, 'form', 'last_name', _('This field is required.'))
        self.assertEqual(lv_url, response.context.get('cancel_url'))

    def test_entity_edition04(self):
        "Not app credentials"
        self.login(is_superuser=False, allowed_apps=['creme_config'])

        response = self.assertGET403(reverse('creme_core__edit_fake_contact', args=(self.UNUSED_PK,)))
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertIn(
            escape(_('You are not allowed to access to the app: {}').format(_('Core'))),
            response.content.decode()
        )

    def test_entity_edition05(self):
        "Not edition credentials"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            # EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        contact = FakeContact.objects.create(user=self.other_user,
                                             first_name='Spike',
                                             last_name='Spiegel',
                                            )

        response = self.assertGET403(contact.get_edit_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')

    def test_entity_edition06(self):
        "Not logged."
        url = reverse('creme_core__edit_fake_contact', args=(self.UNUSED_PK,))
        response = self.assertGET(302, url)
        self.assertRedirects(response, '{}?next={}'.format(reverse('creme_login'), url))

    def test_entity_edition07(self):
        "Not super-user."
        user = self.login(is_superuser=False)
        contact = FakeContact.objects.create(user=user,
                                             first_name='Spike',
                                             last_name='Spiegel',
                                            )
        self.assertGET200(contact.get_edit_absolute_url())

    def test_related_to_entity_edition01(self):
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        address = FakeAddress.objects.create(
            entity=nerv,
            value='26 angel street',
        )
        url = reverse('creme_core__edit_fake_address', args=(address.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(f'Address for <{nerv}>',     context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

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

        response = self.assertGET403(url)
        self.assertTemplateUsed(response, 'creme_core/forbidden.html')
        self.assertIn(
            escape(_('You are not allowed to edit this entity: {}').format(
                        _('Entity #{id} (not viewable)').format(id=nerv.id)
                  )),
            response.content.decode()
        )

        # ---
        nerv.user = user
        nerv.save()
        self.assertGET200(url)
