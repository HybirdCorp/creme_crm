from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import FieldsConfig
from creme.creme_core.models.history import (
    TYPE_AUX_CREATION,
    TYPE_CREATION,
    HistoryLine,
)
from creme.creme_core.tests.base import CremeTestCase

from ..base import (
    Address,
    Contact,
    Organisation,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomAddress
class AddressTestCase(CremeTestCase):
    def test_info_names(self):
        self.assertSetEqual(
            {
                'name', 'address', 'po_box', 'zipcode', 'city',
                'department', 'state', 'country',
            },
            {*Address.info_field_names()},
        )

    def test_info_names__hidden(self):
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        self.assertSetEqual(
            {
                'name', 'address', 'zipcode', 'city',
                'department', 'state', 'country',
            },
            {*Address.info_field_names()},
        )

    def test_empty_fields(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Nerv')

        with self.assertNoException():
            address = Address.objects.create(owner=orga)

        self.assertEqual('', address.name)
        self.assertEqual('', address.address)
        self.assertEqual('', address.po_box)
        self.assertEqual('', address.zipcode)
        self.assertEqual('', address.city)
        self.assertEqual('', address.department)
        self.assertEqual('', address.state)
        self.assertEqual('', address.country)

    @skipIfCustomOrganisation
    def test_deletion(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Nerv')
        address = Address.objects.create(
            owner=orga, name='Other address', city='Metropolis',
        )
        ct = ContentType.objects.get_for_model(Address)

        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True,
            data={'id': address.id},
        )
        self.assertDoesNotExist(address)

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

    def test_str(self):
        address_value = '21 jump street'
        po_box = 'Popop'
        zipcode = '424242'
        city = 'Atlantis'
        department = 'rucrazy'
        state = '??'
        country = 'wtf'

        address = Address(
            name='Address#1',
            address=address_value,
            po_box=po_box,
            zipcode=zipcode,
            city=city,
            department=department,
            state=state,
            country=country,
        )
        self.assertEqual(
            f'{address_value} {zipcode} {city} {department}',
            str(address),
        )

        address.zipcode = None
        self.assertEqual(f'{address_value} {city} {department}', str(address))

        address.department = None
        self.assertEqual(f'{address_value} {city}', str(address))

        self.assertEqual(po_box, str(Address(po_box=po_box)))
        self.assertEqual(state, str(Address(state=state)))
        self.assertEqual(country, str(Address(country=country)))

        self.assertEqual(
            f'{po_box} {state} {country}',
            str(Address(po_box=po_box, state=state, country=country)),
        )

    def test_str__hidden(self):
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[
                ('zipcode',    {FieldsConfig.HIDDEN: True}),
                ('department', {FieldsConfig.HIDDEN: True}),
                ('state',      {FieldsConfig.HIDDEN: True}),
            ],
        )

        address_value = '21 jump street'
        po_box = 'Popop'
        city = 'Atlantis'
        state = '??'
        address = Address(
            name='Address#1',
            address=address_value,
            po_box=po_box,
            zipcode='424242',
            city=city,
            department='rucrazy',
            state=state,
            country='wtf',
        )
        self.assertEqual(f'{address_value} {city}', str(address))

        self.assertEqual(po_box, str(Address(po_box=po_box, state=state)))

    @skipIfCustomOrganisation
    def test_delete_orga(self):
        "Addresses are deleted when the related Organisation is deleted."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Nerv')

        create_address = Address.objects.create
        orga.billing_address = b_addr = create_address(
            name='Billing address', address='BA - Address', owner=orga,
        )
        orga.shipping_address = s_addr = create_address(
            name='Shipping address', address='SA - Address', owner=orga,
        )
        orga.save()

        other_addr = create_address(
            name='Other address', address='OA - Address', owner=orga,
        )

        orga.delete()
        self.assertDoesNotExist(orga)
        self.assertFalse(Address.objects.filter(pk__in=[b_addr.id, s_addr.id, other_addr.id]))

    @skipIfCustomContact
    def test_delete_contact(self):
        "Addresses are deleted when the related Contact is deleted."
        user = self.login_as_root_and_get()

        contact = Contact.objects.create(user=user, first_name='Rei', last_name='Ayanami')

        create_address = partial(Address.objects.create, owner=contact)
        contact.billing_address = b_addr = create_address(
            name='Billing address', address='BA - Address',
        )
        contact.shipping_address = s_addr = create_address(
            name='Shipping address', address='SA - Address',
        )
        contact.save()

        other_addr = create_address(name='Other address', address='OA - Address')

        contact.delete()
        self.assertDoesNotExist(contact)
        self.assertFalse(Address.objects.filter(pk__in=[b_addr.id, s_addr.id, other_addr.id]))

    @skipIfCustomContact
    def test_history(self):
        "Address is auxiliary + double save() because of addresses caused problems."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        old_count = HistoryLine.objects.count()
        country = 'Japan'
        name = 'Gainax'
        self.assertNoFormError(self.client.post(
            reverse('persons__create_organisation'),
            follow=True,
            data={
                'name': name,
                'user':  other_user.id,
                'billing_address-country': country,
            },
        ))

        gainax = self.get_object_or_fail(Organisation, name=name)

        address = gainax.billing_address
        self.assertIsNotNone(address)
        self.assertEqual(country, address.country)

        hlines = [*HistoryLine.objects.order_by('id')]
        # 1 creation + 1 auxiliary (NB: not edition with double save)
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-2]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(other_user,         hline.entity_owner)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertListEqual([],             hline.modifications)

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(other_user,         hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION,  hline.type)
        self.assertEqual(
            [ContentType.objects.get_for_model(address).id, address.id, str(address)],
            hline.modifications,
        )
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_creation">{}<div>',
                _('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': _('Address'),
                    'auxiliary_value': address,
                }
            ),
            html_history_registry.line_explainers([hline], user)[0].render(),
        )
