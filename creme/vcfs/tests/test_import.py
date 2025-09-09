import base64
import urllib
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from PIL.Image import open as open_img

from creme.creme_core.models import (
    CremePropertyType,
    CustomField,
    CustomFieldValue,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.documents.tests.base import DocumentsTestCaseMixin
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.models import Civility, Position, Sector
from creme.persons.populate import UUID_CIVILITY_MR, UUID_POSITION_CEO

from ..vcf_lib import readOne as read_vcf
from ..vcf_lib.base import ContentLine
from .base import (
    Address,
    Contact,
    Document,
    Organisation,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


class VcfImportTestCase(DocumentsTestCaseMixin, CremeTestCase):
    IMPORT_URL = reverse('vcfs__import')
    image_data = (
        '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODw'
        'wQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoI'
        'ChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKC'
        'goKCgoKCgoKCj/wAARCABIAEgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAA'
        'AAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhBy'
        'JxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpT'
        'VFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqr'
        'KztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QA'
        'HwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQ'
        'J3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRom'
        'JygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiI'
        'mKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk'
        '5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD274v3SR6BaWpKk3FyNyHuqqxzj0'
        'DbPzFcBpfi3VdKnSC01RnO3cLe4bzVKj2PzAfQirfxYnW78ZTRhgrW1vHCD12kgvn/'
        'AMfH5V53ptpcWeoXUrzRuojQSSeUQ0n3jnO4+o/LAxXl16j9o2naxvGOiPWbf4jaod'
        'YtHuooItPACXCRrvJ6kuucEH7oxk9Cea9D0nxLo2rMq2OoQPK3SJjskP8AwBsN+lfM'
        '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'
    )

    def _post_step0(self, user, content):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(content.encode())
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        return self.client.post(
            self.IMPORT_URL,
            follow=True,
            data={
                'user':     user,
                'vcf_step': 0,
                'vcf_file': filedata,
            },
        )

    def _post_step1(self, data, errors=False):
        data['vcf_step'] = 1
        response = self.client.post(self.IMPORT_URL, follow=True, data=data)

        if not errors:
            self.assertNoFormError(response)

        return response

    def test_add_vcf(self):
        user = self.login_as_root_and_get()

        self.assertGET200(self.IMPORT_URL)

        response = self._post_step0(user=user, content='BEGIN:VCARD\nFN:Test\nEND:VCARD')
        self.assertNoFormError(response)

        form = self.get_form_or_fail(response)
        self.assertIn('value="1"', str(form['vcf_step']))

    def test_parsing_vcf00(self):
        "First & last names not separated."
        user = self.login_as_root_and_get()

        first_name = 'Yûna'
        last_name = 'Akashi'
        content = f'BEGIN:VCARD\nFN:{first_name} {last_name}\nEND:VCARD'
        self.assertEqual(f'{first_name} {last_name}', read_vcf(content).fn.value)

        response = self._post_step0(user=user, content=content)

        with self.assertNoException():
            form = response.context['form']
            fields = form.fields
            first_name_f = fields['first_name']
            last_name_f = fields['last_name']

        self.assertIn('value="1"', str(form['vcf_step']))

        self.assertEqual(first_name, first_name_f.initial)
        self.assertEqual(last_name, last_name_f.initial)

    def test_parsing_vcf01(self):  # TODO: use BDAY
        "Contact with details & address."
        user = self.login_as_root_and_get()

        first_name = 'Yûna'
        last_name = 'Akashi'
        civility = 'Sempai'
        position = 'Directeur adjoint'
        phone = '00 00 00 00 00'
        mobile = '11 11 11 11 11'
        fax = '22 22 22 22 22'
        email = 'email@email.com'
        site = 'www.my-website.com'
        box = '666'
        street = 'Main avenue'
        city = 'Mahora'
        region = 'Kanto'
        code = '42'
        country = 'Japan'
        content = f"""BEGIN:VCARD
N:{last_name};{first_name};;{civility};
TITLE:{position}
BDAY;value=date:02-10
ADR;TYPE=HOME:{box};;{street};{city};{region};{code};{country}
TEL;TYPE=HOME:{phone}
TEL;TYPE=CELL:{mobile}
TEL;TYPE=FAX:{fax}
EMAIL;TYPE=HOME:{email}
URL;TYPE=HOME:{site}
END:VCARD"""
        response = self._post_step0(user=user, content=content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = read_vcf(content)
        n_value = vobj.n.value
        self.assertEqual(civility, n_value.prefix)
        self.assertEqual(
            _('Read in VCF File: ') + civility,
            fields['civility'].help_text,
        )

        self.assertEqual(first_name, n_value.given)
        self.assertEqual(first_name, fields['first_name'].initial)

        self.assertEqual(last_name,  n_value.family)
        self.assertEqual(last_name, fields['last_name'].initial)

        tel = vobj.contents['tel']
        self.assertEqual(phone, tel[0].value)
        self.assertEqual(phone, fields['phone'].initial)

        self.assertEqual(mobile, tel[1].value)
        self.assertEqual(mobile, fields['mobile'].initial)

        self.assertEqual(fax, tel[2].value)
        self.assertEqual(fax, fields['fax'].initial)

        self.assertEqual(position, vobj.title.value)
        self.assertEqual(
            fields['position'].help_text,
            _('Read in VCF File: ') + position,
        )

        self.assertEqual(email, vobj.email.value)
        self.assertEqual(email, fields['email'].initial)

        self.assertEqual(site, vobj.url.value)
        self.assertEqual(site, fields['url_site'].initial)

        adr_value = vobj.adr.value
        self.assertEqual(last_name, fields['homeaddr_name'].initial)

        self.assertEqual(street, adr_value.street)
        self.assertEqual(box,    adr_value.box)
        self.assertEqual(fields['homeaddr_address'].initial, f'{box} {street}')

        self.assertEqual(city, adr_value.city)
        self.assertEqual(city, fields['homeaddr_city'].initial)

        self.assertEqual(country, adr_value.country)
        self.assertEqual(country, fields['homeaddr_country'].initial)

        self.assertEqual(code, adr_value.code)
        self.assertEqual(code, fields['homeaddr_code'].initial)

        self.assertEqual(region, adr_value.region)
        self.assertEqual(region, fields['homeaddr_region'].initial)

    def test_parsing_vcf02(self):
        "Organisation."
        user = self.login_as_root_and_get()

        name = 'Negima'
        phone = '00 00 00 00 00'
        email = 'corp@corp.com'
        site = 'www.corp.com'
        box = '8989'
        street = 'Magic street'
        city = 'Tokyo'
        region = 'Tokyo region'
        code = '8888'
        country = 'Zipangu'
        content = f"""BEGIN:VCARD
FN:Evangéline McDowell
ORG:{name}
ADR;TYPE=WORK:{box};;{street};{city};{region};{code};{country}
TEL;TYPE=WORK:{phone}
EMAIL;TYPE=WORK:{email}
URL;TYPE=WORK:{site}
END:VCARD"""
        response = self._post_step0(user=user, content=content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = read_vcf(content)

        self.assertEqual(name, vobj.org.value[0])
        self.assertEqual(name, fields['work_name'].initial)

        self.assertEqual(phone, vobj.tel.value)
        self.assertEqual(phone, fields['work_phone'].initial)

        self.assertEqual(email, vobj.email.value)
        self.assertEqual(email, fields['work_email'].initial)

        self.assertEqual(site, vobj.url.value)
        self.assertEqual(site, fields['work_url_site'].initial)

        self.assertEqual(fields['workaddr_name'].initial, name)

        adr = vobj.adr.value
        self.assertEqual(box,    adr.box)
        self.assertEqual(street, adr.street)
        self.assertEqual(fields['workaddr_address'].initial,  f'{box} {street}')

        self.assertEqual(city, adr.city)
        self.assertEqual(city, fields['workaddr_city'].initial)

        self.assertEqual(region, adr.region)
        self.assertEqual(region, fields['workaddr_region'].initial)

        self.assertEqual(code, adr.code)
        self.assertEqual(code, fields['workaddr_code'].initial)

        self.assertEqual(country, adr.country)
        self.assertEqual(country, fields['workaddr_country'].initial)

    def test_parsing_vcf03(self):
        "Address without type ; VCF tags are lower case."
        user = self.login_as_root_and_get()

        box = '852'
        street = '21 Run street'
        city = 'Mahora'
        region = 'Kansai'
        code = '434354'
        country = 'Japan'
        content = f"""begin:vcard
fn:Misora Kasoga
adr:{box};;{street};{city};{region};{code};{country}
tel:00 00 00 00 00
email:email@email.com
x-mozilla-html:FALSE
url:www.url.com
version:2.1
end:vcard"""
        response = self._post_step0(user=user, content=content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = read_vcf(content)
        # self.assertEqual('<VERSION{}2.1>', str(vobj.version))

        help_prefix = _('Read in VCF File without type: ')
        adr_value = vobj.adr.value

        self.assertEqual(box,     adr_value.box)
        self.assertEqual(street,  adr_value.street)
        self.assertEqual(city,    adr_value.city)
        self.assertEqual(region,  adr_value.region)
        self.assertEqual(code,    adr_value.code)
        self.assertEqual(country, adr_value.country)

        self.assertEqual(
            fields['homeaddr_address'].help_text,
            help_prefix + ', '.join([box, street, city, region, code, country])
        )
        self.assertEqual(fields['phone'].help_text,    help_prefix + vobj.tel.value)
        self.assertEqual(fields['email'].help_text,    help_prefix + vobj.email.value)
        self.assertEqual(fields['url_site'].help_text, help_prefix + vobj.url.value)

    @skipIfCustomOrganisation
    def test_parsing_vcf04(self):
        "Existing Organisation."
        user = self.login_as_root_and_get()

        name = 'Negima'
        orga = Organisation.objects.create(user=user, name=name)
        content = f"""BEGIN:VCARD
N:Konoe Konoka
ORG:{name}
ADR;TYPE=WORK:56;;Second street;Kyoto;Kyoto region;7777;Japan
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:email@email.com
URL;TYPE=WORK:www.web-site.com
END:VCARD"""
        response = self._post_step0(user=user, content=content)

        form = self.get_form_or_fail(response)
        self.assertEqual(form['organisation'].field.initial, orga.id)

    def test_parsing_vcf05(self):
        "Multi line, escape chars."
        user = self.login_as_root_and_get()

        first_name = 'Fûka'
        last_name = 'Naritaki'
        long_name = f'{first_name} {last_name} (& Fumika)'
        content = rf"""BEGIN:VCARD
VERSION:3.0
FN:{long_name}
N:{last_name};{first_name}
NICKNAME:The twins
ACCOUNT;type=HOME:123-145789-10
ADR;type=HOME:;;Main Street 256\;\n1rst floor\, Pink door;Mahora;;598;Japan
ORG:University of Mahora\, Department of
  Robotics
END:VCARD"""
        self._post_step0(user=user, content=content)

        vobj = read_vcf(content)
        version = vobj.version
        self.assertIsInstance(version, ContentLine)
        # self.assertEqual('<VERSION{}3.0>', str(version))

        n_value = vobj.n.value
        self.assertEqual(first_name, n_value.given)
        self.assertEqual(last_name,  n_value.family)

        self.assertEqual(
            'University of Mahora, Department of Robotics',
            vobj.org.value[0],
        )

        self.assertEqual(
            'Main Street 256;\n1rst floor, Pink door',
            vobj.adr.value.street,
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_add_contact_vcf00(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        address_count = Address.objects.count()

        content = """BEGIN:VCARD
VERSION:3.0
FN:Ako IZUMI
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:http://www.url.com/
END:VCARD"""
        form = self._post_step0(user=user, content=content).context['form']

        fields = form.fields
        user_id    = fields['user'].initial
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        self.assertIn('value="1"', str(form['vcf_step']))

        # ---
        response2 = self._post_step1(
            data={
                'user':        user_id,
                'first_name':  first_name,
                'last_name':   last_name,
                'phone':       phone,
                'mobile':      mobile,
                'fax':         fax,
                'email':       email,
                'url_site':    url_site,

                'create_or_attach_orga': False,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        contact = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
            phone=phone, mobile=mobile, fax=fax,
            email=email, url_site=url_site,
        )
        self.assertIsNone(contact.sector)
        self.assertRedirects(response2, contact.get_absolute_url())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf01(self):
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        ptype01 = create_ptype(text='Is a fighter')
        ptype02 = create_ptype(text='Is big corp')

        rtype = RelationType.objects.builder(
            id='test-subject_showcases', predicate='showcases', models=[Contact],
        ).symmetric(
            id='test-object_showcases', predicate='is showcased by', models=[Organisation],
        ).get_or_create()[0]
        ct_incompatible_rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='is loving', models=[Contact],
        ).symmetric(
            id='test-object_loves', predicate='is loved by', models=[Contact],
        ).get_or_create()[0]
        internal_rtype = RelationType.objects.builder(
            id='test-subject_leads', predicate='is leading', models=[Contact],
            is_internal=True,
        ).symmetric(
            id='test-object_leads', predicate='is lead by', models=[Organisation],
        ).get_or_create()[0]
        rtype_with_subject_prop = RelationType.objects.builder(
            id='test-subject_fights', predicate='fights',
            models=[Contact], properties=[ptype01],
        ).symmetric(
            id='test-object_fights', predicate='is fought by', models=[Organisation],
        ).get_or_create()[0]
        rtype_with_object_prop = RelationType.objects.builder(
            id='test-subject_pawn', predicate='is an insignificant pawn of', models=[Contact],
        ).symmetric(
            id='test-object_pawn', predicate='has pawn',
            models=[Organisation], properties=[ptype02],
        ).get_or_create()[0]
        rtype_with_object_forb_prop = RelationType.objects.builder(
            id='test-subject_fan', predicate='is a fan of', models=[Contact],
        ).symmetric(
            id='test-object_fan', predicate='has fan',
            models=[Organisation], properties=[ptype02],
        ).get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_commands', predicate='is commanding', models=[Contact],
            enabled=False,
        ).symmetric(
            id='test-object_commands', predicate='is commanded by', models=[Organisation],
        ).get_or_create()[0]

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content = """BEGIN:VCARD
FN:Yue AYASE
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.url.com
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields

        with self.assertNoException():
            rtype_ids = {*fields['relation'].queryset.values_list('id', flat=True)}

        self.assertIn(REL_SUB_EMPLOYED_BY, rtype_ids)
        self.assertIn(REL_SUB_MANAGES,     rtype_ids)
        self.assertIn(rtype.id,            rtype_ids)
        self.assertNotIn(ct_incompatible_rtype.id,       rtype_ids)
        self.assertNotIn(internal_rtype.id,              rtype_ids)
        self.assertNotIn(disabled_rtype.id,              rtype_ids)
        self.assertNotIn(rtype_with_subject_prop.id,     rtype_ids)
        self.assertNotIn(rtype_with_object_prop.id,      rtype_ids)
        self.assertNotIn(rtype_with_object_forb_prop.id, rtype_ids)

        # ---
        response = self._post_step1(
            errors=True,
            data={
                'user':       user.id,

                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,
                'phone':      fields['phone'].initial,
                'mobile':     fields['mobile'].initial,
                'fax':        fields['fax'].initial,
                'email':      fields['email'].initial,
                'url_site':   fields['url_site'].initial,

                'create_or_attach_orga': True,
            },
        )
        form = self.get_form_or_fail(response)
        validation_text = _('Required, if you want to create organisation')
        self.assertFormError(form, field='work_name', errors=validation_text)
        self.assertFormError(form, field='relation',  errors=validation_text)
        self.assertEqual(contact_count, Contact.objects.count())
        self.assertEqual(orga_count,    Organisation.objects.count())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf02(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:http://www.url.com/
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        sector = Sector.objects.all()[0]
        self._post_step1(
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
                'phone':      phone,
                'mobile':     mobile,
                'fax':        fax,
                'email':      email,
                'url_site':   url_site,
                'sector':     sector.id,

                'create_or_attach_orga': False,

                'work_name':     fields['work_name'].initial,
                'work_phone':    fields['work_phone'].initial,
                'work_email':    fields['work_email'].initial,
                'work_url_site': fields['work_url_site'].initial,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())

        self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
            phone=phone, mobile=mobile, fax=fax,
            email=email, url_site=url_site,
            sector=sector,
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf03(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Tchao LINSHEN
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:www.url.com
URL;TYPE=WORK:http://www.work.com/
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        work_name     = fields['work_name'].initial
        work_phone    = fields['work_phone'].initial
        work_email    = fields['work_email'].initial
        work_url_site = fields['work_url_site'].initial

        response = self._post_step1(
            data={
                'user':       fields['user'].initial,
                'first_name': first_name,
                'last_name':  last_name,
                'phone':      phone,
                'mobile':     mobile,
                'fax':        fax,
                'email':      email,
                'url_site':   url_site,

                'create_or_attach_orga': True,

                'relation':      REL_SUB_EMPLOYED_BY,
                'work_name':     work_name,
                'work_phone':    work_phone,
                'work_email':    work_email,
                'work_url_site': work_url_site,
            },
        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count + 1,    Organisation.objects.count())

        orga = self.get_object_or_fail(
            Organisation,
            name=work_name, phone=work_phone,
            email=work_email, url_site=work_url_site,
        )
        contact = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
            phone=phone, mobile=mobile, fax=fax, email=email,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga)
        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf04(self):
        "Related organisation exists & is not updated."
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga = Organisation.objects.create(
            user=user, name='Corporate',
            phone='33 33 33 33 33', email='work@work.com',
            url_site='https://www.work.com',
        )
        orga_count = Organisation.objects.count()

        content = f"""BEGIN:VCARD
FN:Haruna Saotome
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:44 44 44 44 44
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work2.com
URL;TYPE=HOME:www.url2.com
URL;TYPE=WORK:www.work2.com
ORG:{orga.name}
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        self.assertEqual(orga.id, fields['organisation'].initial)

        self._post_step1(
            data={
                'user':          user.id,
                'first_name':    first_name,
                'last_name':     last_name,

                'phone':         phone,
                'mobile':        mobile,
                'fax':           fax,
                'email':         email,
                'url_site':      url_site,

                'create_or_attach_orga': True,
                'organisation':          orga.id,
                'relation':              REL_SUB_EMPLOYED_BY,

                'work_name':     f'{orga.name}_edited',  # <= should not be used,
                'work_phone':    fields['work_phone'].initial,  # <= idem
                'work_email':    fields['work_email'].initial,
                'work_url_site': fields['work_url_site'].initial,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())

        contact = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
            phone=phone, mobile=mobile, fax=fax, email=email,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga)

        orga_not_edited = self.refresh(orga)
        self.assertEqual(orga.name,     orga_not_edited.name)
        self.assertEqual(orga.email,    orga_not_edited.email)
        self.assertEqual(orga.phone,    orga_not_edited.phone)
        self.assertEqual(orga.url_site, orga_not_edited.url_site)

    @skipIfCustomContact
    @skipIfCustomAddress
    def test_add_contact_vcf05(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        address_count = Address.objects.count()
        content = """BEGIN:VCARD
FN:Chisame Hasegawa
ADR;TYPE=HOME:78;;Geek avenue;New-York;;6969;USA
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.url.com
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        adr_name = fields['homeaddr_name'].initial
        address  = fields['homeaddr_address'].initial
        city     = fields['homeaddr_city'].initial
        country  = fields['homeaddr_country'].initial
        code     = fields['homeaddr_code'].initial
        region   = fields['homeaddr_region'].initial

        self._post_step1(
            data={
                'user': fields['user'].initial,

                'first_name': first_name,
                'last_name':  last_name,

                'phone':    fields['phone'].initial,
                'mobile':   fields['mobile'].initial,
                'fax':      fields['fax'].initial,
                'email':    fields['email'].initial,
                'url_site': fields['url_site'].initial,

                'homeaddr_name':     adr_name,
                'homeaddr_address':  address,
                'homeaddr_city':     city,
                'homeaddr_country':  country,
                'homeaddr_code':     code,
                'homeaddr_region':   region,

                'create_or_attach_orga': False,
            },
        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(address_count + 1, Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        address = self.get_object_or_fail(
            Address,
            name=adr_name, address=address,
            city=city, zipcode=code, country=country, department=region,
        )
        self.assertEqual(contact.billing_address, address)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_add_contact_vcf06(self):
        user = self.login_as_root_and_get()
        contact_count = Contact.objects.count()
        address_count = Address.objects.count()
        orga_count    = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Nodoka Myiazaki
ADR;TYPE=HOME:55;;Moe street;Mahora;Kanto;123;Japan
ADR;TYPE=WORK:26;;Eva house;Eva city;Eva region;666;Eva land
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:www.url.com
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        adr_name = fields['homeaddr_name'].initial
        address  = fields['homeaddr_address'].initial
        city     = fields['homeaddr_city'].initial
        country  = fields['homeaddr_country'].initial
        code     = fields['homeaddr_code'].initial
        region   = fields['homeaddr_region'].initial

        work_name = fields['work_name'].initial

        work_adr_name  = fields['workaddr_name'].initial
        work_address   = fields['workaddr_address'].initial
        work_city      = fields['workaddr_city'].initial
        work_country   = fields['workaddr_country'].initial
        work_code      = fields['workaddr_code'].initial
        work_region    = fields['workaddr_region'].initial

        self._post_step1(
            data={
                'user':       fields['user'].initial,
                'first_name': first_name,
                'last_name':  last_name,

                'phone':    fields['phone'].initial,
                'mobile':   fields['mobile'].initial,
                'fax':      fields['fax'].initial,
                'email':    fields['email'].initial,
                'url_site': fields['url_site'].initial,

                'homeaddr_name':     adr_name,
                'homeaddr_address':  address,
                'homeaddr_city':     city,
                'homeaddr_country':  country,
                'homeaddr_code':     code,
                'homeaddr_region':   region,

                'create_or_attach_orga': True,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             work_name,

                'workaddr_name':     work_adr_name,
                'workaddr_address':  work_address,
                'workaddr_city':     work_city,
                'workaddr_country':  work_country,
                'workaddr_code':     work_code,
                'workaddr_region':   work_region,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count + 1,    Organisation.objects.count())
        self.assertEqual(address_count + 2, Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        orga = self.get_object_or_fail(Organisation, name=work_name)
        c_addr = self.get_object_or_fail(
            Address,
            name=adr_name, address=address,
            city=city, zipcode=code, country=country, department=region,
        )
        o_addr = self.get_object_or_fail(
            Address,
            name=work_adr_name, address=work_address,
            city=work_city, zipcode=work_code, country=work_country, department=work_region,
        )
        self.assertEqual(contact.billing_address, c_addr)
        self.assertEqual(orga.billing_address,    o_addr)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf07(self):
        user = self.login_as_root_and_get()
        contact_count = Contact.objects.count()

        orga = Organisation.objects.create(
            user=user, name='Corporate', phone='00 00 00 00 00',
            email='corp@corp.com', url_site='www.corp.com',
        )

        name = 'New amazing name'
        phone = '11 11 11 11'
        email = 'work@work.com'
        url_site = 'www.work.com'
        content = f"""BEGIN:VCARD
FN:Setsuna Sakurazaki
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
TEL;TYPE=WORK:{phone}
EMAIL;TYPE=WORK:{email}
URL;TYPE=WORK:{url_site}
ORG:{name}
END:VCARD"""

        fields = self._post_step0(user=user, content=content).context['form'].fields
        data = {
            'user':       fields['user'].initial,
            'first_name': fields['first_name'].initial,
            'last_name':  fields['last_name'].initial,

            'create_or_attach_orga': '',
            'organisation':          '',
            'relation':              REL_SUB_EMPLOYED_BY,

            'work_name':     fields['work_name'].initial,
            'work_phone':    fields['work_phone'].initial,
            'work_fax':      '12345',
            'work_email':    fields['work_email'].initial,
            'work_url_site': fields['work_url_site'].initial,

            'workaddr_name':     fields['workaddr_name'].initial,
            'workaddr_address':  fields['workaddr_address'].initial,
            'workaddr_city':     fields['workaddr_city'].initial,
            'workaddr_country':  fields['workaddr_country'].initial,
            'workaddr_code':     fields['workaddr_code'].initial,
            'workaddr_region':   fields['workaddr_region'].initial,

            'update_work_name':     'on',
            'update_work_phone':    'on',
            'update_work_email':    'on',
            'update_work_fax':      'on',
            'update_work_url_site': 'on',
            'update_work_address':  'on',
        }
        response1 = self._post_step1(errors=True, data=data)
        form1 = response1.context['form']
        validation_text = _('Create organisation not checked')
        self.assertFormError(form1, field='update_work_name',     errors=validation_text)
        self.assertFormError(form1, field='update_work_phone',    errors=validation_text)
        self.assertFormError(form1, field='update_work_email',    errors=validation_text)
        self.assertFormError(form1, field='update_work_fax',      errors=validation_text)
        self.assertFormError(form1, field='update_work_url_site', errors=validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

        # --------
        data['create_or_attach_orga'] = 'on'
        data['organisation'] = orga.id
        data['relation'] = REL_SUB_EMPLOYED_BY

        self._post_step1(data=data)
        orga = self.refresh(orga)
        self.assertEqual(name,     orga.name)
        self.assertEqual(phone,    orga.phone)
        self.assertEqual(email,    orga.email)
        self.assertEqual(url_site, orga.url_site)

    @skipIfCustomContact
    def test_add_contact_vcf08(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        content = """BEGIN:VCARD
FN:Makie SASAKI
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        response = self._post_step1(
            errors=True,
            data={
                'user':       fields['user'].initial,
                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,

                'create_or_attach_orga': True,
                'relation':             REL_SUB_EMPLOYED_BY,
                'work_name':            fields['work_name'].initial,

                'work_phone':    fields['work_phone'].initial,
                'work_email':    fields['work_email'].initial,
                'work_url_site': fields['work_url_site'].initial,

                'workaddr_name':     fields['workaddr_name'].initial,
                'workaddr_address':  fields['workaddr_address'].initial,
                'workaddr_city':     fields['workaddr_city'].initial,
                'workaddr_country':  fields['workaddr_country'].initial,
                'workaddr_code':     fields['workaddr_code'].initial,
                'workaddr_region':   fields['workaddr_region'].initial,

                'update_work_name':     True,
                'update_work_phone':    True,
                'update_work_email':    True,
                'update_work_fax':      True,
                'update_work_url_site': True,
                'update_work_address':  True,
            },
        )
        form = self.get_form_or_fail(response)
        validation_text = _('Organisation not selected')
        self.assertFormError(form, field='update_work_name',     errors=validation_text)
        self.assertFormError(form, field='update_work_phone',    errors=validation_text)
        self.assertFormError(form, field='update_work_email',    errors=validation_text)
        self.assertFormError(form, field='update_work_fax',      errors=validation_text)
        self.assertFormError(form, field='update_work_url_site', errors=validation_text)
        self.assertFormError(form, field='update_work_address',  errors=validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_contact_vcf09(self):
        user = self.login_as_root_and_get()

        name = 'Negima'
        Organisation.objects.create(
            user=user, name=name, phone='00 00 00 00 00',
            email='corp@corp.com', url_site='www.corp.com',
        )
        content = f"""BEGIN:VCARD
FN:Akira Ookôchi
ORG:{name}
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        response = self._post_step1(
            errors=True,
            data={
                'user':       fields['user'].initial,
                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,

                'create_or_attach_orga': True,
                'organisation':          fields['organisation'].initial,
                'relation':              REL_SUB_EMPLOYED_BY,

                'update_work_name':     True,
                'update_work_phone':    True,
                'update_work_fax':      True,
                'update_work_email':    True,
                'update_work_url_site': True,
                'update_work_address':  True,
            },
        )
        form = self.get_form_or_fail(response)
        validation_text = _('Required, if you want to update organisation')
        self.assertFormError(form, field='work_phone',    errors=validation_text)
        self.assertFormError(form, field='work_email',    errors=validation_text)
        self.assertFormError(form, field='work_fax',      errors=validation_text)
        self.assertFormError(form, field='work_url_site', errors=validation_text)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_add_contact_vcf10(self):
        "Organisation with existing Address."
        user = self.login_as_root_and_get()

        name = 'Robotic club'
        orga = Organisation.objects.create(
            user=user, name=name, phone='00 00 00 00 00',
            email='corp@corp.com', url_site='www.corp.com',
        )
        orga.billing_address = Address.objects.create(
            name='Org_name',
            address='Org_address',
            city='Org_city',
            country='Org_country',
            zipcode='Org_zipcode',
            department='Org_department',
            owner=orga,
        )
        orga.save()

        address_id = orga.billing_address_id

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        address_count = Address.objects.count()

        first_name = 'Chachamaru'
        last_name = 'KARAKURI'

        email = 'work@work.com'
        phone = '11 11 11 11 11'
        site = 'www.work.com'

        country = 'Japan'
        city = 'Mahora'
        zipcode = '42'
        department = 'Kanto'

        box = '99'
        street = 'Tree place'
        address_value = f'{box}, {street}'
        content = f"""BEGIN:VCARD
FN:{first_name} {last_name}
ADR;TYPE=WORK:{box};;{street};{city};{department};{zipcode};{country}
TEL;TYPE=WORK:{phone}
EMAIL;TYPE=WORK:{email}
URL;TYPE=WORK:{site}
ORG:{name}
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        self._post_step1(
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'create_or_attach_orga': True,
                'organisation':          orga.id,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             name,

                'work_phone':    phone,
                'work_email':    email,
                'work_url_site': fields['work_url_site'].initial,

                'workaddr_name':     name,
                'workaddr_address':  address_value,
                'workaddr_city':     city,
                'workaddr_country':  country,
                'workaddr_code':     zipcode,
                'workaddr_region':   department,

                'update_work_name':     True,
                'update_work_phone':    True,
                'update_work_email':    True,
                'update_work_url_site': True,
                'update_work_address':  True,
            },
        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        orga = self.refresh(orga)
        self.assertEqual(name,  orga.name)
        self.assertEqual(phone, orga.phone)
        self.assertEqual(email, orga.email)
        self.assertEqual(site,  orga.url_site)

        billing_address = orga.billing_address
        self.assertEqual(address_id,    billing_address.id)
        self.assertEqual(name,          billing_address.name)
        self.assertEqual(address_value, billing_address.address)
        self.assertEqual(city,          billing_address.city)
        self.assertEqual(country,       billing_address.country)
        self.assertEqual(zipcode,       billing_address.zipcode)
        self.assertEqual(department,    billing_address.department)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_add_contact_vcf11(self):
        user = self.login_as_root_and_get()

        name = 'Astronomy club'
        Organisation.objects.create(
            user=user, name=name,
            phone='00 00 00 00 00', email='corp@corp.com', url_site='https://www.corp.com',
        )

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        address_count = Address.objects.count()

        content = f"""BEGIN:VCARD
FN:Chizuru NABA
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
ORG:{name}
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        orga_id       = fields['organisation'].initial
        work_adr_name = fields['workaddr_name'].initial
        work_address  = fields['workaddr_address'].initial
        work_city     = fields['workaddr_city'].initial
        work_country  = fields['workaddr_country'].initial
        work_code     = fields['workaddr_code'].initial
        work_region   = fields['workaddr_region'].initial
        self._post_step1(
            data={
                'user':       fields['user'].initial,
                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,

                'create_or_attach_orga': True,
                'organisation':          orga_id,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             fields['work_name'].initial,

                'workaddr_name':    work_adr_name,
                'workaddr_address': work_address,
                'workaddr_city':    work_city,
                'workaddr_country': work_country,
                'workaddr_code':    work_code,
                'workaddr_region':  work_region,

                'update_work_address': True,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count + 1, Address.objects.count())

        address = self.get_object_or_fail(
            Address,
            name=work_adr_name, address=work_address,
            city=work_city, zipcode=work_code,
            country=work_country, department=work_region,
        )
        orga = self.get_object_or_fail(Organisation, id=orga_id)

        vobj = read_vcf(content)
        adr = vobj.adr.value

        self.assertEqual(address.name,       vobj.org.value[0])
        self.assertEqual(address.address,    ' '.join([adr.box, adr.street]))
        self.assertEqual(address.city,       adr.city)
        self.assertEqual(address.country,    adr.country)
        self.assertEqual(address.zipcode,    adr.code)
        self.assertEqual(address.department, adr.region)

        self.assertEqual(orga.billing_address, address)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_add_contact_vcf12(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Document.objects.count()
        address_count = Address.objects.count()

        content = (
            'BEGIN:VCARD\n'
            'FN:Kazumi ASAKURA\n'
            'TEL;TYPE=HOME:00 00 00 00 00\n'
            'TEL;TYPE=CELL:11 11 11 11 11\n'
            'TEL;TYPE=FAX:22 22 22 22 22\n'
            'EMAIL;TYPE=HOME:email@email.com\n'
            'URL;TYPE=HOME:www.url.com\n'
            'PHOTO:'
            '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfG'
            'hsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKC'
            'goKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCABIAEgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQE'
            'AAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEI'
            'I0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4e'
            'XqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6e'
            'rx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ'
            '3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZH'
            'SElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6w'
            'sPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD274v3SR6BaWpKk3FyNy'
            'Huqqxzj0DbPzFcBpfi3VdKnSC01RnO3cLe4bzVKj2PzAfQirfxYnW78ZTRhgrW1vHCD12kgvn/AMfH5V53ptp'
            'cWeoXUrzRuojQSSeUQ0n3jnO4+o/LAxXl16j9o2naxvGOiPWbf4jaodYtHuooItPACXCRrvJ6kuucEH7oxk9C'
            'ea9D0nxLo2rMq2OoQPK3SJjskP8AwBsN+lfMkd1cSzWk7SyB5SJViVsLHFjncO5PHXueOlW4dTjvbpoY4d0Co'
            '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'
            'QwbJcZzwM9BRRRTGf//Z'
            '\nEND:VCARD'
        )
        fields = self._post_step0(user=user, content=content).context['form'].fields
        user       = fields['user'].initial
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        url_site   = fields['url_site'].initial
        self._post_step1(
            data={
                'user': user,

                'first_name': first_name,
                'last_name': last_name,

                'phone':    fields['phone'].initial,
                'mobile':   fields['mobile'].initial,
                'fax':      fields['fax'].initial,
                'email':    fields['email'].initial,
                'url_site': url_site,

                'create_or_attach_orga': False,
            },
        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count,       Document.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertEqual(url_site, contact.url_site)

    @skipIfCustomContact
    def test_add_contact_vcf13(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        first_name = 'Negi'
        last_name = 'Springfield'
        content = (
            'BEGIN:VCARD\nN;ENCODING=8BIT:{last_name};{first_name};;'
            '{civility};\nTITLE:{position}\nEND:VCARD'.format(
                first_name=first_name,
                last_name=last_name,
                civility=_('Mr.'),
                position=_('CEO'),
            )
        )
        response = self._post_step0(user=user, content=content)

        with self.assertNoException():
            fields = response.context['form'].fields
            user_id      = fields['user'].initial
            first_name_f = fields['first_name']
            last_name_f  = fields['last_name']
            civility_id  = fields['civility'].initial
            position_id  = fields['position'].initial

        self.assertEqual(user.id, user_id)
        self.assertEqual(first_name, first_name_f.initial)
        self.assertEqual(last_name, last_name_f.initial)
        self.assertEqual(Civility.objects.get(uuid=UUID_CIVILITY_MR).id, civility_id)
        self.assertEqual(Position.objects.get(uuid=UUID_POSITION_CEO).id, position_id)

        self._post_step1(
            data={
                'user':       user_id,
                'first_name': first_name,
                'last_name':  last_name,
                'civility':   civility_id,
                'position':   position_id,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.get_object_or_fail(
            Contact,
            civility=civility_id, first_name=first_name,
            last_name=last_name, position=position_id,
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_vcf_with_image01(self):
        "Raw image embedded in the file."
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Document.objects.count()
        address_count = Address.objects.count()

        content = (
            f'BEGIN:VCARD\n'
            f'FN:Sakurako SHIINA\n'
            f'PHOTO;TYPE=JPEG:{self.image_data}\n'
            f'END:VCARD'
        )
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        image = fields['image_encoded'].initial
        self._post_step1(
            data={
                'user': user.id,

                'first_name': first_name,
                'last_name':  last_name,

                'create_or_attach_orga': False,

                'image_encoded': image,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count + 1,   Document.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )

        image_entity = contact.image
        self.assertIsNotNone(image_entity)
        self.assertEqual(user, image_entity.user)
        self.assertEqual(
            _('Image of {contact}').format(contact=contact), image_entity.title,
        )
        self.assertEqual(_('Imported by VCFs'), image_entity.description)

        with self.assertNoException():
            with open_img(image_entity.filedata.path) as img:
                self.assertTupleEqual((72, 72), img.size)

    @skipIfCustomContact
    @override_settings(VCF_IMAGE_MAX_SIZE=10_000_000)
    def test_vcf_with_image02(self):
        "Link to an image."
        user = self.login_as_root_and_get()

        img_file = open(
            Path(settings.CREME_ROOT) / 'static' / 'common' / 'images' / '500_200.png',
            mode='rb',
        )
        img_file.info = lambda: {'content-length': 5_000}

        # NB: this url is not valid, we just use it to test called arguments.
        url = 'http://localhost:8001/photograph/yukihiro.png'

        contact_count = Contact.objects.count()
        doc_count = Document.objects.count()

        first_name = 'Ayaka'
        last_name = 'YUKIHIRO'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'PHOTO;VALUE=URL:{url}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            image_encoded_f = response1.context['form'].fields['image_encoded']

        self.assertEqual(url, image_encoded_f.initial)

        with patch('urllib.request.urlopen', return_value=img_file) as urlopen_mock:
            self._post_step1(
                data={
                    'user':          user.id,
                    'first_name':    first_name,
                    'last_name':     last_name,
                    'image_encoded': url,
                },
            )

        urlopen_mock.assert_called_once_with(url)

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(doc_count + 1,     Document.objects.count())

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )

        image_entity = contact.image
        self.assertIsNotNone(image_entity)
        self.assertEqual(
            _('Image of {contact}').format(contact=contact), image_entity.title,
        )

        with self.assertNoException():
            with open_img(image_entity.filedata.path) as img:
                self.assertTupleEqual((200, 200), img.size)

    @skipIfCustomContact
    def test_vcf_with_image03(self):
        "Referenced image cannot be found."
        user = self.login_as_root_and_get()

        image_count = Document.objects.count()

        first_name = 'Kaede'
        last_name = 'NAGASE'
        url = 'http://localhost:8001/photograph/doesnotexist.png'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'PHOTO;VALUE=URL:{url}\n'
                f'END:VCARD'
            ),
        )
        with self.assertNoException():
            encoded_f = response1.context['form'].fields['image_encoded']

        self.assertEqual(url, encoded_f.initial)

        exception = urllib.error.URLError('resource cannot be found')
        with patch('urllib.request.urlopen') as urlopen_mock:
            urlopen_mock.side_effect = exception

            response2 = self._post_step1(
                data={
                    'user':          user.id,
                    'first_name':    first_name,
                    'last_name':     last_name,
                    'image_encoded': url,
                },
                errors=True,
            )

        urlopen_mock.assert_called_once_with(url)

        with self.assertNoException():
            errors = response2.context['form'].errors['image_encoded']

        error = self.get_alone_element(errors)
        self.assertEqual(
            _(
                'An error occurred when trying to retrieve the referenced '
                'image [original error: {}].'
            ).format(exception),
            error,
        )

        # self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count, Document.objects.count())

    @override_settings(VCF_IMAGE_MAX_SIZE=10240)  # (10 kB)
    def test_vcf_with_image04(self):
        "Referenced image is too large."
        user = self.login_as_root_and_get()

        img_file = open(
            Path(settings.CREME_ROOT) / 'static' / 'common' / 'images' / '500_200.png',
            mode='rb',
        )
        img_file.info = lambda: {'content-length': 11_000}

        # NB: this url is not valid, we just use it to test called arguments.
        url = 'http://localhost:8001/photograph/hakase.png'

        image_count = Document.objects.count()

        first_name = 'Satomi'
        last_name = 'HAKASE'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'PHOTO;VALUE=URL:{url}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            image_encoded_f = response1.context['form'].fields['image_encoded']

        self.assertEqual(url, image_encoded_f.initial)

        with patch('urllib.request.urlopen', return_value=img_file) as urlopen_mock:
            response2 = self._post_step1(
                data={
                    'user':          user.id,
                    'first_name':    first_name,
                    'last_name':     last_name,
                    'image_encoded': url,
                },
                errors=True,
            )

        urlopen_mock.assert_called_once_with(url)
        self.assertFormError(
            response2.context['form'],
            field='image_encoded',
            errors=_(
                'The referenced image is too large (limit is {} bytes).'
            ).format(10240),
        )
        self.assertEqual(image_count, Document.objects.count())

    def test_vcf_with_image05(self):
        "Invalid base64 data."
        user = self.login_as_root_and_get()

        first_name = 'Satomi'
        last_name = 'HAKASE'
        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'END:VCARD'
            ),
        )

        response2 = self._post_step1(
            data={
                'user':          user.id,
                'first_name':    first_name,
                'last_name':     last_name,
                'image_encoded': 'abc',
            },
            errors=True,
        )

        # NB: difficult to test the message (it contains the original exception message)
        with self.assertNoException():
            response2.context['form'].errors['image_encoded']  # NOQA

    def test_vcf_with_image06(self):
        "Invalid image data."
        user = self.login_as_root_and_get()

        first_name = 'Satomi'
        last_name = 'HAKASE'
        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'END:VCARD'
            ),
        )

        response2 = self._post_step1(
            data={
                'user':          user.id,
                'first_name':    first_name,
                'last_name':     last_name,
                'image_encoded': base64.b64encode(b'not an image').decode(),
            },
            errors=True,
        )
        self.assertFormError(
            response2.context['form'], field='image_encoded', errors=_('Invalid image data'),
        )

    @skipIfCustomContact
    def test_fields_config_hidden01(self):
        "Hide some regular Contact fields."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )

        contact_count = Contact.objects.count()
        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:http://www.url.com/
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        url_site   = fields['url_site'].initial
        self.assertNotIn('email', fields)

        self._post_step1(
            data={
                'user': fields['user'].initial,

                'first_name': first_name,
                'last_name':  last_name,

                'phone':    phone,
                'mobile':   mobile,
                'fax':      fax,
                'email':    'shouldnot@be.used',  # <==
                'url_site': url_site,

                'create_or_attach_orga': False,

                'work_name':     fields['work_name'].initial,
                'work_phone':    fields['work_phone'].initial,
                'work_email':    fields['work_email'].initial,
                'work_url_site': fields['work_url_site'].initial,
            },
        )
        self.assertEqual(contact_count + 1, Contact.objects.count())

        c = self.get_object_or_fail(
            Contact,
            first_name=first_name, last_name=last_name,
            phone=phone, mobile=mobile, fax=fax, url_site=url_site,
        )
        self.assertEqual('', c.email)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_fields_config_hidden02(self):
        "Hide some regular Organisation & Address fields."
        user = self.login_as_root_and_get()

        create_fc = FieldsConfig.objects.create
        create_fc(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        create_fc(
            content_type=Address,
            descriptions=[
                ('zipcode', {FieldsConfig.HIDDEN: True}),
                ('po_box',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        orga_count = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
ADR;TYPE=HOME:56;;Second street;Kyoto;Kyoto region;7777;Japan
ADR;TYPE=WORK:57;;Third street;Tokyo;Tokyo region;8888;Japan
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:http://www.url.com/
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        work_name     = fields['work_name'].initial
        work_phone    = fields['work_phone'].initial
        work_url_site = fields['work_url_site'].initial
        self.assertNotIn('work_email', fields)
        self.assertNotIn('update_work_email', fields)

        adr_name = fields['homeaddr_name'].initial
        city     = fields['homeaddr_city'].initial
        region   = fields['homeaddr_region'].initial
        self.assertEqual('Kyoto', city)

        work_adr_name = fields['workaddr_name'].initial
        work_city     = fields['workaddr_city'].initial
        work_region   = fields['workaddr_region'].initial
        self.assertEqual('Tokyo', work_city)
        self.assertNotIn('workaddr_code', fields)
        self.assertIn('update_work_address', fields)

        self._post_step1(
            data={
                'user':       fields['user'].initial,
                'first_name': first_name,
                'last_name':  last_name,

                'phone':    fields['phone'].initial,
                'mobile':   fields['mobile'].initial,
                'fax':      fields['fax'].initial,
                'email':    fields['email'].initial,
                'url_site': fields['url_site'].initial,

                'homeaddr_name':    adr_name,
                'homeaddr_address': fields['homeaddr_address'].initial,
                'homeaddr_city':    city,
                'homeaddr_country': fields['homeaddr_country'].initial,
                'homeaddr_region':  region,

                'create_or_attach_orga': True,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             work_name,

                'work_phone':    work_phone,
                'work_email':    'shouldnot@be.used',  # <==
                'work_url_site': work_url_site,

                'workaddr_name':     work_adr_name,
                'workaddr_address':  fields['workaddr_address'].initial,
                'workaddr_city':     work_city,
                'workaddr_country':  fields['workaddr_country'].initial,
                'workaddr_region':   work_region,
            },
        )
        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

        self.assertEqual(orga_count + 1, Organisation.objects.count())
        orga = self.get_object_or_fail(Organisation, name=work_name, phone=work_phone)
        self.assertEqual('', orga.email)

        addr = contact.billing_address
        self.assertIsNotNone(addr)
        self.assertEqual(adr_name, addr.name)
        self.assertEqual(city,     addr.city)
        self.assertEqual(region,   addr.department)

        addr = orga.billing_address
        self.assertIsNotNone(addr)
        self.assertEqual(work_adr_name, addr.name)
        self.assertEqual(work_city,     addr.city)
        self.assertEqual(work_region,   addr.department)

    @skipIfCustomContact
    @skipIfCustomAddress
    def test_fields_config_hidden03(self):
        "Hide Contact.billing_address."
        user = self.login_as_root_and_get()

        create_fc = FieldsConfig.objects.create
        create_fc(
            content_type=Contact,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )
        create_fc(
            content_type=Address,
            descriptions=[('zipcode', {FieldsConfig.HIDDEN: True})],
        )

        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
ADR;TYPE=HOME:56;;Second street;Kyoto;Kyoto region;7777;Japan
TEL;TYPE=HOME:00 00 00 00 00
EMAIL;TYPE=HOME:email@email.com
ORG:Corporate\nEND:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        self.assertNotIn('homeaddr_city', fields)
        self.assertNotIn('homeaddr_code', fields)

        self._post_step1(
            data={
                'user': fields['user'].initial,

                'first_name': first_name,
                'last_name':  last_name,

                'phone': fields['phone'].initial,
                'email': fields['email'].initial,

                'homeaddr_name':    'Main',
                'homeaddr_address': 'Second street',
                'homeaddr_city':    'Kyoto',
            },
        )

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertIsNone(contact.billing_address)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_fields_config_hidden04(self):
        "Hide Organisation.billing_address."
        user = self.login_as_root_and_get()

        create_fc = FieldsConfig.objects.create
        create_fc(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )
        create_fc(
            content_type=Address,
            descriptions=[
                ('zipcode', {FieldsConfig.HIDDEN: True}),
                ('po_box',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
ADR;TYPE=WORK:57;;Third street;Tokyo;Tokyo region;8888;Japan
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=WORK:33 33 33 33 33
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields

        work_name = fields['work_name'].initial

        self.assertNotIn('workaddr_city', fields)
        self.assertNotIn('workaddr_code', fields)
        self.assertNotIn('update_work_address', fields)

        self._post_step1(
            data={
                'user':       user.id,
                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,

                'create_or_attach_orga': True,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             work_name,

                'workaddr_name':    'Billing address',
                'workaddr_city':    'Tokyo',
                'workaddr_country': 'Japan',
            },
        )

        orga = self.get_object_or_fail(Organisation, name=work_name)
        self.assertIsNone(orga.billing_address)

    @skipIfCustomContact
    def test_fields_config_hidden05(self):
        "Hide <Contact.image>."
        user = self.login_as_root_and_get()
        image_count = Document.objects.count()

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )

        first_name = 'Sakurako'
        last_name = 'SHIINA'
        response0 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'PHOTO;TYPE=JPEG:{self.image_data}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response0.context['form'].fields

        self.assertNotIn('image',         fields)
        self.assertNotIn('image_encoded', fields)

        self._post_step1(
            data={
                'user': user.id,

                'first_name': first_name,
                'last_name':  last_name,

                'image_encoded': self.image_data,  # Should not be used
            },
        )
        self.assertEqual(image_count, Document.objects.count())

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertIsNone(contact.image)

    @skipIfCustomContact
    def test_fields_config_required_contact(self):
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.REQUIRED: True})],
        )

        response = self._post_step0(
            user=user,
            content=(
                'BEGIN:VCARD\n'
                'FN:Asuna Kagurazaka\n'
                'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response.context['form'].fields
            phone_f = fields['phone']
            email_f = fields['email']

        self.assertFalse(phone_f.required)
        self.assertTrue(email_f.required)

    @skipIfCustomContact
    def test_fields_config_required_contact_image01(self):
        "No image data => visible image field."
        user = self.login_as_root_and_get()
        image = self._create_image(user=user)

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('image', {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            image_f = fields['image']

        self.assertTrue(image_f.required)
        self.assertNotIn('image_encoded', fields)

        # ---
        response2 = self._post_step1(
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'image': image.id,
            },
        )
        self.assertNoFormError(response2)

        asuna = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertEqual(image.id, asuna.image_id)

    @skipIfCustomContact
    def test_fields_config_required_contact_image02(self):
        "Image data => no explicit image field."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('image', {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'PHOTO;TYPE=JPEG:{self.image_data}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            encoded_image_f = fields['image_encoded']

        self.assertTrue(encoded_image_f.required)

        encoded_image = encoded_image_f.initial
        self.assertTrue(encoded_image)

        self.assertNotIn('image', fields)

        # ---
        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name': last_name,

            # 'image_encoded': ...,
        }
        response2 = self._post_step1(data=data, errors=True)
        self.assertFormError(
            response2.context['form'],
            field='image',
            errors=[
                _('This field is required.'),
                _('The field «{}» has been configured as required.').format(_('Photograph')),
            ],
        )

        # ---
        self._post_step1(data={**data, 'image_encoded': encoded_image})

        asuna = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )

        image = asuna.image
        self.assertIsInstance(image, Document)
        self.assertTrue(image.mime_type.is_image)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_fields_config_required_organisation01(self):
        "Field is already in the form; Organisation is created."
        user = self.login_as_root_and_get()

        req_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        name = 'SAO'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'ORG:{name}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            phone_f = fields['work_phone']
            email_f = fields['work_email']

        self.assertFalse(phone_f.required)
        self.assertFalse(email_f.required)

        # ---
        response2 = self._post_step1(
            data={
                'user':       user.id,
                'first_name': fields['first_name'].initial,
                'last_name':  fields['last_name'].initial,

                'create_or_attach_orga': True,
                'relation':              REL_SUB_EMPLOYED_BY,
                'work_name':             name,
            },
            errors=True,
        )
        self.assertFormError(
            response2.context['form'],
            field=f'work_{req_fname}',
            errors=_('The field «{}» has been configured as required.').format(
                Organisation._meta.get_field(req_fname).verbose_name
            ),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_fields_config_required_organisation02(self):
        "Field is already in the form; Organisation already exists."
        user = self.login_as_root_and_get()

        req_fname = 'phone'
        orga = Organisation.objects.create(user=user, name='SAO')

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'

        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'ORG:{orga.name}\n'
                f'END:VCARD'
            ),
        )

        response = self._post_step1(
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,

                'create_or_attach_orga': True,
                'relation': REL_SUB_EMPLOYED_BY,
                'work_name': orga.name,
                'organisation': orga.id,

                # f'update_work_{req_fname}': 'on',
                # f'work_{req_fname}': '',  # <= empty
            },
            errors=True,
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=f'work_{req_fname}',
            errors=_('The field «{}» has been configured as required.').format(
                Organisation._meta.get_field(req_fname).verbose_name
            ),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_fields_config_required_organisation03(self):
        "Field not in the base form (must be added); Organisation is created."
        user = self.login_as_root_and_get()

        req_fname = 'sector'
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        name = 'SAO'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'ORG:{name}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            sector_f = response1.context['form'].fields[f'work_{req_fname}']

        label = Organisation._meta.get_field(req_fname).verbose_name
        self.assertEqual(label, sector_f.label)
        self.assertFalse(sector_f.required)
        self.assertIsNone(sector_f.initial)

        # ---
        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name':  last_name,

            'create_or_attach_orga': True,
            'relation': REL_SUB_EMPLOYED_BY,
            'work_name': name,
        }
        response2 = self._post_step1(data=data, errors=True)
        self.assertFormError(
            response2.context['form'],
            field=f'work_{req_fname}',
            errors=_('The field «{}» has been configured as required.').format(label),
        )

        # ---
        sector = Sector.objects.all()[0]
        self._post_step1(data={**data, f'work_{req_fname}': sector.id})
        self.get_object_or_fail(Organisation, name=name, sector=sector)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_fields_config_required_organisation04(self):
        "Field not in the base form (must be added); Organisation is updated."
        user = self.login_as_root_and_get()

        req_fname = 'sector'

        sector1, sector2 = Sector.objects.all()[:2]
        orga = Organisation.objects.create(user=user, name='SAO', **{req_fname: sector1})

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        name = 'SAO'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'ORG:{name}\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            sector_f = response1.context['form'].fields[f'work_{req_fname}']

        self.assertFalse(sector_f.required)
        self.assertEqual(sector1, sector_f.initial)

        # ---
        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name':  last_name,

            'create_or_attach_orga': True,
            'relation': REL_SUB_EMPLOYED_BY,
            'work_name': name,
            'organisation': orga.id,
        }
        response2 = self._post_step1(data=data, errors=True)
        self.assertFormError(
            response2.context['form'],
            field=f'work_{req_fname}',
            errors=_('The field «{}» has been configured as required.').format(
                Organisation._meta.get_field(req_fname).verbose_name
            ),
        )

        # ---
        self._post_step1(data={**data, f'work_{req_fname}': sector2.id})
        self.assertEqual(sector2, self.refresh(orga).sector)

    @skipIfCustomContact
    def test_fields_config_required_address01(self):
        "Addresses not filled."
        user = self.login_as_root_and_get()

        req_fname = 'country'
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        response1 = self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                f'END:VCARD'
            ),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            contact_country_f = fields[f'homeaddr_{req_fname}']
            orga_country_f    = fields[f'workaddr_{req_fname}']

        self.assertFalse(contact_country_f.required)
        self.assertFalse(orga_country_f.required)

        self._post_step1(
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'create_or_attach_orga': True,
                'relation': REL_SUB_EMPLOYED_BY,
                'work_name': 'SAO',
            },
        )

        asuna = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertIsNone(asuna.billing_address)

    @skipIfCustomContact
    def test_fields_config_required_address02(self):
        "Addresses are filled (+ field name must be remapped on VCF name)."
        user = self.login_as_root_and_get()

        req_fname = 'department'
        req_fname_vcf = 'region'  # name in VCF data

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                f'END:VCARD'
            ),
        )

        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name': last_name,

            # 'homeaddr_name':     ...,
            'homeaddr_address':  '3 Meuporg street',
            'homeaddr_city':     'Tokyo',
            # 'homeaddr_country':  ...,
            # 'homeaddr_code':     ...,

            'create_or_attach_orga': True,
            'relation': REL_SUB_EMPLOYED_BY,
            'work_name': 'SAO',

            # 'workaddr_name':     ...,
            'workaddr_address': '4 Meuporg street',
            'workaddr_city': 'Tokyo',
            # 'workaddr_country':  ...,
            # 'workaddr_code':     ...,
        }
        response2 = self._post_step1(data=data, errors=True)
        form2 = response2.context['form']
        msg = _('The field «{}» has been configured as required.').format(
            Address._meta.get_field(req_fname).verbose_name,
        )
        self.assertFormError(form2, field=f'homeaddr_{req_fname_vcf}', errors=msg)
        self.assertFormError(form2, field=f'workaddr_{req_fname_vcf}', errors=msg)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_fields_config_required_address03(self):
        "Existing organisation without address."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='SAO')

        req_fname = 'department'
        req_fname_vcf = 'region'  # name in VCF data

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                f'END:VCARD'
            ),
        )

        # ---
        address_value = '4 Meuporg street'
        city = 'Tokyo'
        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name': last_name,

            'create_or_attach_orga': True,
            'relation': REL_SUB_EMPLOYED_BY,
            'work_name': orga.name,
            'organisation': orga.id,

            'update_work_address': 'on',

            # 'workaddr_name':     ...,
            'workaddr_address':   address_value,
            'workaddr_city':      city,
            # 'workaddr_country':  ...,
            # 'workaddr_code':     ...,
        }
        response2 = self._post_step1(data=data, errors=True)

        field_name = f'workaddr_{req_fname_vcf}'
        self.assertFormError(
            response2.context['form'],
            field=field_name,
            errors=_('The field «{}» has been configured as required.').format(
                Address._meta.get_field(req_fname).verbose_name
            ),
        )

        # ---
        department = 'Kanto'
        self._post_step1(data={**data, field_name: department})

        address = self.refresh(orga).billing_address
        self.assertIsNotNone(address)
        self.assertEqual(city,          address.city)
        self.assertEqual(address_value, address.address)
        self.assertEqual(department,    getattr(address, req_fname))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_fields_config_required_address04(self):
        "Organisation with existing address."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='SAO')
        country = 'Japan'
        address = Address.objects.create(
            owner=orga,
            name='billing address',
            country=country,
        )

        orga.billing_address = address
        orga.save()

        req_fname = 'department'
        req_fname_vcf = 'region'  # name in VCF data

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[(req_fname, {FieldsConfig.REQUIRED: True})],
        )

        first_name = 'Asuna'
        last_name = 'Kagurazaka'
        self._post_step0(
            user=user,
            content=(
                f'BEGIN:VCARD\n'
                f'FN:{first_name} {last_name}\n'
                f'EMAIL;TYPE=HOME:asuna@sao.jp\n'
                f'END:VCARD'
            ),
        )

        # ---
        address_value = '4 Meuporg street'
        city = 'Tokyo'
        data = {
            'user': user.id,
            'first_name': first_name,
            'last_name': last_name,

            'create_or_attach_orga': True,
            'relation': REL_SUB_EMPLOYED_BY,
            'work_name': orga.name,
            'organisation': orga.id,

            'update_work_address': 'on',

            # 'workaddr_name':     ...,
            'workaddr_address':   address_value,
            'workaddr_city':      city,
            'workaddr_country':   '',  # should not be used
            # 'workaddr_code':     ...,
        }
        response2 = self._post_step1(data=data, errors=True)

        field_name = f'workaddr_{req_fname_vcf}'
        self.assertFormError(
            response2.context['form'],
            field=field_name,
            errors=_('The field «{}» has been configured as required.').format(
                Address._meta.get_field(req_fname).verbose_name
            ),
        )

        # ---
        department = 'Kanto'
        self._post_step1(data={**data, field_name: department})

        address = self.refresh(orga).billing_address
        self.assertIsNotNone(address)
        self.assertEqual(city,          address.city)
        self.assertEqual(address_value, address.address)
        self.assertEqual(country,       address.country)
        self.assertEqual(department,    getattr(address, req_fname))

    @skipIfCustomContact
    def test_customfields01(self):
        "Required custom-fields on Contact must be used."
        user = self.login_as_root_and_get()

        create_cfield = partial(
            CustomField.objects.create,
            field_type=CustomField.STR, content_type=Contact,
        )
        cfield1 = create_cfield(name='Nickname', is_required=True)
        cfield2 = create_cfield(name='Punch line')
        cfield3 = create_cfield(name='ID', is_required=True, content_type=Document)
        cfield4 = create_cfield(name='Deleted', is_required=True, is_deleted=True)

        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
TEL;TYPE=HOME:00 00 00 00 00
EMAIL;TYPE=HOME:email@email.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        self.assertNotIn(f'custom_field-{cfield2.id}', fields)
        self.assertNotIn(f'custom_field-{cfield3.id}', fields)
        self.assertNotIn(f'custom_field-{cfield4.id}', fields)

        cf_name1 = f'custom_field-{cfield1.id}'
        cf_formfield1 = fields.get(cf_name1)
        self.assertIsNotNone(cf_formfield1)
        self.assertTrue(cf_formfield1.required)

        first_name = fields['first_name'].initial
        last_name = fields['last_name'].initial
        data = {
            'user': user.id,

            'first_name': first_name,
            'last_name': last_name,
        }
        response1 = self._post_step1(data=data, errors=True)
        self.assertFormError(
            response1.context['form'],
            field=cf_name1, errors=_('This field is required.'),
        )

        # ---
        nickname = 'Asu'
        self._post_step1(data={**data, cf_name1: nickname})

        asuna = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        cf_value = self.get_object_or_fail(
            cfield1.value_class, custom_field=cfield1.id, entity=asuna.id,
        )
        self.assertEqual(nickname, cf_value.value)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_customfields02(self):
        "Required custom-fields on Organisations must be used."
        user = self.login_as_root_and_get()

        create_cfield = partial(
            CustomField.objects.create,
            field_type=CustomField.STR, content_type=Organisation,
        )
        cfield1 = create_cfield(name='Main country', is_required=True)
        cfield2 = create_cfield(name='Base line')
        cfield3 = create_cfield(name='EXIF', is_required=True, content_type=Document)

        content = """BEGIN:VCARD
FN:Asuna Kagurazaka
TEL;TYPE=HOME:00 00 00 00 00
EMAIL;TYPE=HOME:email@email.com
ORG:SAO
END:VCARD"""
        fields = self._post_step0(user=user, content=content).context['form'].fields
        self.assertNotIn(f'custom_field-{cfield2.id}', fields)
        self.assertNotIn(f'custom_field-{cfield3.id}', fields)

        cf_name1 = f'custom_field-{cfield1.id}'
        cf_formfield1 = fields.get(cf_name1)
        self.assertIsNotNone(cf_formfield1)
        self.assertTrue(cf_formfield1.required)
        self.assertIsNone(cf_formfield1.initial)

        first_name = fields['first_name'].initial
        last_name = fields['last_name'].initial
        work_name = fields['work_name'].initial
        data = {
            'user': user.id,

            'first_name': first_name,
            'last_name': last_name,

            'create_or_attach_orga': True,
            'relation':              REL_SUB_EMPLOYED_BY,
            'work_name':             work_name,
        }
        response1 = self._post_step1(data=data, errors=True)
        self.assertFormError(
            response1.context['form'],
            field=cf_name1, errors=_('This field is required.'),
        )

        # ---
        country = 'Japan'
        self._post_step1(data={**data, cf_name1: country})

        asuna = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertFalse(cfield1.value_class.objects.filter(entity=asuna.id))

        orga = self.get_object_or_fail(Organisation, name=work_name)
        cf_value = self.get_object_or_fail(
            cfield1.value_class, custom_field=cfield1.id, entity=orga.id,
        )
        self.assertEqual(country, cf_value.value)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_customfields03(self):
        "Required custom-fields on Organisations must be used (organisation already exists."
        user = self.login_as_root_and_get()

        cfield = CustomField.objects.create(
            field_type=CustomField.STR,
            content_type=Organisation,
            name='Main country',
            is_required=True,
        )

        orga = Organisation.objects.create(user=user, name='SAO')

        country = 'Japan'
        CustomFieldValue.save_values_for_entities(cfield, [orga], country)

        content = f"""BEGIN:VCARD
FN:Asuna Kagurazaka
TEL;TYPE=HOME:00 00 00 00 00
EMAIL;TYPE=HOME:email@email.com
ORG:{orga.name}
END:VCARD"""
        form = self._post_step0(user=user, content=content).context['form']

        with self.assertNoException():
            cf_formfield = form.fields[f'custom_field-{cfield.id}']

        self.assertEqual(country, cf_formfield.initial)
