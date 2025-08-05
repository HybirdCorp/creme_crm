from datetime import date
from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import FieldsConfig, Relation, RelationType
from creme.persons import constants
from creme.persons.models import LegalForm, Sector, StaffSize

from ..base import (
    Address,
    Contact,
    Organisation,
    _BaseTestCase,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomOrganisation
class OrganisationTestCase(_BaseTestCase):
    def test_empty_fields(self):
        user = self.login_as_root_and_get()

        with self.assertNoException():
            orga = Organisation.objects.create(user=user, name='Nerv')

        self.assertEqual('', orga.description)

        self.assertEqual('', orga.phone)
        self.assertEqual('', orga.fax)
        self.assertEqual('', orga.email)
        self.assertEqual('', orga.url_site)

        self.assertEqual('', orga.annual_revenue)

        self.assertEqual('', orga.siren)
        self.assertEqual('', orga.naf)
        self.assertEqual('', orga.siret)
        self.assertEqual('', orga.rcs)

        self.assertEqual('', orga.tvaintra)
        self.assertEqual('', orga.eori)

    def test_populated_orga_uuid(self):
        first_orga = Organisation.objects.order_by('id').first()
        self.assertIsNotNone(first_orga)
        self.assertTrue(first_orga.is_managed)
        self.assertUUIDEqual(constants.UUID_FIRST_ORGA, first_orga.uuid)

    def test_staff_size(self):
        count = StaffSize.objects.count()

        create_size = StaffSize.objects.create
        size1 = create_size(size='4 and a dog')
        size2 = create_size(size='1 wolf & 1 cub')
        self.assertEqual(count + 1, size1.order)
        self.assertEqual(count + 2, size2.order)

    def test_createview01(self):
        user = self.login_as_root_and_get()

        url = reverse('persons__create_organisation')
        self.assertGET200(url)

        count = Organisation.objects.count()
        name = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.pk,
                'name':        name,
                'description': description,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(description, orga.description)
        self.assertIsNone(orga.creation_date)
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        self.assertRedirects(response, orga.get_absolute_url())

    @skipIfCustomAddress
    def test_createview02(self):
        "With addresses, creation date."
        user = self.login_as_root_and_get()

        name = 'Bebop'
        creation_date = date(year=2005, month=11, day=5)

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        s_address = 'Mars gate (bis)'
        response = self.client.post(
            reverse('persons__create_organisation'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'creation_date': creation_date,

                'billing_address-address':    b_address,
                'billing_address-po_box':     b_po_box,
                'billing_address-zipcode':    b_zipcode,
                'billing_address-city':       b_city,
                'billing_address-department': b_department,
                'billing_address-state':      b_state,
                'billing_address-country':    b_country,

                'shipping_address-address': s_address,
            },
        )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(creation_date, orga.creation_date)

        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_po_box,     billing_address.po_box)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertEqual(s_address, orga.shipping_address.address)

        self.assertContains(response, b_address)
        self.assertContains(response, s_address)

    @skipIfCustomAddress
    def test_createview03(self):
        "FieldsConfig on Address sub-fields."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)

        name = 'Bebop'

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        response = self.client.post(
            reverse('persons__create_organisation'), follow=True,
            data={
                'user': user.pk,
                'name': name,

                'billing_address-address':    b_address,
                'billing_address-po_box':     b_po_box,  # <== should not be used
                'billing_address-zipcode':    b_zipcode,
                'billing_address-city':       b_city,
                'billing_address-department': b_department,
                'billing_address-state':      b_state,
                'billing_address-country':    b_country,
            },
        )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertFalse(billing_address.po_box)

    @skipIfCustomAddress
    def test_createview04(self):
        "FieldsConfig on 'billing_address' FK field."
        self.login_as_root()
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertNotIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)

    @skipIfCustomAddress
    def test_editview01(self):
        user = self.login_as_root_and_get()

        name = 'Bebop'
        orga = Organisation.objects.create(user=user, name=name)
        url = orga.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':                    user.pk,
                'name':                    name,
                'billing_address-zipcode': zipcode,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga.get_absolute_url())

        edited_orga = self.refresh(orga)
        self.assertEqual(name, edited_orga.name)
        self.assertIsNotNone(edited_orga.billing_address)
        self.assertEqual(zipcode, edited_orga.billing_address.zipcode)

    def test_listview(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        response = self.assertGET200(Organisation.get_lv_absolute_url())

        with self.assertNoException():
            orgas_page = response.context['page_obj']

        self.assertEqual(3, orgas_page.paginator.count)  # 3: our 2 orgas + default orga

        orgas_set = {*orgas_page.object_list}
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses are problematic."
        user = self.login_as_root_and_get()

        bebop = Organisation.objects.create(user=user, name='Bebop')

        create_address = partial(
            Address.objects.create,
            address='XXX',
            city='Red city', state='North', zipcode='111',
            country='Mars', department='Dome #12',
            owner=bebop,
        )
        bebop.billing_address  = create_address(name='Hideout #1')
        bebop.shipping_address = create_address(name='Hideout #2')
        bebop.save()

        for i in range(3, 5):
            create_address(name=f'Hideout #{i}')

        url = reverse('creme_core__clone_entity')
        self.assertEqual(url, bebop.get_clone_absolute_url())

        self.assertPOST200(url, data={'id': bebop.id}, follow=True)
        cloned = Organisation.objects.order_by('-id').first()

        self.assertEqual(bebop.name, cloned.name)
        self.assertFalse(cloned.is_managed)

        self.assertEqual(bebop.id, bebop.billing_address.object_id)
        self.assertEqual(bebop.id, bebop.shipping_address.object_id)

        self.assertEqual(cloned.id, cloned.billing_address.object_id)
        self.assertEqual(cloned.id, cloned.shipping_address.object_id)

        addresses   = [*Address.objects.filter(object_id=bebop.id)]
        c_addresses = [*Address.objects.filter(object_id=cloned.id)]
        self.assertEqual(4, len(addresses))
        self.assertEqual(4, len(c_addresses))

        addresses_map   = {a.name: a for a in addresses}
        c_addresses_map = {a.name: a for a in c_addresses}
        self.assertEqual(4, len(addresses_map))
        self.assertEqual(4, len(c_addresses_map))

        for ident, address in addresses_map.items():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    # def test_clone__managed(self):  # DEPRECATED
    #     "Do not clone 'is_managed'."
    #     user = self.login_as_root_and_get()
    #     bebop = Organisation.objects.create(user=user, name='Bebop', is_managed=True)
    #     self.assertPOST409(
    #         bebop.get_clone_absolute_url(), data={'id': bebop.id}, follow=True,
    #     )
    #
    #     cloned = bebop.clone()
    #     self.assertEqual(bebop.name, cloned.name)
    #     self.assertFalse(cloned.is_managed)
    #
    # @skipIfCustomAddress
    # def test_clone__method(self):  # DEPRECATED
    #     "Addresses are problematic."
    #     user = self.login_as_root_and_get()
    #
    #     bebop = Organisation.objects.create(user=user, name='Bebop')
    #
    #     create_address = partial(
    #         Address.objects.create,
    #         address='XXX',
    #         city='Red city', state='North', zipcode='111',
    #         country='Mars', department='Dome #12',
    #         owner=bebop,
    #     )
    #     bebop.billing_address  = create_address(name='Hideout #1')
    #     bebop.shipping_address = create_address(name='Hideout #2')
    #     bebop.save()
    #
    #     for i in range(3, 5):
    #         create_address(name=f'Hideout #{i}')
    #
    #     self.assertEqual(
    #         reverse('creme_core__clone_entity'),
    #         bebop.get_clone_absolute_url(),
    #     )
    #
    #     cloned = bebop.clone()
    #
    #     self.assertEqual(bebop.name, cloned.name)
    #     self.assertFalse(cloned.is_managed)
    #
    #     self.assertEqual(bebop.id, bebop.billing_address.object_id)
    #     self.assertEqual(bebop.id, bebop.shipping_address.object_id)
    #
    #     self.assertEqual(cloned.id, cloned.billing_address.object_id)
    #     self.assertEqual(cloned.id, cloned.shipping_address.object_id)
    #
    #     addresses   = [*Address.objects.filter(object_id=bebop.id)]
    #     c_addresses = [*Address.objects.filter(object_id=cloned.id)]
    #     self.assertEqual(4, len(addresses))
    #     self.assertEqual(4, len(c_addresses))
    #
    #     addresses_map   = {a.name: a for a in addresses}
    #     c_addresses_map = {a.name: a for a in c_addresses}
    #     self.assertEqual(4, len(addresses_map))
    #     self.assertEqual(4, len(c_addresses_map))
    #
    #     for ident, address in addresses_map.items():
    #         address2 = c_addresses_map.get(ident)
    #         self.assertIsNotNone(address2, ident)
    #         self.assertAddressOnlyContentEqual(address, address2)

    def _build_managed_orga(self, user, name='Bebop'):
        return Organisation.objects.create(user=user, name=name, is_managed=True)

    def test_manager_filter_managed_by_creme(self):
        user = self.login_as_root_and_get()

        mng_orga1 = self._build_managed_orga(user=user)
        mng_orga2 = self._build_managed_orga(user=user, name='NERV')
        orga = Organisation.objects.create(user=user, name='Seele')

        with self.assertNumQueries(1):
            qs1 = Organisation.objects.filter_managed_by_creme()
            mng_orgas = {*qs1}

        self.assertIn(mng_orga1, mng_orgas)
        self.assertIn(mng_orga2, mng_orgas)
        self.assertNotIn(orga,   mng_orgas)

        # Test request-cache
        with self.assertNumQueries(0):
            qs2 = Organisation.objects.filter_managed_by_creme()
            [*qs2]  # NOQA

        self.assertEqual(id(qs1), id(qs2))

    def _become_test(self, url_name, relation_type_id):
        user = self.login_as_root_and_get()

        mng_orga = self._build_managed_orga(user=user)
        customer = Contact.objects.create(user=user, first_name='Jet', last_name='Black')

        url = reverse(url_name, args=(customer.id,))
        data = {'id': mng_orga.id}
        self.assertPOST200(url, data=data, follow=True)
        self.assertHaveRelation(subject=customer, type=relation_type_id, object=mng_orga)

        # POST twice
        self.assertPOST200(url, data=data, follow=True)
        self.assertHaveRelation(subject=customer, type=relation_type_id, object=mng_orga)

    def test_get_employees(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Red tail')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Spike',   last_name='Spiegel')
        c2 = create_contact(first_name='Jet',     last_name='Black')
        c3 = create_contact(first_name='Faye',    last_name='Valentine')
        c4 = create_contact(first_name='Edward',  last_name='Wong')
        c5 = create_contact(first_name='Number2', last_name='Droid', is_deleted=True)

        create_relation = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_EMPLOYED_BY,
        )
        create_relation(subject_entity=c1, object_entity=orga1)
        create_relation(subject_entity=c2, object_entity=orga1)
        create_relation(subject_entity=c3, object_entity=orga1, type_id=constants.REL_SUB_MANAGES)
        create_relation(subject_entity=c4, object_entity=orga2)
        create_relation(subject_entity=c5, object_entity=orga1)

        self.assertListEqual([c2, c1], [*orga1.get_employees()])

    def test_get_managers(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Red tail')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Spike',   last_name='Spiegel')
        c2 = create_contact(first_name='Jet',     last_name='Black')
        c3 = create_contact(first_name='Faye',    last_name='Valentine')
        c4 = create_contact(first_name='Edward',  last_name='Wong')
        c5 = create_contact(first_name='Number2', last_name='Droid', is_deleted=True)

        create_relation = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_MANAGES,
        )
        create_relation(subject_entity=c1, object_entity=orga1)
        create_relation(subject_entity=c2, object_entity=orga1)
        create_relation(
            subject_entity=c3, object_entity=orga1, type_id=constants.REL_SUB_EMPLOYED_BY,
        )
        create_relation(subject_entity=c4, object_entity=orga2)
        create_relation(subject_entity=c5, object_entity=orga1)

        self.assertListEqual([c2, c1], [*orga1.get_managers()])

    def test_leads_customers01(self):
        user = self.login_as_root_and_get()

        self._build_managed_orga(user=user)
        Organisation.objects.create(user=user, name='Nerv')

        response = self.assertGET200(reverse('persons__leads_customers'))
        ctxt = response.context

        with self.assertNoException():
            orgas_page = ctxt['page_obj']
            title = ctxt['list_title']

        self.assertEqual(0, orgas_page.paginator.count)
        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items='{}, {}'.format(_('customers'), _('prospects')),
                last_related=_('suspects'),
            ),
            title,
        )

    def test_leads_customers02(self):
        user = self.login_as_root_and_get()

        mng_orga = self._build_managed_orga(user=user)

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        fsf  = create_orga(name='FSF')
        evil = create_orga(name='EvilCorp')

        def create_relation(orga, rtype_id):
            Relation.objects.create(
                user=user,
                subject_entity=orga,
                object_entity=mng_orga,
                type_id=rtype_id,
            )

        create_relation(nerv, constants.REL_SUB_CUSTOMER_SUPPLIER)
        create_relation(acme, constants.REL_SUB_PROSPECT)
        create_relation(fsf,  constants.REL_SUB_SUSPECT)

        response = self.client.get(reverse('persons__leads_customers'))
        orgas_page = response.context['page_obj']

        self.assertEqual(3, orgas_page.paginator.count)

        orgas_set = {*orgas_page.object_list}
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)
        self.assertIn(fsf,  orgas_set)
        self.assertNotIn(evil, orgas_set)

    def test_leads_customers03(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        Relation.objects.create(
            user=user,
            subject_entity=acme,
            object_entity=nerv,
            type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
        )

        response = self.client.get(reverse('persons__leads_customers'))
        self.assertEqual(0, response.context['page_obj'].paginator.count)

    def test_leads_customers_disabled_rtypes01(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_SUSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items=_('customers'),
                last_related=_('prospects'),
            ),
            title,
        )

    def test_leads_customers_disabled_rtypes02(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_PROSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items=_('customers'),
                last_related=_('suspects'),
            ),
            title,
        )

    def test_leads_customers_disabled_rtypes03(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(
                id__in=[constants.REL_SUB_PROSPECT, constants.REL_SUB_SUSPECT],
            ),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()

        self.assertEqual(
            _('List of my {related}').format(related=_('customers')),
            title,
        )

    def test_leads_customers_disabled_rtypes04(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(id__in=[
                constants.REL_SUB_PROSPECT,
                constants.REL_SUB_SUSPECT,
                constants.REL_SUB_CUSTOMER_SUPPLIER,
            ]),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            self.assertGET409(reverse('persons__leads_customers'))
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()

    def test_create_customer01(self):
        user = self.login_as_root_and_get()

        managed1 = self.get_object_or_fail(Organisation, is_managed=True)
        managed2 = Organisation.objects.create(user=user, name='Nerv', is_managed=True)

        url = reverse('persons__create_customer')
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            fields = context1['form'].fields
            rtypes_f = fields['customers_rtypes']
            title = context1['title']

        self.assertEqual(_('Relationships'), rtypes_f.label)
        self.assertInChoices(
            value=constants.REL_SUB_CUSTOMER_SUPPLIER,
            label=_('Is a customer'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_PROSPECT,
            label=_('Is a prospect'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_SUSPECT,
            label=_('Is a suspect'),
            choices=rtypes_f.choices,
        )

        self.assertIn('customers_managed_orga', fields)
        self.assertEqual(
            pgettext('persons-related_creation', 'Create a: {}').format(
                f"{_('customer')}, {_('prospect')}, {_('suspect')}"
            ),
            title,
        )

        def post(managed, name):
            post_response = self.client.post(
                url, follow=True,
                data={
                    'user':  user.id,
                    'name':  name,

                    'customers_managed_orga': managed.id,
                    'customers_rtypes': [constants.REL_SUB_SUSPECT],
                },
            )
            self.assertNoFormError(post_response)

            return self.get_object_or_fail(Organisation, name=name)

        # ----
        orga1 = post(managed2, name='Bebop')
        self.assertHaveNoRelation(orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed2)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_PROSPECT,          managed2)
        self.assertHaveRelation(orga1, constants.REL_SUB_SUSPECT, managed2)

        self.assertHaveNoRelation(orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed1)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_PROSPECT,          managed1)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_SUSPECT,           managed1)

        # ----
        orga2 = post(managed1, name='Red dragons')
        self.assertHaveRelation(subject=orga2, type=constants.REL_SUB_SUSPECT, object=managed1)
        self.assertHaveNoRelation(subject=orga2, type=constants.REL_SUB_SUSPECT, object=managed2)

    def test_create_customer02(self):
        "Not super-user."
        user = self.login_as_persons_user(creatable_models=[Organisation])
        self.add_credentials(user.role, all='!LINK', own='*')

        managed1 = self.get_object_or_fail(Organisation, is_managed=True)
        self.assertFalse(user.has_perm_to_link(managed1))

        managed2 = Organisation.objects.create(user=user, name='Nerv', is_managed=True)
        self.assertTrue(user.has_perm_to_link(managed2))

        url = reverse('persons__create_customer')
        name = 'Bebop'
        data = {
            'user': user.id,
            'name': name,

            'customers_managed_orga': managed1.id,
            'customers_rtypes': [constants.REL_SUB_SUSPECT],
        }
        response1 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response1.context['form'],
            field='customers_managed_orga',
            errors=_('You are not allowed to link this entity: {}').format(managed1),
        )

        # ---
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'user': self.get_root_user().id,  # <==
                'customers_managed_orga': managed2.id,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='user',
            errors=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models=_('Organisations')),
        )

        # ---
        response3 = self.assertPOST200(
            url, follow=True,
            data={**data, 'customers_managed_orga': managed2.id},
        )
        self.assertNoFormError(response3)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertHaveRelation(subject=orga, type=constants.REL_SUB_SUSPECT, object=managed2)

    def test_create_customer03(self):
        "Can never link."
        user = self.login_as_standard(creatable_models=[Organisation])
        self.add_credentials(user.role, all='!LINK')
        self.assertPOST403(reverse('persons__create_customer'))

    def test_create_customer_disabled_rtype01(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_SUSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            context = self.assertGET200(reverse('persons__create_customer')).context

            with self.assertNoException():
                rtypes_f = context['form'].fields['customers_rtypes']
                title = context['title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            pgettext('persons-related_creation', 'Create a: {}').format(
                f"{_('customer')}, {_('prospect')}"
            ),
            title,
        )

        self.assertInChoices(
            value=constants.REL_SUB_CUSTOMER_SUPPLIER,
            label=_('Is a customer'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_PROSPECT,
            label=_('Is a prospect'),
            choices=rtypes_f.choices,
        )
        self.assertNotInChoices(
            value=constants.REL_SUB_SUSPECT, choices=rtypes_f.choices,
        )

    def test_create_customer_disabled_rtype02(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(id__in=[
                constants.REL_SUB_PROSPECT,
                constants.REL_SUB_SUSPECT,
                constants.REL_SUB_CUSTOMER_SUPPLIER,
            ]),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            self.assertGET409(reverse('persons__create_customer'))
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete01(self):
        user = self.login_as_root_and_get()
        orga01 = Organisation.objects.create(user=user, name='Nerv')
        url = orga01.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        self.assertIs(orga01.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(orga01)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete02(self):
        "Cannot delete the last managed organisation."
        self.login_as_root()

        managed_orga = self.get_alone_element(Organisation.objects.filter(is_managed=True))
        self.assertPOST409(managed_orga.get_delete_absolute_url())  # follow=True
        self.assertStillExists(managed_orga)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete03(self):
        "A managed organisation can be deleted if it's not the last one."
        user = self.login_as_root_and_get()

        managed_orga = Organisation.objects.create(user=user, name='Nerv', is_managed=True)
        url = managed_orga.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            managed_orga = self.refresh(managed_orga)

        self.assertIs(managed_orga.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(managed_orga)

    def test_delete_sector01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=user, name='Bebop', sector=hunting)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'sector', hunting.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(hunting)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.sector)

    def test_delete_sector02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        sector2 = Sector.objects.first()
        hunting = Sector.objects.create(title='Bounty hunting')
        bebop = Organisation.objects.create(user=user, name='Bebop', sector=hunting)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'sector', hunting.id),
            ),
            data={'replace_persons__organisation_sector': sector2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(hunting)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(sector2, bebop.sector)

    def test_delete_legal_form01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=user, name='Bebop', legal_form=band)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'legal_form', band.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(LegalForm).job
        job.type.execute(job)
        self.assertDoesNotExist(band)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.legal_form)

    def test_delete_legal_form02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        lform2 = LegalForm.objects.first()
        band = LegalForm.objects.create(title='Bounty hunting band')
        bebop = Organisation.objects.create(user=user, name='Bebop', legal_form=band)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'legal_form', band.id)
            ),
            data={'replace_persons__organisation_legal_form': lform2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(LegalForm).job
        job.type.execute(job)
        self.assertDoesNotExist(band)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(lform2, bebop.legal_form)

    def test_delete_staff_size01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=user, name='Bebop', staff_size=size)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'staff_size', size.id)
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(StaffSize).job
        job.type.execute(job)
        self.assertDoesNotExist(size)

        bebop = self.assertStillExists(bebop)
        self.assertIsNone(bebop.staff_size)

    def test_delete_staff_size02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        size2 = StaffSize.objects.first()
        size = StaffSize.objects.create(size='4 and a dog')
        bebop = Organisation.objects.create(user=user, name='Bebop', staff_size=size)

        response = self.client.post(
            reverse(
                'creme_config__delete_instance', args=('persons', 'staff_size', size.id)
            ),
            data={'replace_persons__organisation_staff_size': size2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(StaffSize).job
        job.type.execute(job)
        self.assertDoesNotExist(size)

        bebop = self.assertStillExists(bebop)
        self.assertEqual(size2, bebop.staff_size)

    def test_set_orga_as_managed01(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Swordfish')
        orga3 = create_orga(name='RedTail')

        url = reverse('persons__orga_set_managed')
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        get_ctxt = response1.context.get
        self.assertEqual(_('Add some managed organisations'), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),         get_ctxt('submit_label'))

        # ---
        response2 = self.client.post(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1, orga2)},
        )
        self.assertNoFormError(response2)

        self.assertTrue(self.refresh(orga1).is_managed)
        self.assertTrue(self.refresh(orga2).is_managed)
        self.assertFalse(self.refresh(orga3).is_managed)

        # Managed Organisations are excluded
        response3 = self.assertPOST200(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1)},
        )
        self.assertFormError(
            response3.context['form'],
            field='organisations',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': orga1},
        )

    def test_set_orga_as_managed02(self):
        "Not super-user."
        self.login_as_persons_user(
            allowed_apps=['creme_core'],
            admin_4_apps=['creme_core'],
        )
        self.assertGET200(reverse('persons__orga_set_managed'))

    def test_set_orga_as_managed03(self):
        "Admin permission needed."
        self.login_as_persons_user(
            allowed_apps=['creme_core'],
            # admin_4_apps=['creme_core'],
        )
        self.assertGET403(reverse('persons__orga_set_managed'))

    def test_set_orga_as_not_managed(self):
        user = self.login_as_root_and_get()

        orga1 = self.get_alone_element(Organisation.objects.filter(is_managed=True))
        orga2 = self._build_managed_orga(user=user)

        url = reverse('persons__orga_unset_managed')
        data = {'id': orga2.id}
        self.assertGET405(url)
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertFalse(self.refresh(orga2).is_managed)

        self.assertPOST409(url, data={'id': orga1.id})  # At least 1 managed organisation
        self.assertTrue(self.refresh(orga1).is_managed)
