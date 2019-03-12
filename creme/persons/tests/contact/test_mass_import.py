# -*- coding: utf-8 -*-

try:
    from functools import partial

    from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin

    from ..base import (_BaseTestCase, skipIfCustomAddress, skipIfCustomContact,
            Contact, Address)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomContact
class ContactMassImportTestCase(_BaseTestCase, MassImportBaseTestCaseMixin):
    IMPORT_DATA = {
        'step': 1,
        # 'document': doc.id, 'user': self.user.id,

        'first_name_colselect': 1,
        'last_name_colselect':  2,

        'civility_colselect':      0,
        'description_colselect':   0,
        'skype_colselect':         0,
        'phone_colselect':         0,
        'mobile_colselect':        0,
        'fax_colselect':           0,
        'position_colselect':      0,
        'full_position_colselect': 0,
        'sector_colselect':        0,
        'email_colselect':         0,
        'url_site_colselect':      0,
        'birthday_colselect':      0,
        'image_colselect':         0,

        # 'property_types', 'fixed_relations', 'dyn_relations',

        # TODO: factorise with OrganisationTestCase
        'billaddr_address_colselect':    0,  'shipaddr_address_colselect':    0,
        'billaddr_po_box_colselect':     0,  'shipaddr_po_box_colselect':     0,
        'billaddr_city_colselect':       0,  'shipaddr_city_colselect':       0,
        'billaddr_state_colselect':      0,  'shipaddr_state_colselect':      0,
        'billaddr_zipcode_colselect':    0,  'shipaddr_zipcode_colselect':    0,
        'billaddr_country_colselect':    0,  'shipaddr_country_colselect':    0,
        'billaddr_department_colselect': 0,  'shipaddr_department_colselect': 0,
    }

    @skipIfCustomAddress
    def test_mass_import01(self):
        user = self.login()

        count = Contact.objects.count()
        lines = [('Rei',   'Ayanami'),
                 ('Asuka', 'Langley'),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(
            self._build_import_url(Contact),
            follow=True,
            data=dict(self.IMPORT_DATA,
                      document=doc.id,
                      user=user.id,
                      first_name_colselect=1,
                      last_name_colselect=2,
                     ),
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        lines_count = len(lines)
        self._assertNoResultError(self._get_job_results(job))

        self.assertEqual(count + lines_count, Contact.objects.count())

        for first_name, last_name in lines:
            contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
            self.assertEqual(user, contact.user)
            self.assertIsNone(contact.billing_address)

    @skipIfCustomAddress
    def test_mass_import02(self):
        "Address."
        user = self.login()

        contact_count = Contact.objects.count()

        city = 'Tokyo'
        lines = [
            ('First name', 'Last name', 'City'),
            ('Rei',        'Ayanami',   city),
            ('Asuka',      'Langley',   ''),
        ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(
            self._build_import_url(Contact),
            follow=True,
            data=dict(self.IMPORT_DATA,
                      document=doc.id, has_header=True,
                      user=user.id,
                      first_name_colselect=1,
                      last_name_colselect=2,
                      billaddr_city_colselect=3,
                     ),
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        lines_count = len(lines) - 1  # '-1' for header
        jresults = self._get_job_results(job)
        self.assertEqual(lines_count, len(jresults)) # '-1' for header
        self.assertEqual(contact_count + lines_count, Contact.objects.count())

        rei = self.get_object_or_fail(Contact, last_name=lines[1][1], first_name=lines[1][0])
        address = rei.billing_address
        self.assertIsInstance(address, Address)
        self.assertEqual(city, address.city)

        asuka = self.get_object_or_fail(Contact, last_name=lines[2][1], first_name=lines[2][0])
        self.assertIsNone(asuka.billing_address)

    @skipIfCustomAddress
    def test_mass_import03(self):
        "Update (with address)."
        user = self.login()

        last_name = 'Ayanami'
        first_name = 'Rei'
        rei = Contact.objects.create(user=user, last_name=last_name, first_name=first_name)

        city1 = 'Kyoto'
        city2 = 'Tokyo'
        create_address = partial(Address.objects.create, address='XXX', country='Japan',
                                 owner=rei,
                                )
        rei.billing_address  = addr1 = create_address(name='Hideout #1', city=city1)
        rei.shipping_address = addr2 = create_address(name='Hideout #2', city=city2)
        rei.save()

        addr_count = Address.objects.count()

        address_val1 = '213 Gauss Street'
        address_val2 = '56 Einstein Avenue'
        email = 'contact@bebop.mrs'
        doc = self._build_csv_doc([(first_name, last_name, address_val1, address_val2, email)])
        response = self.client.post(
            self._build_import_url(Contact),
            follow=True,
            data=dict(self.IMPORT_DATA,
                      document=doc.id,
                      user=user.id,
                      key_fields=['first_name', 'last_name'],
                      email_colselect=5,
                      billaddr_address_colselect=3,
                      shipaddr_address_colselect=4,
                     ),
        )
        self.assertNoFormError(response)

        self._execute_job(response)

        rei = self.refresh(rei)
        self.assertEqual(email, rei.email)

        self.assertEqual(addr_count, Address.objects.count())

        addr1 = self.refresh(addr1)
        self.assertEqual(city1, addr1.city)
        self.assertEqual(address_val1, addr1.address)

        addr2 = self.refresh(addr2)
        self.assertEqual(city2, addr2.city)
