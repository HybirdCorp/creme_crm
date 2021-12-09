# -*- coding: utf-8 -*-

from functools import partial

from django.template import Context, Template
from django.utils.translation import gettext as _

from creme import persons
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.models import Relation, SetCredentials
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.models import Civility

Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class PersonsTagsTestCase(CremeTestCase):
    def test_persons_pretty_address01(self):
        "<address> & <po_box> fields."
        address1 = Address(address='742 Evergreen Terrace')
        address2 = Address(po_box='123456')
        address3 = Address(address=address1.address, po_box=address2.po_box)

        with self.assertNoException():
            render = Template(
                r'{% load persons_tags %}'
                r'{{address1|persons_pretty_address}}'
                r'#{{address2|persons_pretty_address}}'
                r'#{{address3|persons_pretty_address}}'
            ).render(Context({
                'address1': address1,
                'address2': address2,
                'address3': address3,
            }))

        self.assertEqual(
            f'{address1.address}'
            f'#{address2.po_box}'
            f'#{address3.address}\n{address3.po_box}',
            render.strip(),
        )

    def test_persons_pretty_address02(self):
        "Zip code & city."
        address1 = Address(zipcode='123')
        address2 = Address(city='Springfield')
        address3 = Address(city='Shelbyville', zipcode='124')

        with self.assertNoException():
            render = Template(
                r'{% load persons_tags %}'
                r'{{address1|persons_pretty_address}}'
                r'#{{address2|persons_pretty_address}}'
                r'#{{address3|persons_pretty_address}}'
            ).render(Context({
                'address1': address1,
                'address2': address2,
                'address3': address3,
            }))

        self.assertEqual(
            # f'{address1.zipcode}#{address2.city}#{address3.city} {address3.zipcode}',
            f'{address1.zipcode}#{address2.city}#{address3.zipcode} {address3.city}',
            render.strip(),
        )

    def test_persons_pretty_address03(self):
        "Address & City."
        address = Address(address='742 Evergreen Terrace', city='Springfield')

        with self.assertNoException():
            render = Template(
                r'{% load persons_tags %}'
                r'{{address|persons_pretty_address}}'
            ).render(Context({'address': address}))

        self.assertEqual(
            f'{address.address}\n{address.city}',
            render.strip(),
        )

    def test_persons_pretty_contact(self):
        civ = Civility(title='Mister', shortcut='Mr')
        contact1 = Contact(civility=civ, first_name='Homer', last_name='Simpson')
        contact2 = Contact(first_name='Bartholomew', last_name='Simpson')
        contact3 = Contact(
            civility=Civility(title='No shortcut'),
            first_name='Lisa', last_name='Simpson',
        )
        contact4 = Contact(last_name='Moleman')
        contact5 = Contact()

        with self.assertNoException():
            render = Template(
                r'{% load persons_tags %}'
                r'{{contact1|persons_pretty_contact}}'
                r'#{{contact2|persons_pretty_contact}}'
                r'#{{contact3|persons_pretty_contact}}'
                r'#{{contact4|persons_pretty_contact}}'
                r'#{{contact5|persons_pretty_contact}}#'
            ).render(Context({
                'contact1': contact1,
                'contact2': contact2,
                'contact3': contact3,
                'contact4': contact4,
                'contact5': contact5,
            }))

        self.assertEqual(
            '{}#{}#{}#{}##'.format(
                _('{civility} {first_name} {last_name}').format(
                    civility=civ.shortcut,
                    first_name=contact1.first_name,
                    last_name=contact1.last_name.upper(),
                ),
                _('{first_name} {last_name}').format(
                    first_name=contact2.first_name,
                    last_name=contact2.last_name.upper(),
                ),
                _('{first_name} {last_name}').format(
                    first_name=contact3.first_name,
                    last_name=contact3.last_name.upper(),
                ),
                contact4.last_name.upper(),
            ),
            render.strip(),
        )

    def test_persons_contact_first_employer01(self):
        user = self.create_user()
        contact = Contact.objects.create(user=user, first_name='Homer', last_name='Simpson')

        with self.assertNoException():
            render1 = Template(
                r'{% load persons_tags %}'
                r'{% persons_contact_first_employer contact=contact user=user as employer %}'
                r'{% if employer %}ERROR{% endif %}'
            ).render(Context({'contact': contact, 'user': user}))

        self.assertEqual('', render1.strip())

        # ---
        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Nuclear plant')

        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(type_id=REL_SUB_EMPLOYED_BY, object_entity=orga1)

        with self.assertNoException():
            render2 = Template(
                r'{% load persons_tags %}'
                r'{% persons_contact_first_employer contact=contact user=user as employer %}'
                r'{% if employer.as_manager %}ERROR{% endif %}'
                r'{{employer.organisation}}'
            ).render(Context({'contact': contact, 'user': user}))

        self.assertEqual(str(orga1), render2.strip())

        # ---
        orga2 = create_orga(name='Super internet 2000')
        create_rel(type_id=REL_SUB_MANAGES, object_entity=orga2)

        with self.assertNoException():
            render3 = Template(
                r'{% load persons_tags %}'
                r'{% persons_contact_first_employer contact=contact user=user as employer %}'
                r'{% if not employer.as_manager %}ERROR{% endif %}'
                r'{{employer.organisation}}'
            ).render(Context({'contact': contact, 'user': user}))

        self.assertEqual(str(orga2), render3.strip())

    def test_persons_contact_first_employer02(self):
        "Deleted organisations."
        user = self.create_user()
        contact = Contact.objects.create(user=user, first_name='Homer', last_name='Simpson')

        create_orga = partial(Organisation.objects.create, user=user, is_deleted=True)
        orga1 = create_orga(name='Nuclear plant')

        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(type_id=REL_SUB_EMPLOYED_BY, object_entity=orga1)

        template = Template(
            r'{% load persons_tags %}'
            r'{% persons_contact_first_employer contact=contact user=user as employer %}'
            r'{% if employer %}ERROR{% endif %}'
        )
        ctxt = Context({'contact': contact, 'user': user})

        with self.assertNoException():
            render1 = template.render(ctxt)

        self.assertEqual('', render1.strip())

        # ---
        orga2 = create_orga(name='Super internet 2000')
        create_rel(type_id=REL_SUB_MANAGES, object_entity=orga2)

        with self.assertNoException():
            render2 = template.render(ctxt)

        self.assertEqual('', render2.strip())

    def test_persons_contact_first_employer03(self):
        "Not viewable organisations."
        user = self.login(is_superuser=False, allowed_apps=['persons'])
        other_user = self.other_user
        contact = Contact.objects.create(user=user, first_name='Homer', last_name='Simpson')

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = Organisation.objects.create
        orga1 = create_orga(name='Nuclear plant#1', user=other_user)
        orga2 = create_orga(name='Mega internet 2000', user=other_user)

        create_rel = partial(Relation.objects.create, user=user, subject_entity=contact)
        create_rel(type_id=REL_SUB_EMPLOYED_BY, object_entity=orga1)
        create_rel(type_id=REL_SUB_MANAGES, object_entity=orga2)

        template = Template(
            r'{% load persons_tags %}'
            r'{% persons_contact_first_employer contact=contact user=user as employer %}'
            r'{% if employer %}ERROR{% endif %}'
        )
        ctxt = Context({'contact': contact, 'user': user})

        with self.assertNoException():
            render1 = template.render(ctxt)

        self.assertEqual('', render1.strip())

        # ---
        orga3 = create_orga(name='Nuclear plant', user=user)
        create_rel(type_id=REL_SUB_EMPLOYED_BY, object_entity=orga3)

        with self.assertNoException():
            render2 = Template(
                r'{% load persons_tags %}'
                r'{% persons_contact_first_employer contact=contact user=user as employer %}'
                r'{% if employer.as_manager %}ERROR{% endif %}'
                r'{{employer.organisation}}'
            ).render(Context({'contact': contact, 'user': user}))

        self.assertEqual(str(orga3), render2.strip())

        # ---
        orga4 = create_orga(name='Super internet 2000', user=user)
        create_rel(type_id=REL_SUB_MANAGES, object_entity=orga4)

        with self.assertNoException():
            render3 = Template(
                r'{% load persons_tags %}'
                r'{% persons_contact_first_employer contact=contact user=user as employer %}'
                r'{% if not employer.as_manager %}ERROR{% endif %}'
                r'{{employer.organisation}}'
            ).render(Context({'contact': contact, 'user': user}))

        self.assertEqual(str(orga4), render3.strip())

    def test_persons_addresses_formblock_fields01(self):
        "1 FK, 1 field."
        user = self.create_user()

        class ContactForm(CremeEntityForm):
            class Meta(CremeEntityForm.Meta):
                model = Contact
                fields = ('user', 'first_name', 'last_name')

            def __init__(this, *args, **kwargs):
                super().__init__(*args, **kwargs)
                this.fields['billing_address-city'] = Address._meta.get_field('city').formfield()

        with self.assertNoException():
            render = Template(
                r'{% load persons_tags %}'
                r'{% persons_addresses_formblock_fields'
                r' form=form'
                r' address_fks=fks'
                r' zip_fields=False'
                r' as info %}'
                r'<form>'
                r'  <span data-prefix="{{info.grouped_meta.0.prefix}}">'
                r'  {{info.grouped_meta.0.title}}'
                r'  </span>'
                r'  {{info.grouped_fields.0.0}}'
                r'</form>'
            ).render(Context({
                'form': ContactForm(user=user),
                'fks': [Contact._meta.get_field('billing_address')],
            }))

        self.assertHTMLEqual(
            f'<form>'
            f' <span data-prefix="billing_address">{_("Billing address")}</span>'
            f' <input type="text" name="billing_address-city" maxlength="100"'
            f'        id="id_billing_address-city">'
            f'</form>',
            render,
        )

    def test_persons_addresses_formblock_fields02(self):
        "2 FKs, 2 fields."
        user = self.create_user()

        fks = [
            Contact._meta.get_field(fname)
            for fname in ('billing_address', 'shipping_address')
        ]

        class ContactForm(CremeEntityForm):
            class Meta(CremeEntityForm.Meta):
                model = Contact
                fields = ('user', 'first_name', 'last_name')

            def __init__(this, *args, **kwargs):
                super().__init__(*args, **kwargs)
                fields = this.fields

                get_addr_field = Address._meta.get_field
                city_field = get_addr_field('city')
                zipcode_field = get_addr_field('zipcode')

                fields['billing_address-city'] = city_field.formfield()
                fields['billing_address-zipcode'] = zipcode_field.formfield()

                fields['shipping_address-city'] = city_field.formfield()
                fields['shipping_address-zipcode'] = zipcode_field.formfield()

        form = ContactForm(user=user)

        # <zip_fields=False> ---
        with self.assertNoException():
            render1 = Template(
                r'{% load persons_tags %}'
                r'{% persons_addresses_formblock_fields'
                r' form=form'
                r' address_fks=fks'
                r' zip_fields=False'
                r' as info %}'
                r'<form>'
                r'  <span data-prefix="{{info.grouped_meta.0.prefix}}">'
                r'  {{info.grouped_meta.0.title}}'
                r'  </span>'
                r'  {{info.grouped_fields.0.0}}'
                r'  {{info.grouped_fields.0.1}}'
                r'  <span data-prefix="{{info.grouped_meta.1.prefix}}">'
                r'  {{info.grouped_meta.1.title}}'
                r'  </span>'
                r'  {{info.grouped_fields.1.0}}'
                r'  {{info.grouped_fields.1.1}}'
                r'</form>'
            ).render(Context({'form': form, 'fks': fks}))

        self.assertHTMLEqual(
            f'<form>'
            f'  <span data-prefix="billing_address">{_("Billing address")}</span>'
            f'  <input type="text" maxlength="100" name="billing_address-city"'
            f'   id="id_billing_address-city">'
            f'  <input type="text" maxlength="100" name="billing_address-zipcode"'
            f'   id="id_billing_address-zipcode">'

            f'  <span data-prefix="shipping_address">{_("Shipping address")}</span>'
            f'  <input type="text" maxlength="100" name="shipping_address-city"'
            f'         id="id_shipping_address-city">'
            f'  <input type="text" maxlength="100" name="shipping_address-zipcode"'
            f'         id="id_shipping_address-zipcode">'
            f'</form>',
            render1,
        )

        # <zip_fields=True> ---
        with self.assertNoException():
            render2 = Template(
                r'{% load persons_tags %}'
                r'{% persons_addresses_formblock_fields'
                r' form=form'
                r' address_fks=fks'
                r' as info %}'
                r'<form>'
                r'  <span data-prefix="{{info.grouped_meta.0.prefix}}">'
                r'  {{info.grouped_meta.0.title}}'
                r'  </span>'
                r'  <span data-prefix="{{info.grouped_meta.1.prefix}}">'
                r'  {{info.grouped_meta.1.title}}'
                r'  </span>'
                r'  <div>'
                r'    {{info.grouped_fields.0.0}}'
                r'    {{info.grouped_fields.0.1}}'
                r'  </div>'
                r'  <div>'
                r'    {{info.grouped_fields.1.0}}'
                r'    {{info.grouped_fields.1.1}}'
                r'  </div>'
                r'</form>'
            ).render(Context({'form': form, 'fks': fks}))

        self.assertHTMLEqual(
            f'<form>'
            f'  <span data-prefix="billing_address">{_("Billing address")}</span>'
            f'  <span data-prefix="shipping_address">{_("Shipping address")}</span>'
            f'  <div>'
            f'    <input type="text" maxlength="100" name="billing_address-city"'
            f'           id="id_billing_address-city">'
            f'     <input type="text" maxlength="100" name="shipping_address-city"'
            f'            id="id_shipping_address-city">'
            f'  </div>'
            f'  <div>'
            f'     <input type="text" maxlength="100" name="billing_address-zipcode"'
            f'            id="id_billing_address-zipcode">'
            f'     <input type="text" maxlength="100" name="shipping_address-zipcode"'
            f'            id="id_shipping_address-zipcode">'
            f'  </div>'
            f'</form>',
            render2,
        )
