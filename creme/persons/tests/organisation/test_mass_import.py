from functools import partial

from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.models import FieldsConfig
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin

from ..base import (
    Address,
    Organisation,
    _BaseTestCase,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomOrganisation
class OrganisationMassImportTestCase(MassImportBaseTestCaseMixin,
                                     _BaseTestCase):
    IMPORT_DATA = {
        'step':     1,
        # 'document': doc.id, 'user': self.user.id,
        'name_colselect': 1,

        'sector_colselect':         0,
        'creation_date_colselect':  0,
        'staff_size_colselect':     0,
        'email_colselect':          0,
        'fax_colselect':            0,
        'phone_colselect':          0,
        'description_colselect':    0,
        'code_colselect':           0,
        'siren_colselect':          0,
        'naf_colselect':            0,
        'annual_revenue_colselect': 0,
        'url_site_colselect':       0,
        'legal_form_colselect':     0,
        'rcs_colselect':            0,
        'tvaintra_colselect':       0,
        'subject_to_vat_colselect': 0,
        'capital_colselect':        0,
        'siret_colselect':          0,
        'eori_colselect':           0,

        # 'property_types', 'fixed_relations', 'dyn_relations',

        'billaddr_address_colselect':    0,   'shipaddr_address_colselect':    0,
        'billaddr_po_box_colselect':     0,   'shipaddr_po_box_colselect':     0,
        'billaddr_city_colselect':       0,   'shipaddr_city_colselect':       0,
        'billaddr_state_colselect':      0,   'shipaddr_state_colselect':      0,
        'billaddr_zipcode_colselect':    0,   'shipaddr_zipcode_colselect':    0,
        'billaddr_country_colselect':    0,   'shipaddr_country_colselect':    0,
        'billaddr_department_colselect': 0,   'shipaddr_department_colselect': 0,
    }

    @skipIfCustomAddress
    def test_mass_import01(self):
        user = self.login_as_root_and_get()

        name1 = 'Nerv'
        city1 = 'Tokyo'
        name2 = 'Gunsmith Cats'
        city2 = 'Chicago'
        lines = [(name1, city1, ''), (name2, '', city2)]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Organisation),
            follow=True,
            data={
                **self.IMPORT_DATA,
                'document': doc.id,
                'user': user.id,
                'billaddr_city_colselect': 2,
                'shipaddr_city_colselect': 3,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertListEqual(
            [_('Import «{model}» from {doc}').format(model=_('Organisation'), doc=doc)],
            job.description,
        )

        results = self._get_job_results(job)
        lines_count = len(lines)
        self.assertEqual(lines_count, len(results))
        self._assertNoResultError(results)

        billing_address = self.get_object_or_fail(Organisation, name=name1).billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(_('Billing address'), billing_address.name)
        self.assertEqual(city1,                billing_address.city)

        shipping_address = self.get_object_or_fail(Organisation, name=name2).shipping_address
        self.assertIsNotNone(shipping_address)
        self.assertEqual(_('Shipping address'), shipping_address.name)
        self.assertEqual(city2,                 shipping_address.city)

        self.assertListEqual(
            [
                ngettext(
                    '{count} «{model}» has been created.',
                    '{count} «{model}» have been created.',
                    lines_count
                ).format(count=lines_count, model=_('Organisations')),
                ngettext(
                    '{count} line in the file.',
                    '{count} lines in the file.',
                    lines_count
                ).format(count=lines_count),
            ],
            job.stats,
        )

    @skipIfCustomAddress
    def test_mass_import02(self):
        "Update (with address)."
        user = self.login_as_root_and_get()

        name = 'Bebop'
        city1 = 'Red city'
        city2 = 'Crater city'

        bebop = Organisation.objects.create(user=user, name=name)

        country = 'Mars'
        create_address = partial(
            Address.objects.create,
            address='XXX', country=country, owner=bebop,
        )
        bebop.billing_address  = addr1 = create_address(name='Hideout #1', city=city1)
        bebop.shipping_address = addr2 = create_address(name='Hideout #2', city=city2)
        bebop.save()

        addr_count = Address.objects.count()

        address_val1 = '213 Gauss Street'
        address_val2 = '56 Einstein Avenue'
        email = 'contact@bebop.mrs'
        doc = self._build_csv_doc([(name, address_val1, address_val2, email)], user=user)
        response = self.client.post(
            self._build_import_url(Organisation),
            follow=True,
            data={
                **self.IMPORT_DATA,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['name'],
                'email_colselect': 4,
                'billaddr_address_colselect': 2,
                'shipaddr_address_colselect': 3,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)

        bebop = self.refresh(bebop)
        self.assertEqual(email, bebop.email)

        self.assertEqual(addr_count, Address.objects.count())

        addr1 = self.refresh(addr1)
        self.assertEqual(city1, addr1.city)
        self.assertEqual(address_val1, addr1.address)
        self.assertEqual(country,      addr1.country)  # Value not erased

        addr2 = self.refresh(addr2)
        self.assertEqual(city2, addr2.city)

    @skipIfCustomAddress
    def test_mass_import03(self):
        "FieldsConfig on Address sub-field."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        name = 'Nerv'
        city = 'Tokyo'
        po_box = 'ABC123'
        doc = self._build_csv_doc([(name, city, po_box)], user=user)
        response = self.client.post(
            self._build_import_url(Organisation), follow=True,
            data={
                **self.IMPORT_DATA,
                'document': doc.id,
                'user': user.id,

                'billaddr_city_colselect':   2,
                'billaddr_po_box_colselect': 3,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        billing_address = self.get_object_or_fail(Organisation, name=name).billing_address

        self.assertIsNotNone(billing_address)
        self.assertEqual(city, billing_address.city)
        self.assertFalse(billing_address.po_box)

    @skipIfCustomAddress
    def test_mass_import04(self):
        "FieldsConfig on 'billing_address' FK field."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        name = 'Nerv'
        doc = self._build_csv_doc([(name, 'Tokyo', 'ABC123')], user=user)
        response = self.client.post(
            self._build_import_url(Organisation), follow=True,
            data={
                **self.IMPORT_DATA,
                'document': doc.id,
                'user': user.id,

                'billaddr_city_colselect': 2,  # Should not be used
                'billaddr_po_box_colselect': 3,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertIsNone(orga.billing_address)

        self._assertNoResultError(self._get_job_results(job))
