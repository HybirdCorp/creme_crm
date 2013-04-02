# -*- coding: utf-8 -*-

try:
    from os import path as os_path
    from tempfile import NamedTemporaryFile

    from django.utils.translation import ugettext as _
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase

    from creme.media_managers.models import Image

    from creme.persons.models import Contact, Organisation, Address
    from creme.persons.constants import REL_SUB_EMPLOYED_BY

    from creme.vcfs import vcf_lib
    from creme.vcfs.forms import vcf as vcf_forms
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class VcfImportTestCase(CremeTestCase):
    IMPORT_URL = '/vcfs/vcf'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def _post_step0(self, content_str):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(content_str)
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        return self.client.post(self.IMPORT_URL, follow=True,
                                data={'user':     self.user,
                                      'vcf_step': 0,
                                      'vcf_file': filedata,
                                     }
                                )

    def _post_step1(self, data, errors=False):
        data['vcf_step']= 1
        response = self.client.post(self.IMPORT_URL, follow=True, data=data)

        if not errors:
            self.assertNoFormError(response)

        return response

    def test_add_vcf(self):
        self.login()

        self.assertGET200(self.IMPORT_URL)

        response = self._post_step0('BEGIN:VCARD\nFN:Test\nEND:VCARD')
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('value="1"', unicode(form['vcf_step']))

    def test_parsing_vcf00(self):
        self.login()

        content  = 'BEGIN:VCARD\nFN:Prénom Nom\nEND:VCARD'
        response = self._post_step0(content)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('value="1"', unicode(form['vcf_step']))

        firt_name, sep, last_name = vcf_lib.readOne(content).fn.value.partition(' ')
        self.assertEqual(form['first_name'].field.initial, firt_name)
        self.assertEqual(form['last_name'].field.initial,  last_name)

    def test_parsing_vcf01(self):
        self.login()

        content  = """BEGIN:VCARD
N:Nom;Prénom;;Civilité;
TITLE:Directeur adjoint
ADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.my-website.com
END:VCARD"""
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = vcf_lib.readOne(content)
        n_value = vobj.n.value

        self.assertEqual(fields['civility'].help_text, _(u'Read in VCF File : ') + n_value.prefix)
        self.assertEqual(fields['first_name'].initial, n_value.given)
        self.assertEqual(fields['last_name'].initial,  n_value.family)

        tel = vobj.contents['tel']
        self.assertEqual(fields['phone'].initial,  tel[0].value)
        self.assertEqual(fields['mobile'].initial, tel[1].value)
        self.assertEqual(fields['fax'].initial,    tel[2].value)

        self.assertEqual(fields['position'].help_text, ''.join([_(u'Read in VCF File : '), vobj.title.value]))
        self.assertEqual(fields['email'].initial,       vobj.email.value)
        self.assertEqual(fields['url_site'].initial,    vobj.url.value)

        adr_value = vobj.adr.value
        self.assertEqual(fields['adr_last_name'].initial, n_value.family)
        self.assertEqual(fields['address'].initial,       ' '.join([adr_value.box, adr_value.street]))
        self.assertEqual(fields['city'].initial,          adr_value.city)
        self.assertEqual(fields['country'].initial,       adr_value.country)
        self.assertEqual(fields['code'].initial,          adr_value.code)
        self.assertEqual(fields['region'].initial,        adr_value.region)

    def test_parsing_vcf02(self):
        self.login()

        content  = """BEGIN:VCARD
FN:Prénom Nom
ORG:Corporate
ADR;TYPE=WORK:Numéro de rue;;Nom de la rue;Ville;Region;Code Postal;Pays
TEL;TYPE=WORK:00 00 00 00 00
EMAIL;TYPE=WORK:corp@corp.com
URL;TYPE=WORK:www.corp.com
END:VCARD"""
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = vcf_lib.readOne(content)
        self.assertEqual(fields['work_name'].initial,     vobj.org.value[0])
        self.assertEqual(fields['work_phone'].initial,    vobj.tel.value)
        self.assertEqual(fields['work_email'].initial,    vobj.email.value)
        self.assertEqual(fields['work_url_site'].initial, vobj.url.value)
        self.assertEqual(fields['work_adr_name'].initial, vobj.org.value[0])

        adr = vobj.adr.value
        self.assertEqual(fields['work_address'].initial,  '%s %s' % (adr.box, adr.street))
        self.assertEqual(fields['work_city'].initial,     adr.city)
        self.assertEqual(fields['work_region'].initial,   adr.region)
        self.assertEqual(fields['work_code'].initial,     adr.code)
        self.assertEqual(fields['work_country'].initial,  adr.country)

    def test_parsing_vcf03(self):
        self.login()

        content  = """BEGIN:VCARD
FN:Prénom Nom
ADR:Numéro de rue;;Nom de la rue;Ville;Région;Code Postal;Pays
TEL:00 00 00 00 00
EMAIL:email@email.com
URL:www.url.com
END:VCARD"""
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = vcf_lib.readOne(content)
        help_prefix = _(u'Read in VCF File without type : ')
        adr_value = vobj.adr.value
        adr = ', '.join([adr_value.box, adr_value.street, adr_value.city, adr_value.region, adr_value.code, adr_value.country])
        self.assertEqual(fields['address'].help_text,  ''.join([help_prefix, adr]))
        self.assertEqual(fields['phone'].help_text,    ''.join([help_prefix, vobj.tel.value]))
        self.assertEqual(fields['email'].help_text,    ''.join([help_prefix, vobj.email.value]))
        self.assertEqual(fields['url_site'].help_text, ''.join([help_prefix, vobj.url.value]))

    def test_parsing_vcf04(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Corporate')
        content  = """BEGIN:VCARD
N:Prénom Nom
ORG:Corporate
ADR;TYPE=WORK:Numéro de rue;;Nom de la rue;Ville;Region;Code Postal;Pays
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:email@email.com
URL;TYPE=WORK:www.web-site.com
END:VCARD"""
        response = self._post_step0(content)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(form['organisation'].field.initial, orga.id)

    def test_add_contact_vcf00(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:http://www.url.com/
END:VCARD"""
        form = self._post_step0(content).context['form']

        fields = form.fields
        user_id    = fields['user'].initial
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        self.assertIn('value="1"', unicode(form['vcf_step']))

        response = self._post_step1(data={'user':        user_id,
                                           'first_name':  first_name,
                                           'last_name':   last_name,
                                           'phone':       phone,
                                           'mobile':      mobile,
                                           'fax':         fax,
                                           'email':       email,
                                           'url_site':    url_site,
                                           'create_or_attach_orga': False,
                                          }
                                         )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name,
                                          phone=phone, mobile=mobile, fax=fax,
                                          email=email, url_site=url_site,
                                         )
        self.assertRedirects(response, contact.get_absolute_url())

    def test_add_contact_vcf01(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.url.com
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        response = self._post_step1(errors=True,
                                    data={'user':       fields['user'].initial,
                                          'first_name': fields['first_name'].initial,
                                          'last_name':  fields['last_name'].initial,
                                          'phone':      fields['phone'].initial,
                                          'mobile':     fields['mobile'].initial,
                                          'fax':        fields['fax'].initial,
                                          'email':      fields['email'].initial,
                                          'url_site':   fields['url_site'].initial,
                                          'create_or_attach_orga': True,
                                         }
                                    )
        validation_text = _(u'Required, if you want to create organisation')
        self.assertFormError(response, 'form', 'work_name', validation_text)
        self.assertFormError(response, 'form', 'relation',  validation_text)
        self.assertEqual(contact_count, Contact.objects.count())
        self.assertEqual(orga_count,    Organisation.objects.count())

    def test_add_contact_vcf02(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Jean HUDARD
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
TEL;TYPE=WORK:33 33 33 33 33
EMAIL;TYPE=HOME:email@email.com
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=HOME:http://www.url.com/
URL;TYPE=WORK:www.work.com
ORG:Corporate\nEND:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial
        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'phone':         phone,
                               'mobile':        mobile,
                               'fax':           fax,
                               'email':         email,
                               'url_site':      url_site,
                               'create_or_attach_orga': False,
                               'work_name':     fields['work_name'].initial,
                               'work_phone':    fields['work_phone'].initial,
                               'work_email':    fields['work_email'].initial,
                               'work_url_site': fields['work_url_site'].initial,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())

        self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name, phone=phone,
                                mobile=mobile, fax=fax, email=email, url_site=url_site
                               )

    def test_add_contact_vcf03(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Jean HUDARD
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
        fields = self._post_step0(content).context['form'].fields
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

        response = self._post_step1(data={'user':          fields['user'].initial,
                                          'first_name':    first_name,
                                          'last_name':     last_name,
                                          'phone':         phone,
                                          'mobile':        mobile,
                                          'fax':           fax,
                                          'email':         email,
                                          'url_site':      url_site,
                                          'create_or_attach_orga': True,
                                          'relation':      REL_SUB_EMPLOYED_BY,
                                          'work_name':     work_name,
                                          'work_phone':    work_phone,
                                          'work_email':    work_email,
                                          'work_url_site': work_url_site,
                                         }
                                    )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count + 1,    Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=work_name, phone=work_phone,
                                       email=work_email, url_site=work_url_site,
                                      )
        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name,
                                          phone=phone, mobile=mobile, fax=fax, email=email,
                                         )
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)
        self.assertRedirects(response, contact.get_absolute_url())

    def test_add_contact_vcf04(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        orga = Organisation.objects.create(user=self.user, name='Corporate',
                                           phone='33 33 33 33 33', email='work@work.com',
                                           url_site='www.work.com',
                                          )
        self.assertEqual(orga_count + 1, Organisation.objects.count())

        content  = """BEGIN:VCARD
FN:Jean HUDARD
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
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        phone      = fields['phone'].initial
        mobile     = fields['mobile'].initial
        fax        = fields['fax'].initial
        email      = fields['email'].initial
        url_site   = fields['url_site'].initial

        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'phone':         phone,
                               'mobile':        mobile,
                               'fax':           fax,
                               'email':         email,
                               'url_site':      url_site,
                               'create_or_attach_orga': True,
                               'organisation':  fields['organisation'].initial,
                               'relation':      REL_SUB_EMPLOYED_BY,
                               'work_name':     fields['work_name'].initial,
                               'work_phone':    fields['work_phone'].initial,
                               'work_email':    fields['work_email'].initial,
                               'work_url_site': fields['work_url_site'].initial,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count + 1,    Organisation.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name,
                                          phone=phone, mobile=mobile, fax=fax, email=email,
                                         )
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

    def test_add_contact_vcf05(self):
        self.login()

        contact_count = Contact.objects.count()
        address_count = Address.objects.count()
        content = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.url.com
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        adr_last_name = fields['adr_last_name'].initial
        address       = fields['address'].initial
        city          = fields['city'].initial
        country       = fields['country'].initial
        code          = fields['code'].initial
        region        = fields['region'].initial

        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'phone':         fields['phone'].initial,
                               'mobile':        fields['mobile'].initial,
                               'fax':           fields['fax'].initial,
                               'email':         fields['email'].initial,
                               'url_site':      fields['url_site'].initial,
                               'adr_last_name': adr_last_name,
                               'address':       address,
                               'city':          city,
                               'country':       country,
                               'code':          code,
                               'region':        region,
                               'create_or_attach_orga': False,
                              }
                        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(address_count + 1, Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        address = self.get_object_or_fail(Address, name=adr_last_name, address=address,
                                          city=city, zipcode=code, country=country, department=region,
                                         )
        self.assertEqual(contact.billing_address, address)

    def test_add_contact_vcf06(self):
        self.login()
        contact_count = Contact.objects.count()
        address_count = Address.objects.count()
        orga_count    = Organisation.objects.count()
        content = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays
ADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays
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
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial

        adr_last_name = fields['adr_last_name'].initial
        address       = fields['address'].initial
        city          = fields['city'].initial
        country       = fields['country'].initial
        code          = fields['code'].initial
        region        = fields['region'].initial

        work_name      = fields['work_name'].initial
        work_adr_name  = fields['work_adr_name'].initial
        work_address   = fields['work_address'].initial
        work_city      = fields['work_city'].initial
        work_country   = fields['work_country'].initial
        work_code      = fields['work_code'].initial
        work_region    = fields['work_region'].initial

        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'phone':         fields['phone'].initial,
                               'mobile':        fields['mobile'].initial,
                               'fax':           fields['fax'].initial,
                               'email':         fields['email'].initial,
                               'url_site':      fields['url_site'].initial,
                               'adr_last_name': adr_last_name,
                               'address':       address,
                               'city':          city,
                               'country':       country,
                               'code':          code,
                               'region':        region,
                               'create_or_attach_orga': True,
                               'relation':      REL_SUB_EMPLOYED_BY,
                               'work_name':     work_name,
                               'work_adr_name': work_adr_name,
                               'work_address':  work_address,
                               'work_city':     work_city,
                               'work_country':  work_country,
                               'work_code':     work_code,
                               'work_region':   work_region,
                              }
                             )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count + 1,    Organisation.objects.count())
        self.assertEqual(address_count + 2, Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        orga    = self.get_object_or_fail(Organisation, name=work_name)
        c_addr  = self.get_object_or_fail(Address, name=adr_last_name, address=address, city=city,
                                          zipcode=code, country=country, department=region,
                                         )
        o_addr  = self.get_object_or_fail(Address, name=work_adr_name, address=work_address, city=work_city,
                                          zipcode=work_code, country=work_country, department=work_region,
                                         )
        self.assertEqual(contact.billing_address, c_addr)
        self.assertEqual(orga.billing_address,    o_addr)

    def test_add_contact_vcf07(self):
        self.login()

        contact_count = Contact.objects.count()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00',
                                    email='corp@corp.com', url_site='www.corp.com',
                                   )
        content  = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        response = self._post_step1(errors=True,
                                    data={'user':                 fields['user'].initial,
                                          'first_name':           fields['first_name'].initial,
                                          'last_name':            fields['last_name'].initial,
                                          'create_or_attach_orga': False,
                                          'organisation':         fields['organisation'].initial,
                                          'relation':             REL_SUB_EMPLOYED_BY,
                                          'work_name':            fields['work_name'].initial,
                                          'work_phone':           fields['work_phone'].initial,
                                          'work_email':           fields['work_email'].initial,
                                          'work_url_site':        fields['work_url_site'].initial,
                                          'work_adr_name':        fields['work_adr_name'].initial,
                                          'work_address':         fields['work_address'].initial,
                                          'work_city':            fields['work_city'].initial,
                                          'work_country':         fields['work_country'].initial,
                                          'work_code':            fields['work_code'].initial,
                                          'work_region':          fields['work_region'].initial,
                                          'update_orga_name':     True,
                                          'update_orga_phone':    True,
                                          'update_orga_email':    True,
                                          'update_orga_fax':      True,
                                          'update_orga_url_site': True,
                                          'update_orga_address':  True,
                                         }
                                    )
        validation_text = _(u'Create organisation not checked')
        self.assertFormError(response, 'form', 'update_orga_name',     validation_text)
        self.assertFormError(response, 'form', 'update_orga_phone',    validation_text)
        self.assertFormError(response, 'form', 'update_orga_email',    validation_text)
        self.assertFormError(response, 'form', 'update_orga_fax',      validation_text)
        self.assertFormError(response, 'form', 'update_orga_url_site', validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

    def test_add_contact_vcf08(self):
        self.login()

        contact_count = Contact.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        response = self._post_step1(errors=True,
                                    data={'user':                 fields['user'].initial,
                                          'first_name':           fields['first_name'].initial,
                                          'last_name':            fields['last_name'].initial,
                                          'create_or_attach_orga': True,
                                          'relation':             REL_SUB_EMPLOYED_BY,
                                          'work_name':            fields['work_name'].initial,
                                          'work_phone':           fields['work_phone'].initial,
                                          'work_email':           fields['work_email'].initial,
                                          'work_url_site':        fields['work_url_site'].initial,
                                          'work_adr_name':        fields['work_adr_name'].initial,
                                          'work_address':         fields['work_address'].initial,
                                          'work_city':            fields['work_city'].initial,
                                          'work_country':         fields['work_country'].initial,
                                          'work_code':            fields['work_code'].initial,
                                          'work_region':          fields['work_region'].initial,
                                          'update_orga_name':     True,
                                          'update_orga_phone':    True,
                                          'update_orga_email':    True,
                                          'update_orga_fax':      True,
                                          'update_orga_url_site': True,
                                          'update_orga_address':  True,
                                         }
                                    )
        validation_text = _(u'Organisation not selected')
        self.assertFormError(response, 'form', 'update_orga_name',     validation_text)
        self.assertFormError(response, 'form', 'update_orga_phone',    validation_text)
        self.assertFormError(response, 'form', 'update_orga_email',    validation_text)
        self.assertFormError(response, 'form', 'update_orga_fax',      validation_text)
        self.assertFormError(response, 'form', 'update_orga_url_site', validation_text)
        self.assertFormError(response, 'form', 'update_orga_address',  validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

    def test_add_contact_vcf09(self):
        self.login()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00',
                                    email='corp@corp.com', url_site='www.corp.com',
                                   )
        content  = """BEGIN:VCARD
FN:Jean HUDARD
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        response = self._post_step1(errors=True,
                                    data={'user':                 fields['user'].initial,
                                          'first_name':           fields['first_name'].initial,
                                          'last_name':            fields['last_name'].initial,
                                          'create_or_attach_orga': True,
                                          'organisation':         fields['organisation'].initial,
                                          'relation':             REL_SUB_EMPLOYED_BY,
                                          'update_orga_name':     True,
                                          'update_orga_phone':    True,
                                          'update_orga_fax':      True,
                                          'update_orga_email':    True,
                                          'update_orga_url_site': True,
                                          'update_orga_address':  True,
                                         }
                                    )
        validation_text = _(u'Required, if you want to update organisation')
        self.assertFormError(response, 'form', 'work_phone',    validation_text)
        self.assertFormError(response, 'form', 'work_email',    validation_text)
        self.assertFormError(response, 'form', 'work_fax',      validation_text)
        self.assertFormError(response, 'form', 'work_url_site', validation_text)

    def test_add_contact_vcf10(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00',
                                           email='corp@corp.com', url_site='www.corp.com',
                                          )
        orga.billing_address = Address.objects.create(name='Org_name',
                                                      address='Org_address',
                                                      city='Org_city',
                                                      country='Org_country',
                                                      zipcode='Org_zipcode',
                                                      department='Org_department',
                                                      content_type_id=ContentType.objects.get_for_model(Organisation).id,
                                                      object_id=orga.id,
                                                     )
        orga.save()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=WORK:www.work.com
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        self._post_step1(data={'user':                 fields['user'].initial,
                               'first_name':           fields['first_name'].initial,
                               'last_name':            fields['last_name'].initial,
                               'create_or_attach_orga': True,
                               'organisation':         fields['organisation'].initial,
                               'relation':             REL_SUB_EMPLOYED_BY,
                               'work_name':            fields['work_name'].initial,
                               'work_phone':           fields['work_phone'].initial,
                               'work_email':           fields['work_email'].initial,
                               'work_url_site':        fields['work_url_site'].initial,
                               'work_adr_name':        fields['work_adr_name'].initial,
                               'work_address':         fields['work_address'].initial,
                               'work_city':            fields['work_city'].initial,
                               'work_country':         fields['work_country'].initial,
                               'work_code':            fields['work_code'].initial,
                               'work_region':          fields['work_region'].initial,
                               'update_orga_name':     True,
                               'update_orga_phone':    True,
                               'update_orga_email':    True,
                               'update_orga_url_site': True,
                               'update_orga_address':  True,
                              }
                        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        orga = self.refresh(orga)
        billing_address = orga.billing_address

        vobj = vcf_lib.readOne(content)
        adr = vobj.adr.value
        org = vobj.org.value[0]
        self.assertEqual(orga.name,                  org)
        self.assertEqual(orga.phone,                 vobj.tel.value)
        self.assertEqual(orga.email,                 vobj.email.value)
        self.assertEqual(orga.url_site,              'http://www.work.com/')
        self.assertEqual(billing_address.name,       org)
        self.assertEqual(billing_address.address,    ' '.join([adr.box, adr.street]))
        self.assertEqual(billing_address.city,       adr.city)
        self.assertEqual(billing_address.country,    adr.country)
        self.assertEqual(billing_address.zipcode,    adr.code)
        self.assertEqual(billing_address.department, adr.region)

    def test_add_contact_vcf11(self):
        self.login()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00',
                                    email='corp@corp.com', url_site='www.corp.com',
                                   )

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
ADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays
ORG:Corporate
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        orga_id       = fields['organisation'].initial
        work_adr_name = fields['work_adr_name'].initial
        work_address  = fields['work_address'].initial
        work_city     = fields['work_city'].initial
        work_country  = fields['work_country'].initial
        work_code     = fields['work_code'].initial
        work_region   = fields['work_region'].initial
        self._post_step1(data={'user':                 fields['user'].initial,
                               'first_name':           fields['first_name'].initial,
                               'last_name':            fields['last_name'].initial,
                               'create_or_attach_orga': True,
                               'organisation':         orga_id,
                               'relation':             REL_SUB_EMPLOYED_BY,
                               'work_name':            fields['work_name'].initial,
                               'work_adr_name':        work_adr_name,
                               'work_address':         work_address,
                               'work_city':            work_city,
                               'work_country':         work_country,
                               'work_code':            work_code,
                               'work_region':          work_region,
                               'update_orga_address':  True,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count + 1, Address.objects.count())

        address = self.get_object_or_fail(Address, name=work_adr_name, address=work_address,
                                          city=work_city, zipcode=work_code,
                                          country=work_country, department=work_region,
                                         )
        orga    = self.get_object_or_fail(Organisation, id=orga_id)

        vobj = vcf_lib.readOne(content)
        adr = vobj.adr.value

        self.assertEqual(address.name,       vobj.org.value[0])
        self.assertEqual(address.address,    ' '.join([adr.box, adr.street]))
        self.assertEqual(address.city,       adr.city)
        self.assertEqual(address.country,    adr.country)
        self.assertEqual(address.zipcode,    adr.code)
        self.assertEqual(address.department, adr.region)

        self.assertEqual(orga.billing_address, address)

    def test_add_contact_vcf12(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Image.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
TEL;TYPE=HOME:00 00 00 00 00
TEL;TYPE=CELL:11 11 11 11 11
TEL;TYPE=FAX:22 22 22 22 22
EMAIL;TYPE=HOME:email@email.com
URL;TYPE=HOME:www.url.com
PHOTO:""" \
'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' \
'\nEND:VCARD'
        fields = self._post_step0(content).context['form'].fields
        user       = fields['user'].initial
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        url_site   = fields['url_site'].initial
        self._post_step1(data={'user':          user,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'phone':         fields['phone'].initial,
                               'mobile':        fields['mobile'].initial,
                               'fax':           fields['fax'].initial,
                               'email':         fields['email'].initial,
                               'url_site':      url_site,
                               'create_or_attach_orga': False,
                              }
                        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count,       Image.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        # url_site='http://www.url.com/' and not url_site=url_site because URLField add 'http://' and '/'
        self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name,
                                url_site='http://www.url.com/',
                               )

    def test_add_contact_vcf13(self):
        self.login()

        contact_count = Contact.objects.count()
        content  = 'BEGIN:VCARD\nN;ENCODING=8BIT:HUDARD;Jean;;%(civility)s;\nTITLE:%(position)s\nEND:VCARD' % {
                            'civility': _('Mr.'),
                            'position': _('CEO'),
                        }
        response = self._post_step0(content)

        with self.assertNoException():
            form = response.context['form']
            user_id     = form.fields['user'].initial
            first_name  = form.fields['first_name'].initial
            last_name   = form.fields['last_name'].initial
            civility_id = form.fields['civility'].initial
            position_id = form.fields['position'].initial

        self.assertEqual(self.user.id, user_id)
        self.assertEqual('Jean', first_name)
        self.assertEqual('HUDARD', last_name)
        self.assertEqual(3, civility_id) #pk=3 see persons.populate
        self.assertEqual(1, position_id) #pk=1 idem

        self._post_step1(data={'user':       user_id,
                               'first_name': first_name,
                               'last_name':  last_name,
                               'civility':   civility_id,
                               'position':   position_id,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.get_object_or_fail(Contact, civility=civility_id, first_name=first_name,
                                last_name=last_name, position=position_id,
                               )

    def test_add_contact_vcf14(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Image.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
PHOTO;TYPE=JPEG:""" \
'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' \
'\nEND:VCARD'
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        image      = fields['image_encoded'].initial
        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'create_or_attach_orga': False,
                               'image_encoded': image,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count + 1,   Image.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.assertEqual(address_count,     Address.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertTrue(contact.image)
        self.assertEqual(_(u'Image of %s') % contact, contact.image.name)
        contact.image.image.delete()

    def test_add_contact_vcf15(self):
        self.login()

        vcf_forms.URL_START = vcf_forms.URL_START + ('file',)

        path_base = os_path.join(settings.CREME_ROOT, 'static', 'chantilly', 'images', '500.png')
        self.assert_(os_path.exists(path_base))
        path = 'file:///' + os_path.normpath(path_base)

        contact_count = Contact.objects.count()
        #image_count   = Image.objects.count()
        self.assertEqual(0, Image.objects.count())

        content  = """BEGIN:VCARD
FN:Jean HUDARD
PHOTO;VALUE=URL:%s
END:VCARD""" % path
        fields = self._post_step0(content).context['form'].fields
        first_name = fields['first_name'].initial
        last_name  = fields['last_name'].initial
        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    first_name,
                               'last_name':     last_name,
                               'image_encoded': fields['image_encoded'].initial,
                              }
                        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        #self.assertEqual(image_count + 1,   Image.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

        images = Image.objects.all()
        self.assertEqual(1, len(images))

        image = images[0]
        self.assertEqual(image,                       contact.image)
        self.assertEqual(_(u'Image of %s') % contact, image.name)
        image.delete()

    def test_add_contact_vcf16(self):
        self.login()

        contact_count = Contact.objects.count()
        image_count   = Image.objects.count()

        content  = """BEGIN:VCARD
FN:Jean HUDARD
PHOTO;VALUE=URL:http://wwwwwwwww.wwwwwwwww.wwwwwwww/wwwwwww.jpg
END:VCARD"""
        fields = self._post_step0(content).context['form'].fields
        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    fields['first_name'].initial,
                               'last_name':     fields['last_name'].initial,
                               'image_encoded': fields['image_encoded'].initial,
                              }
                        )

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count,       Image.objects.count())

    def test_add_contact_vcf17(self):
        self.login()

        settings.VCF_IMAGE_MAX_SIZE = 10240 #(10 kB)
        vcf_forms.URL_START = vcf_forms.URL_START + ('file',)

        contact_count = Contact.objects.count()
        image_count   = Image.objects.count()
        content  = """BEGIN:VCARD
FN:Jean HUDARD
PHOTO;VALUE=URL:file:///%s
END:VCARD""" % os_path.normpath(os_path.join(settings.CREME_ROOT, 'static', 'images', '500.png'))
        fields = self._post_step0(content).context['form'].fields
        self._post_step1(data={'user':          fields['user'].initial,
                               'first_name':    fields['first_name'].initial,
                               'last_name':     fields['last_name'].initial,
                               'image_encoded': fields['image_encoded'].initial,
                              }
                        )
        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(image_count,       Image.objects.count())
