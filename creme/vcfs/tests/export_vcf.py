# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, RelationType, SetCredentials, ButtonMenuItem

    from creme.persons.models import Contact, Organisation, Address, Civility
    from creme.persons.constants import REL_OBJ_EMPLOYED_BY

    from creme.vcfs.buttons import generate_vcf_button
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class VcfExportTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def _generate_vcf(self, contact, status_code=200):
        response = self.client.get('/vcfs/%s/generate_vcf' % contact.id)
        self.assertEqual(status_code, response.status_code)

        return response

    def create_contact(self):
        return Contact.objects.create(user=self.user,
                                      last_name='Abitbol',
                                      first_name='George',
                                      phone='0404040404',
                                      mobile='0606060606',
                                      fax='0505050505',
                                      email='a@aa.fr',
                                      url_site='www.aaa.fr',
                                     )

    def create_address(self, contact, prefix):
        return Address.objects.create(address='%s_address' % prefix,
                                      city='%s_city' % prefix,
                                      po_box='%s_po_box' % prefix,
                                      country='%s_country' % prefix,
                                      zipcode='%s_zipcode' % prefix,
                                      department='%s_department' % prefix,
                                      content_type_id=ContentType.objects.get_for_model(Contact).id,
                                      object_id=contact.id,
                                     )

    def test_button(self):
        self.login()
        ButtonMenuItem.create_if_needed(pk='vcfs-test_button', model=Contact,
                                        button=generate_vcf_button, order=100,
                                       )

        contact = self.create_contact()
        response = self.assertGET200(contact.get_absolute_url())
        self.assertTemplateUsed(response, generate_vcf_button.template_name)

    def test_get_empty_vcf(self):
        self.login()
        response = self._generate_vcf(Contact.objects.create(user=self.user, last_name='Abitbol'))
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_basic_role(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'persons', 'vcfs'), creatable_models=[Contact])
        user = self.user

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | \
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK, # no EntityCredentials.VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        contact = Contact.objects.create(user=self.other_user, last_name='Abitbol')
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_view(contact))
        self._generate_vcf(contact, status_code=403)

    def test_get_vcf_civility(self):
        self.login()
        contact = Contact.objects.create(user=self.user,
                                         civility=Civility.objects.create(title='Monsieur'),
                                         last_name='Abitbol'
                                        )

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;Monsieur;\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_org(self):
        self.login()
        user = self.user
        contact = Contact.objects.create(user=user, last_name='Abitbol')
        orga = Organisation.objects.create(user=user, name='ORGNAME')

        rtype = RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY)
        Relation.objects.create(type=rtype, subject_entity=orga, object_entity=contact, user=user)

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\nORG:ORGNAME\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_billing_addr(self):
        self.login()
        contact = self.create_contact()
        contact.civility = Civility.objects.create(title='Mr')
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;Org_city;Org_department;'
                         'Org_zipcode;Org_countr\r\n y\r\nTEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_shipping_addr(self):
        self.login()
        contact = self.create_contact()
        contact.civility = Civility.objects.create(title='Mr')
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;'
                         'Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;'
                         '\r\nTEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_both_addr(self):
        self.login()
        contact = self.create_contact()
        contact.civility = Civility.objects.create(title='Mr')
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;sh\r\n ipping_zipcode;shipping_country\r\n'
                         'ADR:billing_po_box;;billing_address;billing_city;billing_department;billin\r\n g_zipcode;billing_country\r\n'
                         'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_addr_eq(self):
        self.login()
        contact = self.create_contact()
        contact.civility = Civility.objects.create(title='Mr')
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()
        self.create_address(contact, 'Org') #other_address

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_person(self):
        self.login()
        contact = self.create_contact()
        contact.civility = Civility.objects.create(title='Mr')
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()
        self.create_address(contact, 'Org') #other_address

        response = self._generate_vcf(contact)
        self.assertEqual('BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;sh\r\n ipping_zipcode;shipping_country\r\n'
                         'ADR:billing_po_box;;billing_address;billing_city;billing_department;billin\r\n g_zipcode;billing_country\r\n'
                         'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )
