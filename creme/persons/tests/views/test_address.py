from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.models import FieldsConfig
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.bricks import PrettyOtherAddressesBrick

from ..base import (
    Address,
    Organisation,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomAddress
class AddressTestCase(BrickTestCaseMixin, CremeTestCase):
    def login_n_create_orga(self):
        user = self.login_as_root_and_get()

        return Organisation.objects.create(user=user, name='Nerv')

    @staticmethod
    def _build_add_url(entity):
        return reverse('persons__create_address', args=(entity.id,))

    def _create_address(self, orga, name, address='', po_box='', city='',
                        state='', zipcode='', country='', department=''):
        response = self.client.post(
            self._build_add_url(orga),
            data={
                'name':       name,
                'address':    address,
                'po_box':     po_box,
                'city':       city,
                'state':      state,
                'zipcode':    zipcode,
                'country':    country,
                'department': department,
            },
        )
        self.assertNoFormError(response)

    @skipIfCustomOrganisation
    def test_creation(self):
        orga = self.login_n_create_orga()
        self.assertFalse(Address.objects.filter(object_id=orga.id).exists())

        context = self.assertGET200(self._build_add_url(orga)).context
        self.assertEqual(
            _('Adding address to «{entity}»').format(entity=orga),
            context.get('title'),
        )
        self.assertEqual(_('Save the address'), context.get('submit_label'))

        name = 'Address#1'
        addr_value = '21 jump street'
        po_box = 'Popop'
        city = 'Atlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(
            orga, name, addr_value, po_box, city, state, zipcode, country, department,
        )

        address = self.get_alone_element(Address.objects.filter(object_id=orga.id))
        self.assertEqual(name,       address.name)
        self.assertEqual(addr_value, address.address)
        self.assertEqual(po_box,     address.po_box)
        self.assertEqual(city,       address.city)
        self.assertEqual(state,      address.state)
        self.assertEqual(zipcode,    address.zipcode)
        self.assertEqual(country,    address.country)
        self.assertEqual(department, address.department)

        now_value = now()
        self.assertDatetimesAlmostEqual(address.created, now_value)
        self.assertDatetimesAlmostEqual(address.modified, now_value)

        response = self.client.get(orga.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=PrettyOtherAddressesBrick,
        )
        fields = {
            elt.text
            for elt in brick_node.findall(".//span[@class='address-option-value']")
        }
        self.assertIn(department, fields)
        self.assertIn(state,      fields)
        self.assertIn(country,    fields)

    @skipIfCustomOrganisation
    def test_creation__billing(self):
        orga = self.login_n_create_orga()

        url = reverse('persons__create_billing_address', args=(orga.id,))
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(
            _('Adding billing address to «{entity}»').format(entity=orga),
            context.get('title'),
        )
        self.assertEqual(_('Save the address'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields

        self.assertIn('city',    fields)
        self.assertIn('address', fields)
        self.assertNotIn('name', fields)

        addr_value = '21 jump street'
        city = 'Atlantis'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'address': addr_value,
                'city':    city,
            },
        ))

        address = self.get_alone_element(Address.objects.filter(object_id=orga.id))
        self.assertEqual(city,       address.city)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.po_box)
        self.assertEqual(_('Billing address'), address.name)

        self.assertEqual(address, self.refresh(orga).billing_address)

    @skipIfCustomOrganisation
    def test_creation__billing__hidden(self):
        "FK is hidden."
        orga = self.login_n_create_orga()

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(reverse('persons__create_billing_address', args=(orga.id,)))

    @skipIfCustomOrganisation
    def test_creation__shipping(self):
        orga = self.login_n_create_orga()
        url = reverse('persons__create_shipping_address', args=(orga.id,))

        context = self.assertGET200(url).context
        self.assertEqual(
            _('Adding shipping address to «{entity}»').format(entity=orga),
            context.get('title')
        )
        self.assertEqual(_('Save the address'), context.get('submit_label'))

        addr_value = '21 jump street'
        country = 'Wonderland'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'address': addr_value,
                'country': country,
            },
        ))

        address = self.get_alone_element(Address.objects.filter(object_id=orga.id))
        self.assertEqual(country,    address.country)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.zipcode)
        self.assertEqual(_('Shipping address'), address.name)

        self.assertEqual(address, self.refresh(orga).shipping_address)

    @skipIfCustomOrganisation
    def test_edition(self):
        orga = self.login_n_create_orga()

        name = 'Address#1'
        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Atlantis'
        state = '??'
        zipcode = '424242'
        country = 'wtf'
        department = 'rucrazy'

        self._create_address(
            orga, name, address_value, po_box, city, state, zipcode, country, department,
        )
        address = Address.objects.filter(object_id=orga.id)[0]

        url = address.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit address for «{entity}»').format(entity=orga),
            response.context.get('title'),
        )

        # ---
        city = 'Groville'
        country = 'Groland'
        response = self.client.post(
            url,
            data={
                'name':       name,
                'address':    address,
                'po_box':     po_box,
                'city':       city,
                'state':      state,
                'zipcode':    zipcode,
                'country':    country,
                'department': department,
            },
        )
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city,    address.city)
        self.assertEqual(country, address.country)

    @skipIfCustomOrganisation
    def test_edition__billing(self):
        orga = self.login_n_create_orga()

        name = 'Address#1'
        address_value = '21 jump street'
        city = 'Atlantis'
        zipcode = '424242'

        self._create_address(orga, name, address_value, city=city, zipcode=zipcode)
        address = Address.objects.filter(object_id=orga.id)[0]

        url = f'{address.get_edit_absolute_url()}?type=billing'
        response = self.assertGET200(url)
        self.assertEqual(
            _('Edit billing address for «{entity}»').format(entity=orga),
            response.context.get('title'),
        )

        # --
        city = 'Groville'
        response = self.client.post(
            url,
            data={
                'name':       name,
                'address':    address,
                'city':       city,
                'zipcode':    zipcode,
            },
        )
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city, address.city)
        self.assertEqual(_('Billing address'), address.name)

    @skipIfCustomOrganisation
    def test_edition__shipping(self):
        orga = self.login_n_create_orga()

        name = 'Address#1'
        address_value = '21 jump street'
        city = 'Atlantis'
        zipcode = '424242'

        self._create_address(orga, name, address_value, city=city, zipcode=zipcode)
        address = Address.objects.filter(object_id=orga.id)[0]

        url = f'{address.get_edit_absolute_url()}?type=shipping'
        response = self.assertGET200(url)
        self.assertEqual(
            _('Edit shipping address for «{entity}»').format(entity=orga),
            response.context.get('title'),
        )

        # ---
        city = 'Groville'
        response = self.client.post(
            url,
            data={
                'name':       name,
                'address':    address,
                'city':       city,
                'zipcode':    zipcode,
            },
        )
        self.assertNoFormError(response)

        address = self.refresh(address)
        self.assertEqual(city, address.city)
        self.assertEqual(_('Shipping address'), address.name)
