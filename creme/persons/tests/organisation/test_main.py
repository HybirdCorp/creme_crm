# -*- coding: utf-8 -*-

from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FieldsConfig, Relation, SetCredentials
from creme.persons import constants
from creme.persons.models import LegalForm, Sector, StaffSize

from ..base import (  # skipIfCustomContact
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
        user = self.login()

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

    def test_populated_orga_uuid(self):
        first_orga = Organisation.objects.order_by('id').first()
        self.assertIsNotNone(first_orga)
        self.assertTrue(first_orga.is_managed)
        self.assertEqual(constants.UUID_FIRST_ORGA, str(first_orga.uuid))

    def test_staff_size(self):
        count = StaffSize.objects.count()

        create_size = StaffSize.objects.create
        size1 = create_size(size='4 and a dog')
        size2 = create_size(size='1 wolf & 1 cub')
        self.assertEqual(count + 1, size1.order)
        self.assertEqual(count + 2, size2.order)

    def test_createview01(self):
        user = self.login()

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
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        self.assertRedirects(response, orga.get_absolute_url())

    @skipIfCustomAddress
    def test_createview02(self):
        "With addresses."
        user = self.login()

        name = 'Bebop'

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
        user = self.login()
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
        self.login()
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
        user = self.login()

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
        user = self.login()

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
        "Addresses are problematic"
        user = self.login()

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

        cloned = bebop.clone()

        self.assertEqual(bebop.name, cloned.name)

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

    def _build_managed_orga(self, user=None, name='Bebop'):
        return Organisation.objects.create(user=user or self.user, name=name, is_managed=True)

    def test_manager_filter_managed_by_creme(self):
        user = self.login()

        mng_orga1 = self._build_managed_orga()
        mng_orga2 = self._build_managed_orga(name='NERV')
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
        user = self.login()

        mng_orga = self._build_managed_orga()
        customer = Contact.objects.create(user=user, first_name='Jet', last_name='Black')

        url = reverse(url_name, args=(customer.id,))
        data = {'id': mng_orga.id}
        self.assertPOST200(url, data=data, follow=True)
        self.get_object_or_fail(
            Relation,
            subject_entity=customer, object_entity=mng_orga, type=relation_type_id,
        )

        # POST twice
        self.assertPOST200(url, data=data, follow=True)
        self.assertRelationCount(
            1, subject_entity=customer, object_entity=mng_orga, type_id=relation_type_id,
        )

    def test_get_employees(self):
        user = self.login()

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
        user = self.login()

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

    # def test_become_customer01(self):
    #     self._become_test('persons__become_customer', constants.REL_SUB_CUSTOMER_SUPPLIER)
    #
    # @skipIfCustomContact
    # def test_become_customer02(self):
    #     "Credentials errors"
    #     user = self.login(is_superuser=False)
    #
    #     create_creds = partial(SetCredentials.objects.create, role=self.role)
    #     create_creds(
    #         value=(
    #             EntityCredentials.VIEW
    #             | EntityCredentials.CHANGE
    #             | EntityCredentials.DELETE
    #             | EntityCredentials.UNLINK
    #         ),  # Not 'LINK'
    #         set_type=SetCredentials.ESET_ALL,
    #     )
    #     create_creds(
    #         value=(
    #             EntityCredentials.VIEW
    #             | EntityCredentials.CHANGE
    #             | EntityCredentials.DELETE
    #             | EntityCredentials.LINK
    #             | EntityCredentials.UNLINK
    #         ),
    #         set_type=SetCredentials.ESET_OWN,
    #     )
    #
    #     mng_orga01 = self._build_managed_orga()
    #
    #     # Can not link it
    #     customer01 = Contact.objects.create(
    #         user=self.other_user, first_name='Jet', last_name='Black',
    #     )
    #
    #     self.assertPOST403(
    #         reverse('persons__become_customer', args=(customer01.id,)),
    #         data={'id': mng_orga01.id}, follow=True
    #     )
    #     self.assertEqual(0, Relation.objects.filter(subject_entity=customer01.id).count())
    #
    #     mng_orga02 = self._build_managed_orga(user=self.other_user)  # Can not link it
    #     customer02 = Contact.objects.create(user=user, first_name='Vicious', last_name='??')
    #     self.assertPOST403(
    #         reverse('persons__become_customer', args=(customer02.id,)),
    #         data={'id': mng_orga02.id}, follow=True
    #     )
    #     self.assertEqual(0, Relation.objects.filter(subject_entity=customer02.id).count())

    # def test_become_prospect(self):
    #     self._become_test('persons__become_prospect', constants.REL_SUB_PROSPECT)
    #
    # def test_become_suspect(self):
    #     self._become_test('persons__become_suspect', constants.REL_SUB_SUSPECT)
    #
    # def test_become_inactive_customer(self):
    #     self._become_test('persons__become_inactive_customer', constants.REL_SUB_INACTIVE)
    #
    # def test_become_supplier(self):
    #     self._become_test('persons__become_supplier', constants.REL_OBJ_CUSTOMER_SUPPLIER)

    def test_leads_customers01(self):
        user = self.login()

        self._build_managed_orga()
        Organisation.objects.create(user=user, name='Nerv')

        response = self.assertGET200(reverse('persons__leads_customers'))

        with self.assertNoException():
            orgas_page = response.context['page_obj']

        self.assertEqual(0, orgas_page.paginator.count)

    def test_leads_customers02(self):
        user = self.login()

        mng_orga = self._build_managed_orga()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        fsf  = create_orga(name='FSF')
        evil = create_orga(name='EvilCorp')

        # post = partial(self.client.post, data={'id': mng_orga.id})
        # post(reverse('persons__become_customer', args=(nerv.id,)))
        # post(reverse('persons__become_prospect', args=(acme.id,)))
        # post(reverse('persons__become_suspect',  args=(fsf.id,)))
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
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        # self.client.post(
        #     reverse('persons__become_customer', args=(nerv.id,)),
        #     data={'id': acme.id},
        # )
        Relation.objects.create(
            user=user,
            subject_entity=acme,
            object_entity=nerv,
            type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
        )

        response = self.client.get(reverse('persons__leads_customers'))
        self.assertEqual(0, response.context['page_obj'].paginator.count)

    def test_create_customer01(self):
        user = self.login()

        managed1 = self.get_object_or_fail(Organisation, is_managed=True)
        managed2 = Organisation.objects.create(user=user, name='Nerv', is_managed=True)

        url = reverse('persons__create_customer')
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rtypes_f = fields['customers_rtypes']

        self.assertEqual(_('Relationships'), rtypes_f.label)
        self.assertIn('customers_managed_orga', fields)

        def post(managed, name):
            response = self.client.post(
                url, follow=True,
                data={
                    'user':  user.id,
                    'name':  name,

                    'customers_managed_orga': managed.id,
                    'customers_rtypes': [constants.REL_SUB_SUSPECT],
                },
            )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Organisation, name=name)

        # ----
        orga1 = post(managed2, name='Bebop')
        self.assertRelationCount(0, orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed2)
        self.assertRelationCount(0, orga1, constants.REL_SUB_PROSPECT,          managed2)
        self.assertRelationCount(1, orga1, constants.REL_SUB_SUSPECT,           managed2)

        self.assertRelationCount(0, orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed1)
        self.assertRelationCount(0, orga1, constants.REL_SUB_PROSPECT,          managed1)
        self.assertRelationCount(0, orga1, constants.REL_SUB_SUSPECT,           managed1)

        # ----
        orga2 = post(managed1, name='Red dragons')
        self.assertRelationCount(1, orga2, constants.REL_SUB_SUSPECT, managed1)
        self.assertRelationCount(0, orga2, constants.REL_SUB_SUSPECT, managed2)

    def test_create_customer02(self):
        "Not super-user."
        user = self.login(is_superuser=False, creatable_models=[Organisation])

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not 'LINK'
            set_type=SetCredentials.ESET_ALL,
        )
        create_creds(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

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
        response = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response, 'form', 'customers_managed_orga',
            _('You are not allowed to link this entity: {}').format(managed1),
        )

        # ---
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'user': self.other_user.id,  # <==
                'customers_managed_orga': managed2.id,
            },
        )
        self.assertFormError(
            response, 'form', 'user',
            _('You are not allowed to link with the «{models}» of this user.').format(
                models=_('Organisations'),
            ),
        )

        # ---
        response = self.assertPOST200(
            url, follow=True,
            data={**data, 'customers_managed_orga': managed2.id},
        )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertRelationCount(1, orga, constants.REL_SUB_SUSPECT, managed2)

    def test_create_customer03(self):
        "Can never link."
        self.login(is_superuser=False, creatable_models=[Organisation])
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not 'LINK'
            set_type=SetCredentials.ESET_ALL,
        )
        self.assertPOST403(reverse('persons__create_customer'))

    def test_delete01(self):
        user = self.login()
        orga01 = Organisation.objects.create(user=user, name='Nerv')
        url = orga01.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        self.assertIs(orga01.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(orga01)

    def test_delete02(self):
        "Cannot delete the last managed organisation."
        self.login()

        managed_orgas = Organisation.objects.filter(is_managed=True)
        self.assertEqual(1, len(managed_orgas))

        managed_orga = managed_orgas[0]
        self.assertPOST409(managed_orga.get_delete_absolute_url())  # follow=True
        self.assertStillExists(managed_orga)

    def test_delete03(self):
        "A managed organisation ac be deleted if it's not the last one."
        user = self.login()

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
        user = self.login()
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
        user = self.login()
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
        user = self.login()
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
        user = self.login()
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
        user = self.login()
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
        user = self.login()
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
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Swordfish')
        orga3 = create_orga(name='RedTail')

        url = reverse('persons__orga_set_managed')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Add some managed organisations'), context.get('title'))
        self.assertEqual(_('Save the modifications'),         context.get('submit_label'))

        # ---
        response = self.client.post(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1, orga2)},
        )
        self.assertNoFormError(response)

        self.assertTrue(self.refresh(orga1).is_managed)
        self.assertTrue(self.refresh(orga2).is_managed)
        self.assertFalse(self.refresh(orga3).is_managed)

        # Managed Organisations are excluded
        response = self.assertPOST200(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1)},
        )
        # self.assertFormError(response, 'form', 'organisations', _('This entity does not exist.'))
        self.assertFormError(
            response, 'form', 'organisations',
            _('«%(entity)s» violates the constraints.') % {'entity': orga1},
        )

    def test_set_orga_as_managed02(self):
        "Not super-user."
        self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'persons'],
            admin_4_apps=['creme_core'],
        )
        self.assertGET200(reverse('persons__orga_set_managed'))

    def test_set_orga_as_managed03(self):
        "Admin permission needed."
        self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'persons'],
            # admin_4_apps=['creme_core'],
        )
        self.assertGET403(reverse('persons__orga_set_managed'))

    def test_set_orga_as_not_managed(self):
        self.login()

        mngd_orgas = Organisation.objects.filter(is_managed=True)
        self.assertEqual(1, len(mngd_orgas))

        orga1 = mngd_orgas[0]
        orga2 = self._build_managed_orga()

        url = reverse('persons__orga_unset_managed')
        data = {'id': orga2.id}
        self.assertGET405(url)
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertFalse(self.refresh(orga2).is_managed)

        self.assertPOST409(url, data={'id': orga1.id})  # At least 1 managed organisation
        self.assertTrue(self.refresh(orga1).is_managed)
