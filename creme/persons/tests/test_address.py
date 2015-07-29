# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import FieldsConfig
    from creme.creme_core.models.history import HistoryLine, TYPE_CREATION, TYPE_AUX_CREATION

    from .base import skipIfCustomAddress, skipIfCustomContact, skipIfCustomOrganisation
    from ..models import Address, Organisation, Contact
    from ..blocks import other_address_block
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('AddressTestCase',)


@skipIfCustomAddress
class AddressTestCase(CremeTestCase):
    #ADD_URL = '/persons/address/add/%s'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'persons')

    def login(self, create_orga=True, *args, **kwargs):
        super(AddressTestCase, self).login(*args, **kwargs)

        if create_orga:
            return Organisation.objects.create(user=self.user, name='Nerv')

    def _build_add_url(self, entity):
        return reverse('persons__create_address', args=(entity.id,))

    def _create_address(self, orga, name, address, po_box, city, state, zipcode, country, department):
#        response = self.client.post(self.ADD_URL % orga.id,
        response = self.client.post(self._build_add_url(orga),
                                    data={'name':       name,
                                          'address':    address,
                                          'po_box':     po_box,
                                          'city':       city,
                                          'state':      state,
                                          'zipcode':    zipcode,
                                          'country':    country,
                                          'department': department,
                                         }
                                   )
        self.assertNoFormError(response)

    def test_info_names01(self):
        self.assertEqual({'name', 'address', 'po_box', 'zipcode', 'city',
                          'department', 'state', 'country',
                         },
                         set(Address.info_field_names())
                        )

    def test_info_names02(self):
        fconf = FieldsConfig.create(Address,
                                    descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
                                   )

        self.assertEqual({'name', 'address', 'zipcode', 'city',
                          'department', 'state', 'country',
                         },
                         set(Address.info_field_names())
                        )

    @skipIfCustomOrganisation
    def test_createview(self):
        orga = self.login()
        self.assertFalse(Address.objects.filter(object_id=orga.id).exists())

        #self.assertGET200(self.ADD_URL % orga.id)
        self.assertGET200(self._build_add_url(orga))

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Atlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(name,       address.name)
        self.assertEqual(address_value, address.address)
        self.assertEqual(po_box,     address.po_box)
        self.assertEqual(city,       address.city)
        self.assertEqual(state,      address.state)
        self.assertEqual(zipcode,    address.zipcode)
        self.assertEqual(country,    address.country)
        self.assertEqual(department, address.department)

        response = self.client.get(orga.get_absolute_url())
        self.assertContains(response, 'id="%s"' % other_address_block.id_)
        self.assertContains(response, name)
        self.assertContains(response, address_value)
        self.assertContains(response, po_box)
        self.assertContains(response, city)
        self.assertContains(response, state)
        self.assertContains(response, zipcode)
        self.assertContains(response, country)
        self.assertContains(response, department)

    @skipIfCustomOrganisation
    def test_create_billing(self):
        orga = self.login()
        self.assertGET404('/persons/address/add/invalid/%s' % orga.id)

#        url = '/persons/address/add/billing/%s' % orga.id
        url = reverse('persons__create_billing_address', args=(orga.id,))
        self.assertGET200(url)

        addr_value = '21 jump street'
        city = 'Atlantis'
        self.assertNoFormError(self.client.post(url, data={'address': addr_value,
                                                           'city':    city,
                                                          }
                                               )
                              )

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(city,       address.city)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.po_box)
        self.assertEqual('',         address.name)

        self.assertEqual(address, self.refresh(orga).billing_address)

    @skipIfCustomOrganisation
    def test_create_shipping(self):
        orga = self.login()
