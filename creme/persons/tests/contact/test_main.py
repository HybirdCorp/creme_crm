# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import ValidationError
    from django.urls import reverse
    from django.utils.html import escape
    from django.utils.translation import ugettext as _, pgettext

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui.field_printers import field_printers_registry
    from creme.creme_core.models import (RelationType, Relation,
            SetCredentials, FieldsConfig, CremeUser)

    from creme.documents.tests.base import skipIfCustomDocument

    from creme.persons.models import Position, Civility, Sector
    from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY, UUID_FIRST_CONTACT

    from ..base import (_BaseTestCase, skipIfCustomAddress, skipIfCustomContact,
            skipIfCustomOrganisation, Contact, Organisation, Address, Document)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomContact
class ContactTestCase(_BaseTestCase):
    def _build_addrelated_url(self, orga_id, rtype_id=None):
        kwargs = {'orga_id': orga_id}

        if rtype_id:
            kwargs['rtype_id'] = rtype_id

        return reverse('persons__create_related_contact', kwargs=kwargs)

    def test_empty_fields(self):
        user = self.login()

        with self.assertNoException():
            contact = Contact.objects.create(user=user, last_name='Spiegel')

        self.assertEqual('', contact.first_name)
        self.assertEqual('', contact.description)
        self.assertEqual('', contact.skype)
        self.assertEqual('', contact.phone)
        self.assertEqual('', contact.mobile)
        self.assertEqual('', contact.email)
        self.assertEqual('', contact.url_site)
        self.assertEqual('', contact.full_position)

    def test_unicode(self):
        first_name = 'Spike'
        last_name  = 'Spiegel'
        build_contact = partial(Contact, last_name=last_name)
        self.assertEqual(last_name, str(build_contact()))
        self.assertEqual(last_name, str(build_contact(first_name='')))
        self.assertEqual(_('{first_name} {last_name}').format(
                                first_name=first_name,
                                last_name=last_name,
                            ),
                         str(build_contact(first_name=first_name))
                        )

        captain = Civility.objects.create(title='Captain')  # No shortcut
        self.assertEqual(_('{first_name} {last_name}').format(
                                first_name=first_name,
                                last_name=last_name,
                            ),
                         str(build_contact(first_name=first_name, civility=captain))
                        )

        captain.shortcut = shortcut = 'Cpt'
        captain.save()
        self.assertEqual(_('{civility} {first_name} {last_name}').format(
                                civility=shortcut,
                                first_name=first_name,
                                last_name=last_name,
                            ),
                         str(build_contact(first_name=first_name, civility=captain))
                        )

    def test_populated_contact_uuid(self):
        first_contact = Contact.objects.order_by('id').first()
        self.assertIsNotNone(first_contact)

        user = first_contact.is_user
        self.assertIsNotNone(user)

        self.assertEqual(UUID_FIRST_CONTACT, str(first_contact.uuid))

    def test_createview01(self):
        user = self.login()

        url = reverse('persons__create_contact')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'persons/add_contact_form.html')

        count = Contact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(url, follow=True,
                                    data={'user':       user.pk,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomAddress
    def test_createview02(self):
        "With addresses"
        user = self.login()

        first_name = 'Spike'
        b_address = 'In the Bebop.'
        s_address = 'In the Bebop (bis).'

        url = reverse('persons__create_contact')
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('billing_address-address', fields)
        self.assertIn('shipping_address-address', fields)
        self.assertNotIn('billing_address-name', fields)
        self.assertNotIn('shipping_address-name', fields)

        response = self.client.post(url, follow=True,
                                    data={'user':                     user.pk,
                                          'first_name':               first_name,
                                          'last_name':                'Spiegel',
                                          'billing_address-address':  b_address,
                                          'shipping_address-address': s_address,
                                         },
                                   )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        billing_address = contact.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,            billing_address.address)
        self.assertEqual(_('Billing address'), billing_address.name)

        shipping_address = contact.shipping_address
        self.assertIsNotNone(shipping_address)
        self.assertEqual(s_address,             shipping_address.address)
        self.assertEqual(_('Shipping address'), shipping_address.name)

        self.assertContains(response, b_address)
        self.assertContains(response, s_address)

    def test_editview01(self):
        user = self.login()
        first_name = 'Faye'
        contact = Contact.objects.create(user=user, first_name=first_name, last_name='Valentine')

        url = contact.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'persons/edit_contact_form.html')

        last_name = 'Spiegel'
        response = self.assertPOST200(url, follow=True,
                                      data={'user':       user.pk,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                           },
                                     )

        contact = self.refresh(contact)
        self.assertEqual(last_name, contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomAddress
    def test_editview02(self):
        "Edit addresses"
        user = self.login()

        first_name = 'Faye'
        last_name  = 'Valentine'
        self.assertPOST200(reverse('persons__create_contact'), follow=True,
                           data={'user':                     user.pk,
                                 'first_name':               first_name,
                                 'last_name':                last_name,
                                 'billing_address-address':  'In the Bebop.',
                                 'shipping_address-address': 'In the Bebop. (bis)',
                                },
                          )
        contact = Contact.objects.get(first_name=first_name)
        billing_address_id  = contact.billing_address_id
        shipping_address_id = contact.shipping_address_id

        state   = 'Solar system'
        country = 'Mars'
        self.assertNoFormError(self.client.post(contact.get_edit_absolute_url(), follow=True,
                                                data={'user':                     user.pk,
                                                      'first_name':               first_name,
                                                      'last_name':                last_name,
                                                      'billing_address-state':    state,
                                                      'shipping_address-country': country,
                                                     },
                                               )
                              )

        contact = self.refresh(contact)
        self.assertEqual(billing_address_id,  contact.billing_address_id)
        self.assertEqual(shipping_address_id, contact.shipping_address_id)

        self.assertEqual(state,   contact.billing_address.state)
        self.assertEqual(country, contact.shipping_address.country)

    def test_editview03(self):
        "Contact is a user => sync"
        user = self.login()
        contact = self.get_object_or_fail(Contact, is_user=user)

        url = contact.get_edit_absolute_url()
        response = self.assertPOST200(url, follow=True,
                                      data={'user':      user.id,
                                            'last_name': contact.last_name,
                                           },
                                     )
        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'first_name', msg)
        self.assertFormError(response, 'form', 'email',      msg)

        first_name = contact.first_name.lower(); self.assertNotEqual(first_name, user.first_name)
        last_name  = contact.last_name.upper();  self.assertNotEqual(last_name,  user.last_name)
        email      = '{}.{}@noir.org'.format(user.first_name, user.last_name)
        self.assertNotEqual(email, user.email)

        response = self.client.post(url, follow=True,
                                    data={'user':       user.id,
                                          'last_name':  last_name,
                                          'first_name': first_name,
                                          'email':      email,
                                         },
                                   )
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertEqual(email,      contact.email)

        user = self.refresh(user)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)

    def test_editview04(self):
        "Contact is a user + emails is hidden (crashed)"
        user = self.login()
        contact = self.get_object_or_fail(Contact, is_user=user)

        FieldsConfig.create(Contact,
                            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                           )

        url = contact.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('email', fields)

        last_name  = user.last_name
        first_name = user.first_name
        email = user.email
        description = 'First contact user'
        response = self.client.post(url, follow=True,
                                    data={'user':        user.id,
                                          'last_name':   last_name,
                                          'first_name':  first_name,
                                          'email':       'useless@dontcare.org',
                                          'description': description,
                                         },
                                   )
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(first_name,  contact.first_name)
        self.assertEqual(last_name,   contact.last_name)
        self.assertEqual(email,       contact.email)  # <= no change
        self.assertEqual(description, contact.description)

        user = self.refresh(user)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)  # <= no change

    def test_is_user01(self):
        "Property 'linked_contact'"
        user = self.login()

        with self.assertNumQueries(0):
            rel_contact = user.linked_contact

        contact = self.get_object_or_fail(Contact, is_user=user)
        self.assertEqual(contact, rel_contact)

        user = self.refresh(user)  # Clean cache

        with self.assertNumQueries(1):
            user.linked_contact

        with self.assertNumQueries(0):
            user.linked_contact

        self.assertTrue(hasattr(user, 'get_absolute_url'))
        self.assertEqual(contact.get_absolute_url(), user.get_absolute_url())

    def test_is_user02(self):
        """Contact.clean() + integrity of User."""
        user = self.login()
        contact = user.linked_contact
        last_name = contact.last_name
        first_name = contact.first_name

        contact.email = ''
        contact.first_name = ''
        contact.save()

        user = self.refresh(user)
        self.assertEqual('',         user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual('',         user.email)

        with self.assertRaises(ValidationError) as cm:
            contact.full_clean()

        self.assertEqual([_('This Contact is related to a user and must have a first name.')],
                         cm.exception.messages
                        )

        contact.first_name = first_name

        with self.assertRaises(ValidationError) as cm:
            contact.full_clean()

        self.assertEqual([_('This Contact is related to a user and must have an e-mail address.')],
                         cm.exception.messages
                        )

    def test_listview(self):
        user = self.login()

        count = Contact.objects.filter(is_deleted=False).count()

        create_contact = partial(Contact.objects.create, user=user)
        faye    = create_contact(first_name='Faye',    last_name='Valentine')
        spike   = create_contact(first_name='Spike',   last_name='Spiegel')
        vicious = create_contact(first_name='Vicious', last_name='Badguy', is_deleted=True)

        response = self.assertGET200(Contact.get_lv_absolute_url())

        with self.assertNoException():
            # contacts_page = response.context['entities']
            contacts_page = response.context['page_obj']

        self.assertEqual(count + 2, contacts_page.paginator.count)

        contacts_set = set(contacts_page.object_list)
        self.assertIn(faye,  contacts_set)
        self.assertIn(spike, contacts_set)
        self.assertNotIn(vicious, contacts_set)

    @skipIfCustomOrganisation
    def test_create_linked_contact01(self):
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Acme')
        url = self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY)
        self.assertGET200(url)

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.client.post(url, follow=True,
                                    data={'orga_overview': 'dontcare',
                                          'relation':      'dontcare',
                                          'user':          user.pk,
                                          'first_name':    first_name,
                                          'last_name':     last_name,
                                         },
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga.get_absolute_url())

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertRelationCount(1, orga, REL_OBJ_EMPLOYED_BY, contact)
        self.assertEqual(last_name, contact.last_name)

    @skipIfCustomOrganisation
    def test_create_linked_contact02(self):
        "RelationType not fixed"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Acme')
        url = self._build_addrelated_url(orga.id)
        self.assertGET200(url)

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.client.post(url, follow=True,
                                    data={'orga_overview': 'dontcare',
                                          'relation':      REL_SUB_EMPLOYED_BY,
                                          'user':          user.pk,
                                          'first_name':    first_name,
                                          'last_name':     last_name,
                                         },
                                   )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, orga, REL_OBJ_EMPLOYED_BY, contact)

    @skipIfCustomOrganisation
    def test_create_linked_contact03(self):
        "No LINK credentials"
        user = self.login(is_superuser=False, creatable_models=[Contact])

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_OWN,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not 'LINK'
                 )

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY)
        self.assertGET403(url)

        get_ct = ContentType.objects.get_for_model
        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Organisation))
        self.assertGET403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Contact))
        self.assertGET200(url)

        response = self.assertPOST200(url, follow=True,
                                      data={'orga_overview': 'dontcare',
                                            'relation':      'dontcare',
                                            'user':          self.other_user.pk,
                                            'first_name':    'Bugs',
                                            'last_name':     'Bunny',
                                           }
                                     )
        self.assertFormError(response, 'form', 'user',
                             _('You are not allowed to link with the «{models}» of this user.').format(
                                    models=_('Contacts'),
                                )
                            )

    @skipIfCustomOrganisation
    def test_create_linked_contact04(self):
        "Cannot VIEW the organisation => error"
        user = self.login(is_superuser=False, creatable_models=[Contact])

        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | EntityCredentials.LINK |
                  EntityCredentials.DELETE | EntityCredentials.UNLINK,
            ctype=ContentType.objects.get_for_model(Contact),  # Not Organisation
        )

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertFalse(user.has_perm_to_view(orga))

        response = self.client.get(self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY))
        self.assertContains(response,
                            escape(_('You are not allowed to view this entity: {}').format(
                                    _('Entity #{id} (not viewable)').format(id=orga.id)
                                  )),
                            status_code=403
                           )

    @skipIfCustomOrganisation
    def test_create_linked_contact05(self):
        "Cannot LINK the organisation => error"
        user = self.login(is_superuser=False, creatable_models=[Contact])

        get_ct = ContentType.objects.get_for_model

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_ALL,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | EntityCredentials.LINK |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,
                  ctype=get_ct(Contact),  # Not Organisation
                 )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not LINK
                  ctype=get_ct(Organisation),
                 )

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        self.assertGET403(self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY))

    @skipIfCustomOrganisation
    def test_create_linked_contact06(self):
        "Misc errors"
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Acme')

        self.assertGET404(self._build_addrelated_url(1024,  # Doesn't exist
                                                     REL_OBJ_EMPLOYED_BY,
                                                    )
                         )
        self.assertGET404(self._build_addrelated_url(orga.id,
                                                     'IDONOTEXIST',
                                                    )
                        )

        create_rtype = RelationType.create
        rtype1 = create_rtype(('persons-subject_test_rtype1', 'RType #1',     [Organisation]),
                              ('persons-object_test_rtype1',  'Rtype sym #1', [Contact]),
                             )[0]
        self.assertGET200(self._build_addrelated_url(orga.id, rtype1.id))

        rtype2 = create_rtype(('persons-subject_test_badrtype1', 'Bad RType #1',     [Organisation]),
                              ('persons-object_test_badrtype1',  'Bad RType sym #1', [Document]),  # <==
                             )[0]
        self.assertGET409(self._build_addrelated_url(orga.id, rtype2.id))

        rtype3 = create_rtype(('persons-subject_test_badrtype2', 'Bad RType #2',     [Document]),  # <==
                              ('persons-object_test_badrtype2',  'Bad RType sym #2', [Contact]),
                             )[0]
        self.assertGET409(self._build_addrelated_url(orga.id, rtype3.id))

        rtype4 = create_rtype(('persons-subject_test_badrtype3', 'Bad RType #3',     [Organisation]),
                              ('persons-object_test_badrtype3',  'Bad RType sym #3', [Contact]),
                              is_internal=True,  # <==
                             )[0]
        self.assertGET409(self._build_addrelated_url(orga.id, rtype4.id))

    @skipIfCustomOrganisation
    def test_create_linked_contact07(self):
        "Avoid internal RelationType"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Acme')
        rtype = RelationType.create(
            ('persons-subject_test_linked', 'is the employee of the month at', [Contact]),
            ('persons-object_test_linked',  'has the employee of the month',   [Organisation]),
            is_internal=True,
        )[0]

        response = self.assertPOST200(self._build_addrelated_url(orga.id),
                                      follow=True,
                                      data={'orga_overview': 'dontcare',
                                            'relation':      rtype.id,
                                            'user':          user.pk,
                                            'first_name':    'Bugs',
                                            'last_name':     'Bunny',
                                           }
                                      )
        self.assertFormError(response, 'form', 'relation',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses & is_user are problematic"
        user = self.login()
        naruto = self.get_object_or_fail(Contact, is_user=user)

        create_address = partial(Address.objects.create,
                                 city='Konoha', state='Konoha', zipcode='111',
                                 country='The land of fire', department="Ninjas' homes",
                                 content_type=ContentType.objects.get_for_model(Contact),
                                 object_id=naruto.id,
                                )
        naruto.billing_address  = create_address(name="Naruto's", address='Home', po_box='000')
        naruto.shipping_address = create_address(name="Naruto's", address='Home (second entry)', po_box='001')
        naruto.save()

        for i in range(5):
            create_address(name='Secret Cave #{}'.format(i), address='Cave #{}'.format(i), po_box='XXX')

        kage_bunshin = naruto.clone()

        self.assertEqual(naruto.first_name, kage_bunshin.first_name)
        self.assertEqual(naruto.last_name, kage_bunshin.last_name)
        self.assertIsNone(kage_bunshin.is_user)  # <====

        self.assertEqual(naruto.id, naruto.billing_address.object_id)
        self.assertEqual(naruto.id, naruto.shipping_address.object_id)

        self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
        self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)

        addresses   = list(Address.objects.filter(object_id=naruto.id))
        c_addresses = list(Address.objects.filter(object_id=kage_bunshin.id))
        self.assertEqual(7, len(addresses))
        self.assertEqual(7, len(c_addresses))

        addresses_map   = {a.address: a for a in addresses}
        c_addresses_map = {a.address: a for a in c_addresses}
        self.assertEqual(7, len(addresses_map))
        self.assertEqual(7, len(c_addresses_map))

        for ident, address in addresses_map.items():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    def test_delete01(self):
        user = self.login()
        naruto = Contact.objects.create(user=user, first_name='Naruto', last_name='Uzumaki')
        url = naruto.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            naruto = self.refresh(naruto)

        self.assertIs(naruto.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(naruto)

    def test_delete02(self):
        "Can not delete if the Contact corresponds to an user"
        user = self.login()
        contact = user.linked_contact
        self.assertPOST403(contact.get_delete_absolute_url(), follow=True)

    def test_delete03(self):
        "Can not trash if the Contact corresponds to an user"
        user = self.login()
        contact = user.linked_contact
        self.assertPOST403(contact.get_delete_absolute_url(), follow=True)

    def test_delete_civility(self):
        "Set to null"
        user = self.login()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(user=user, first_name='Harlock',
                                         last_name='Matsumoto', civility=captain,
                                        )

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'civility')),
                           data={'id': captain.pk}
                          )
        self.assertDoesNotExist(captain)

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.civility)

    def test_delete_position(self):
        "Set to null"
        user = self.login()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(user=user, first_name='Harlock',
                                         last_name='Matsumoto', position=captain,
                                        )

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'position')),
                           data={'id': captain.pk}
                          )
        self.assertDoesNotExist(captain)

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.position)

    def test_delete_sector(self):
        "Set to null"
        user = self.login()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(user=user, first_name='Harlock',
                                         last_name='Matsumoto', sector=piracy,
                                        )

        self.assertPOST200(reverse('creme_config__delete_instance', args=('persons', 'sector')),
                           data={'id': piracy.pk}
                          )
        self.assertDoesNotExist(piracy)

        harlock = self.get_object_or_fail(Contact, pk=harlock.pk)
        self.assertIsNone(harlock.sector)

    @skipIfCustomDocument
    def test_delete_image(self):
        "Set to null"
        user = self.login()
        image = self._create_image()
        harlock = Contact.objects.create(user=user, last_name='Matsumoto', image=image)

        image.delete()

        self.assertDoesNotExist(image)
        self.assertIsNone(self.refresh(harlock).image)

    def test_user_linked_contact01(self):
        first_name = 'Deunan'
        last_name = 'Knut'
        user = CremeUser.objects.create(username='dknut', last_name=last_name, first_name=first_name)

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsInstance(contact, Contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

    def test_user_linked_contact02(self):
        user = CremeUser.objects.create(username='dknut', is_team=True,
                                        last_name='Knut', first_name='Deunan',
                                       )

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsNone(contact)

    def test_user_delete_is_user(self):
        "Manage Contact.is_user field : Contact is no more related to deleted user."
        user = self.login()
        other_user = self.other_user

        contact = user.linked_contact
        other_contact = other_user.linked_contact

        create_contact = Contact.objects.create
        deunan   = create_contact(user=user,       first_name='Deunan',   last_name='Knut')
        briareos = create_contact(user=other_user, first_name='Briareos', last_name='Hecatonchires')

        self.assertNoFormError(self.client.post(reverse('creme_config__delete_user', args=(other_user.id,)),
                                                {'to_user': user.id}
                                               )
                              )
        self.assertDoesNotExist(other_user)
        self.assertStillExists(contact)

        other_contact = self.assertStillExists(other_contact)
        self.assertIsNone(other_contact.is_user)
        self.assertEqual(user, other_contact.user)

        self.assertStillExists(deunan)
        self.assertEqual(user, self.assertStillExists(briareos).user)

    def test_fk_user_printer01(self):
        user = self.login()

        deunan = Contact.objects.create(user=user, first_name='Deunan', last_name='Knut')
        kirika = user.linked_contact

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual('<a href="{}">{}</a>'.format(kirika.get_absolute_url(), kirika),
                         get_html_val(deunan, 'user', user)
                        )
        self.assertEqual('<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
                         get_html_val(deunan, 'is_user', user)
                        )

        self.assertEqual(str(user), field_printers_registry.get_csv_field_value(deunan, 'user', user))

    def test_fk_user_printer02(self):
        "Team"
        user = self.login()

        eswat = CremeUser.objects.create(username='eswat', is_team=True)
        deunan = Contact.objects.create(user=eswat, first_name='Deunan', last_name='Knut')

        self.assertEqual(str(eswat),
                         field_printers_registry.get_html_field_value(deunan, 'user', user)
                        )
