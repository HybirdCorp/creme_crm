# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import listview as lv_form
from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import FieldsConfig
from creme.creme_core.models.history import (
    TYPE_AUX_CREATION,
    TYPE_CREATION,
    HistoryLine,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import PrettyOtherAddressesBrick
from ..forms.listview import AddressFKField
from .base import (
    Address,
    Contact,
    Organisation,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomAddress
class AddressTestCase(CremeTestCase, BrickTestCaseMixin):
    def login(self, create_orga=True, *args, **kwargs):
        super().login(*args, **kwargs)

        if create_orga:
            return Organisation.objects.create(user=self.user, name='Nerv')

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

    def test_info_names01(self):
        self.assertSetEqual(
            {
                'name', 'address', 'po_box', 'zipcode', 'city',
                'department', 'state', 'country',
            },
            {*Address.info_field_names()},
        )

    def test_info_names02(self):
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        self.assertSetEqual(
            {
                'name', 'address', 'zipcode', 'city',
                'department', 'state', 'country',
            },
            {*Address.info_field_names()}
        )

    def test_empty_fields(self):
        orga = self.login()

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
    def test_createview(self):
        orga = self.login()
        self.assertFalse(Address.objects.filter(object_id=orga.id).exists())

        context = self.assertGET200(self._build_add_url(orga)).context
        self.assertEqual(
            _('Adding address to «{entity}»').format(entity=orga),
            context.get('title'),
        )
        self.assertEqual(_('Save the address'), context.get('submit_label'))

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
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            PrettyOtherAddressesBrick.id_,
        )
        fields = {
            elt.text
            for elt in brick_node.findall(".//span[@class='address-option-value']")
        }
        self.assertIn(department, fields)
        self.assertIn(state,      fields)
        self.assertIn(country,    fields)

    @skipIfCustomOrganisation
    def test_create_billing01(self):
        orga = self.login()

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

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(city,       address.city)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.po_box)
        self.assertEqual(_('Billing address'), address.name)

        self.assertEqual(address, self.refresh(orga).billing_address)

    @skipIfCustomOrganisation
    def test_create_billing02(self):
        "FK is hidden"
        orga = self.login()

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(reverse('persons__create_billing_address', args=(orga.id,)))

    @skipIfCustomOrganisation
    def test_create_shipping(self):
        orga = self.login()
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

        addresses = Address.objects.filter(object_id=orga.id)
        self.assertEqual(1, len(addresses))

        address = addresses[0]
        self.assertEqual(country,    address.country)
        self.assertEqual(addr_value, address.address)
        self.assertEqual('',         address.zipcode)
        self.assertEqual(_('Shipping address'), address.name)

        self.assertEqual(address, self.refresh(orga).shipping_address)

    @skipIfCustomOrganisation
    def test_editview01(self):
        orga = self.login()

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
    def test_editview02(self):
        "Billing address"
        orga = self.login()

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
    def test_editview03(self):
        "Shipping address"
        orga = self.login()

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

    @skipIfCustomOrganisation
    def test_deleteview(self):
        orga = self.login()

        self._create_address(
            orga,
            'name', 'address', 'po_box', 'city', 'state', 'zipcode', 'country', 'department'
        )
        address = Address.objects.filter(object_id=orga.id)[0]
        ct = ContentType.objects.get_for_model(Address)

        self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': address.id},
        )
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

    def test_str01(self):
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

    def test_str02(self):
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
        orga = self.login()

        create_address = Address.objects.create
        orga.billing_address = b_addr = create_address(
            name='Billing address', address='BA - Address', owner=orga,
        )
        orga.save()

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
        self.login(create_orga=False)

        contact = Contact.objects.create(user=self.user, first_name='Rei', last_name='Ayanami')

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
        user = self.login(create_orga=False)

        old_count = HistoryLine.objects.count()
        country = 'Japan'
        name = 'Gainax'
        self.assertNoFormError(self.client.post(
            reverse('persons__create_organisation'),
            follow=True,
            data={
                'name': name,
                'user':  self.other_user.id,
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
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_CREATION,      hline.type)
        self.assertListEqual([],             hline.modifications)

        hline = hlines[-1]
        self.assertEqual(gainax.id,          hline.entity.id)
        self.assertEqual(gainax.entity_type, hline.entity_ctype)
        self.assertEqual(self.other_user,    hline.entity_owner)
        self.assertEqual(TYPE_AUX_CREATION,  hline.type)
        self.assertEqual(
            [ContentType.objects.get_for_model(address).id, address.id, str(address)],
            hline.modifications,
        )
        self.assertListEqual(
            [_('Add <{type}>: “{value}”').format(type=_('Address'), value=address)],
            hline.get_verbose_modifications(user),
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

    # NB: keep as example
    # def test_search_field(self):
    #     self.login(create_orga=False)
    #
    #     field = AddressFKField(
    #         cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
    #         user=self.user,
    #     )
    #
    #     expected_choices = [
    #         {'value': '',                    'label': _('All')},
    #         {'value': lv_form.NULL,          'label': _('* is empty *')},
    #         {'value': AddressFKField.FILLED, 'label': _('* filled *')},
    #     ]
    #     self.assertEqual(expected_choices, field.choices)
    #
    #     widget = field.widget
    #     self.assertIsInstance(widget, lv_form.SelectLVSWidget)
    #     self.assertEqual(expected_choices, widget.choices)
    #
    #     to_python = field.to_python
    #     self.assertEqual(Q(), to_python(value=''))
    #     self.assertEqual(Q(), to_python(value=None))
    #     self.assertEqual(Q(), to_python(value='invalid'))
    #
    #     create_orga = partial(Organisation.objects.create, user=self.user)
    #     orga1 = create_orga(name='Orga without address')
    #     orga2 = create_orga(name='Orga with empty address')
    #     orga3 = create_orga(name='Orga with blank address')
    #     orga4 = create_orga(name='Orga with address #1')
    #     orga5 = create_orga(name='Orga with address #2')
    #     orga6 = create_orga(name='Orga with empty address with a name')
    #     orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]
    #
    #     create_address = Address.objects.create
    #     addr2 = create_address(address='',                    owner=orga2)
    #     addr3 = create_address(address='   ',                 owner=orga3)
    #     addr4 = create_address(address='  42 Towel street  ', owner=orga4)
    #     addr5 = create_address(city='Neo-tokyo',              owner=orga5)
    #     addr6 = create_address(name='Billing',                owner=orga6)
    #
    #     orga2.billing_address = addr2; orga2.save()
    #     orga3.billing_address = addr3; orga3.save()
    #     orga4.billing_address = addr4; orga4.save()
    #     orga5.billing_address = addr5; orga5.save()
    #     orga6.billing_address = addr6; orga6.save()
    #
    #     # NULL ---
    #     self.assertSetEqual(
    #         {orga1, orga2, orga3, orga6},
    #         set(Organisation.objects.filter(id__in=orga_ids)
    #                                 .filter(to_python(value=lv_form.NULL))
    #            )
    #     )
    #
    #     # NOT NULL ---
    #     self.assertSetEqual(
    #         {orga4, orga5},
    #         set(Organisation.objects.filter(id__in=orga_ids)
    #                                 .filter(to_python(value=AddressFKField.FILLED))
    #            )
    #     )
    def test_search_field01(self):
        self.login(create_orga=False)

        field = AddressFKField(
            cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
            user=self.user,
        )
        self.assertIsInstance(field.widget, lv_form.TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=None))

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga1 = create_orga(name='Orga without address')
        orga2 = create_orga(name='Orga with empty address')
        orga3 = create_orga(name='Orga with address #1')
        orga4 = create_orga(name='Orga with address #2')
        orga5 = create_orga(name='Orga with address #3 (not OK)')
        orga6 = create_orga(name='Orga with named address')
        orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]

        def create_billing_address(owner, **kwargs):
            owner.billing_address = Address.objects.create(owner=owner, **kwargs)
            owner.save()

        create_billing_address(address='',                owner=orga2)
        create_billing_address(address='42 Towel street', owner=orga3)
        create_billing_address(city='TowelCity',          owner=orga4)
        create_billing_address(address='42 Fish street',  owner=orga5)
        create_billing_address(name='Towel',              owner=orga6)

        self.assertSetEqual(
            {orga3, orga4},
            {
                *Organisation.objects
                             .filter(id__in=orga_ids)
                             .filter(to_python(value='towel')),
            },
        )

    def test_search_field02(self):
        "Ignore hidden fields."
        self.login(create_orga=False)

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('city', {FieldsConfig.HIDDEN: True})],
        )

        field = AddressFKField(
            cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
            user=self.user,
        )

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga1 = create_orga(name='Orga without address')
        orga2 = create_orga(name='Orga with empty address')
        orga3 = create_orga(name='Orga with address #1')
        orga4 = create_orga(name='Orga with address #2 (hidden field)')
        orga5 = create_orga(name='Orga with address #3 (not OK)')
        orga6 = create_orga(name='Orga with named address')
        orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]

        def create_billing_address(owner, **kwargs):
            owner.billing_address = Address.objects.create(owner=owner, **kwargs)
            owner.save()

        create_billing_address(address='',                owner=orga2)
        create_billing_address(address='42 Towel street', owner=orga3)
        create_billing_address(city='TowelCity',          owner=orga4)
        create_billing_address(address='42 Fish street',  owner=orga5)
        create_billing_address(name='Towel',              owner=orga6)

        self.assertListEqual(
            [orga3],
            [
                *Organisation.objects
                             .filter(id__in=orga_ids)
                             .filter(field.to_python(value='towel')),
            ],
        )