#        url = '/persons/address/add/shipping/%s' % orga.id
        url = reverse('persons__create_shipping_address', args=(orga.id,))
        self.assertGET200(url)

        addr_value = '21 jump street'
        country = 'Wonderland'
        self.assertNoFormError(self.client.post(url, data={'address': addr_value,
                                                           'country': country,
                                                          }
                                               )
                              )

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(country,    address.country)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.zipcode)
        self.assertEqual('',         address.name)

        self.assertEqual(address, self.refresh(orga).shipping_address)

    @skipIfCustomOrganisation
    def test_editview(self):
        orga = self.login()

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Atlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(orga, name, address_value, po_box, city, state, zipcode, country, department)
        address = Address.objects.filter(object_id=orga.id)[0]

        #url = '/persons/address/edit/%s' % address.id
        url = address.get_edit_absolute_url()
        self.assertGET200(url)

        city = 'Groville'
        country = 'Groland'
        response = self.client.post(url, data={'name':       name,
                                               'address':    address,
                                               'po_box':     po_box,
                                               'city':       city,
                                               'state':      state,
                                               'zipcode':    zipcode,
                                               'country':    country,
                                               'department': department,
                                             }
                                   )
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city,    address.city)
        self.assertEqual(country, address.country)

    @skipIfCustomOrganisation
    def test_deleteview(self):
        orga = self.login()

        self._create_address(orga, 'name', 'address', 'po_box', 'city', 'state', 'zipcode', 'country', 'department')
        address = Address.objects.filter(object_id=orga.id)[0]
        ct = ContentType.objects.get_for_model(Address)

        self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': address.id})
        self.assertFalse(Address.objects.filter(object_id=orga.id).exists())

    def test_bool(self):
        self.assertFalse(Address())
        self.assertTrue(Address(name='Address#1'))
        self.assertTrue(Address(address='21 jump street'))
        self.assertTrue(Address(po_box='Popop'))
        self.assertTrue(Address(zipcode='424242'))
        self.assertTrue(Address(city='Atlantis'))
        self.assertTrue(Address(department='rucrazy'))
        self.assertTrue(Address(state='OfTheArt'))
        self.assertTrue(Address(country='Yeeeha'))

        self.assertTrue(Address(address='21 jump street', country='Yeeeha'))

    def test_unicode(self):
        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        zipcode = '424242'
        city = 'Atlantis'
        department = 'rucrazy'
        state = '??'
        country = 'wtf'

        address = Address(name=name,
                          address=address_value,
                          po_box=po_box,
                          zipcode=zipcode,
                          city=city,
                          department=department,
                          state=state,
                          country=country
                         )
        self.assertEqual(u'%s %s %s %s' % (address_value, zipcode, city, department),
                         unicode(address)
                        )

        address.zipcode = None
        self.assertEqual(u'%s %s %s' % (address_value, city, department), unicode(address))

        address.department = None
        self.assertEqual(u'%s %s' % (address_value, city), unicode(address))

        self.assertEqual(po_box, unicode(Address(po_box=po_box)))
        self.assertEqual(state, unicode(Address(state=state)))
        self.assertEqual(country, unicode(Address(country=country)))

        self.assertEqual('%s %s %s' % (po_box, state, country),
                         unicode(Address(po_box=po_box, state=state, country=country))
                        )

    @skipIfCustomOrganisation
    def test_delete_orga(self):
        "Addresses are deleted when the related Organisation is deleted."
        orga = self.login()

        create_address = Address.objects.create
        orga.billing_address = b_addr = create_address(name="Billing address",
                                                       address="BA - Address",
                                                       owner=orga,
                                                      )
        orga.save()

        orga.shipping_address = s_addr = create_address(name="Shipping address",
                                                        address="SA - Address",
                                                        owner=orga,
                                                       )
        orga.save()

        other_addr = create_address(name="Other address", address="OA - Address", owner=orga)

        orga.delete()
        self.assertDoesNotExist(orga)
        self.assertFalse(Address.objects.filter(pk__in=[b_addr.id, s_addr.id, other_addr.id]))

    @skipIfCustomContact
    def test_delete_contact(self):
        "Addresses are deleted when the related Contact is deleted."
        self.login(create_orga=False)

        contact = Contact.objects.create(user=self.user, first_name='Rei', last_name='Ayanami')

        create_address = Address.objects.create
        contact.billing_address = b_addr = create_address(name="Billing address",
                                                          address="BA - Address",
                                                          owner=contact,
                                                         )
        contact.save()

        contact.shipping_address = s_addr = create_address(name="Shipping address",
                                                           address="SA - Address",
                                                           owner=contact,
                                                          )
        contact.save()

        other_addr = create_address(name="Other address", address="OA - Address", owner=contact)

        contact.delete()
        self.assertDoesNotExist(contact)
        self.assertFalse(Address.objects.filter(pk__in=[b_addr.id, s_addr.id, other_addr.id]))

    @skipIfCustomContact
    def test_history(self):
        "Address is auxiliary + double save() because of addresses caused problems"
        self.login(create_orga=False)

        old_count = HistoryLine.objects.count()
        country = 'Japan'
        name = 'Gainax'
        self.assertNoFormError(self.client.post(reverse('persons__create_organisation'),
                                                follow=True,
                                                data={'name': name,
                                                      'user':  self.other_user.id,
                                                      'billing_address-country': country,
                                                     }
                                               )
                              )

        gainax = self.get_object_or_fail(Organisation, name=name)

        address = gainax.billing_address
        self.assertIsNotNone(address)
        self.assertEqual(country, address.country)

        #hlines = self._get_hlines()
        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines)) #1 creation + 1 auxiliary (NB: not edition with double save)

        hline = hlines[-2]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertEqual([],                 hline.modifications)

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION,  hline.type)
        self.assertEqual([ContentType.objects.get_for_model(address).id, address.id, unicode(address)],
                         hline.modifications
                        )
        self.assertEqual([_(u'Add <%(type)s>: “%(value)s”') % {
                                'type':  _(u'Address'),
                                'value': address,
                               }
                         ],
#                         hline.verbose_modifications
                         hline.get_verbose_modifications(self.user)
                        )
