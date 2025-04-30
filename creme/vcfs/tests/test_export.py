from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from creme.creme_core.models import (
    ButtonMenuItem,
    FieldsConfig,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.constants import REL_OBJ_EMPLOYED_BY
from creme.persons.models import Civility
from creme.vcfs.buttons import GenerateVcfButton

from .base import (
    Address,
    Contact,
    Organisation,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomContact
class VcfExportTestCase(CremeTestCase):
    def _generate_vcf(self, contact, status_code=200):
        response = self.client.get(reverse('vcfs__export', args=(contact.id,)))
        self.assertEqual(status_code, response.status_code)

        return response

    def create_contact(self, user, **kwargs):
        return Contact.objects.create(**{
            'user': user,
            'last_name': 'Abitbol',
            'first_name': 'George',
            'phone': '0404040404',
            'mobile': '0606060606',
            'fax': '0505050505',
            'email': 'a@aa.fr',
            'url_site': 'www.aaa.fr',
            **kwargs
        })

    def create_address(self, contact, prefix):
        return Address.objects.create(
            address=f'{prefix}_address',
            city=f'{prefix}_city',
            po_box=f'{prefix}_po_box',
            country=f'{prefix}_country',
            zipcode=f'{prefix}_zipcode',
            department=f'{prefix}_department',
            content_type_id=ContentType.objects.get_for_model(Contact).id,
            object_id=contact.id,
        )

    def test_button(self):
        user = self.login_as_root_and_get()
        ButtonMenuItem.objects.create(
            content_type=Contact, button=GenerateVcfButton, order=100,
        )

        contact = self.create_contact(user=user)
        response = self.assertGET200(contact.get_absolute_url())
        self.assertTemplateUsed(response, GenerateVcfButton.template_name)

    def test_get_empty_vcf(self):
        user = self.login_as_root_and_get()
        response = self._generate_vcf(Contact.objects.create(user=user, last_name='Abitbol'))
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\nEND:VCARD\r\n',
            response.content,
        )

    def test_get_vcf_basic_role(self):
        user = self.login_as_standard(
            allowed_apps=('creme_core', 'persons', 'vcfs'),
            creatable_models=[Contact],
        )
        self.add_credentials(user.role, all='!VIEW')

        contact = Contact.objects.create(user=self.get_root_user(), last_name='Abitbol')
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_view(contact))
        self._generate_vcf(contact, status_code=403)

    def test_get_vcf_civility(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user,
            civility=Civility.objects.create(title='Monsieur'),
            last_name='Abitbol',
        )

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;Monsieur;\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomOrganisation
    def test_get_vcf_org(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(user=user, last_name='Abitbol')
        orga = Organisation.objects.create(user=user, name='ORGNAME')

        rtype = RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY)
        Relation.objects.create(
            type=rtype, subject_entity=orga, object_entity=contact, user=user,
        )

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\n'
            b'ORG:ORGNAME\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_get_vcf_billing_addr(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user, civility=Civility.objects.create(title='Mr'))
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;Org_city;Org_department;'
            b'Org_zipcode;Org_countr\r\n y\r\nTEL;TYPE=CELL:0606060606\r\n'
            b'EMAIL;TYPE=INTERNET:a@aa.fr\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
            b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_get_vcf_shipping_addr(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user, civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;'
            b'Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
            b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;'
            b'\r\nTEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_get_vcf_both_addr(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user, civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
            b'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;'
            b'sh\r\n ipping_zipcode;shipping_country\r\n'
            b'ADR:billing_po_box;;billing_address;billing_city;billing_department;'
            b'billin\r\n g_zipcode;billing_country\r\n'
            b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
            b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_get_vcf_addr_eq(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user, civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()
        self.create_address(contact, 'Org')  # Other_address

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
            b'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
            b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
            b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_person(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user, civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()
        self.create_address(contact, 'Org')  # Other_address

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
            b'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;'
            b'sh\r\n ipping_zipcode;shipping_country\r\n'
            b'ADR:billing_po_box;;billing_address;billing_city;billing_department;'
            b'billin\r\n g_zipcode;billing_country\r\n'
            b'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
            b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
            b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )

    @skipIfCustomAddress
    def test_fields_config(self):
        user = self.login_as_root_and_get()
        contact = self.create_contact(user=user)
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()

        create_fc = FieldsConfig.objects.create
        create_fc(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        create_fc(
            content_type=Address,
            descriptions=[('zipcode', {FieldsConfig.HIDDEN: True})],
        )

        response = self._generate_vcf(contact)
        self.assertEqual(
            b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
            b'ADR:billing_po_box;;billing_address;billing_city;billing_department;;'
            b'billi\r\n ng_country\r\n'
            b'TEL;TYPE=CELL:0606060606\r\n'
            b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;;\r\n'
            b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
            response.content,
        )
