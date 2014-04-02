# -*- coding: utf-8 -*-

try:
    from os import path as os_path
    from tempfile import NamedTemporaryFile

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.encoding import smart_str
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase

    from creme.media_managers.models import Image

    from creme.persons.models import Contact, Organisation, Address
    from creme.persons.constants import REL_SUB_EMPLOYED_BY

    from ..forms import vcf as vcf_forms
    from ..vcf_lib import readOne as read_vcf
    from ..vcf_lib.base import ContentLine
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class VcfImportTestCase(CremeTestCase):
    IMPORT_URL = '/vcfs/vcf'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'persons')

    def _post_step0(self, content):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(smart_str(content))
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

        firt_name, sep, last_name = read_vcf(content).fn.value.partition(' ')
        self.assertEqual(form['first_name'].field.initial, firt_name)
        self.assertEqual(form['last_name'].field.initial,  last_name)

    def test_parsing_vcf01(self): #TODO: use BDAY
        self.login()

        first_name = u'Yûna'
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
        content  = u"""BEGIN:VCARD
N:%(last_name)s;%(first_name)s;;%(civility)s;
TITLE:%(position)s
BDAY;value=date:02-10
ADR;TYPE=HOME:%(box)s;;%(street)s;%(city)s;%(region)s;%(code)s;%(country)s
TEL;TYPE=HOME:%(phone)s
TEL;TYPE=CELL:%(mobile)s
TEL;TYPE=FAX:%(fax)s
EMAIL;TYPE=HOME:%(email)s
URL;TYPE=HOME:%(site)s
END:VCARD""" % {'last_name':  last_name,
                'first_name': first_name,
                'civility':   civility,
                'position':   position,
                'phone':      phone,
                'mobile':     mobile,
                'fax':        fax,
                'email':      email,
                'site':       site,

                'box':     box,
                'street':  street,
                'city':    city,
                'region':  region,
                'code':    code,
                'country': country,
               }
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = read_vcf(content)
        n_value = vobj.n.value
        self.assertEqual(civility, n_value.prefix)
        self.assertEqual(_(u'Read in VCF File : ') + civility,
                         fields['civility'].help_text
                        )

        self.assertEqual(first_name, n_value.given)
        self.assertEqual(first_name, fields['first_name'].initial)

        self.assertEqual(last_name,  n_value.family)
        self.assertEqual(last_name, fields['last_name'].initial)

        #print '=====>', vobj, vobj.bday, type(vobj.bday)

        tel = vobj.contents['tel']
        self.assertEqual(phone, tel[0].value)
        self.assertEqual(phone, fields['phone'].initial)

        self.assertEqual(mobile, tel[1].value)
        self.assertEqual(mobile, fields['mobile'].initial)

        self.assertEqual(fax, tel[2].value)
        self.assertEqual(fax, fields['fax'].initial)

        self.assertEqual(position, vobj.title.value)
        self.assertEqual(fields['position'].help_text,
                         _(u'Read in VCF File : ') + position
                        )

        self.assertEqual(email, vobj.email.value)
        self.assertEqual(email, fields['email'].initial)

        self.assertEqual(site, vobj.url.value)
        self.assertEqual(site, fields['url_site'].initial)

        adr_value = vobj.adr.value
        self.assertEqual(last_name, fields['adr_last_name'].initial)

        self.assertEqual(street, adr_value.street)
        self.assertEqual(box,    adr_value.box)
        self.assertEqual(fields['address'].initial, '%s %s' %(box, street))

        self.assertEqual(city, adr_value.city)
        self.assertEqual(city, fields['city'].initial)

        self.assertEqual(country, adr_value.country)
        self.assertEqual(country, fields['country'].initial)

        self.assertEqual(code, adr_value.code)
        self.assertEqual(code, fields['code'].initial)

        self.assertEqual(region, adr_value.region)
        self.assertEqual(region, fields['region'].initial)

    def test_parsing_vcf02(self):
        self.login()

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
        content = u"""BEGIN:VCARD
FN:Evangéline McDowell
ORG:%(name)s
ADR;TYPE=WORK:%(box)s;;%(street)s;%(city)s;%(region)s;%(code)s;%(country)s
TEL;TYPE=WORK:%(phone)s
EMAIL;TYPE=WORK:%(email)s
URL;TYPE=WORK:%(site)s
END:VCARD""" % {'name':  name,
                'phone': phone,
                'email': email,
                'site':  site,

                'box':     box,
                'street':  street,
                'city':    city,
                'region':  region,
                'code':    code,
                'country': country,
               }
        response = self._post_step0(content)

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

        self.assertEqual(fields['work_adr_name'].initial, name)

        adr = vobj.adr.value
        self.assertEqual(box,    adr.box)
        self.assertEqual(street, adr.street)
        self.assertEqual(fields['work_address'].initial,  '%s %s' % (box, street))

        self.assertEqual(city, adr.city)
        self.assertEqual(city, fields['work_city'].initial)

        self.assertEqual(region, adr.region)
        self.assertEqual(region, fields['work_region'].initial)

        self.assertEqual(code, adr.code)
        self.assertEqual(code, fields['work_code'].initial)

        self.assertEqual(country, adr.country)
        self.assertEqual(country, fields['work_country'].initial)

    def test_parsing_vcf03(self):
        "Address without type"
        self.login()

        box = '852'
        street = '21 Run street'
        city = 'Mahora'
        region = 'Kansai'
        code = '434354'
        country = 'Japan'
        content = u"""begin:vcard
fn:Misora Kasoga
adr:%(box)s;;%(street)s;%(city)s;%(region)s;%(code)s;%(country)s
tel:00 00 00 00 00
email:email@email.com
x-mozilla-html:FALSE
url:www.url.com
version:2.1
end:vcard""" % {'box':     box,
                'street':  street,
                'city':    city,
                'region':  region,
                'code':    code,
                'country': country
               }
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields

        vobj = read_vcf(content)
        #self.assertEqual('<VERSION{}2.1>', str(vobj.version))

        help_prefix = _(u'Read in VCF File without type : ')
        adr_value = vobj.adr.value

        self.assertEqual(box,     adr_value.box)
        self.assertEqual(street,  adr_value.street)
        self.assertEqual(city,    adr_value.city)
        self.assertEqual(region,  adr_value.region)
        self.assertEqual(code,    adr_value.code)
        self.assertEqual(country, adr_value.country)

        self.assertEqual(fields['address'].help_text,
                         help_prefix + ', '.join([box, street, city, region, code, country])
                        )
        self.assertEqual(fields['phone'].help_text,    help_prefix + vobj.tel.value)
        self.assertEqual(fields['email'].help_text,    help_prefix + vobj.email.value)
        self.assertEqual(fields['url_site'].help_text, help_prefix + vobj.url.value)

    def test_parsing_vcf04(self):
        "Existing Organisation"
        self.login()

        name = 'Negima'
        orga = Organisation.objects.create(user=self.user, name=name)
        content = u"""BEGIN:VCARD
N:Konoe Konoka
ORG:%(name)s
ADR;TYPE=WORK:56;;Second street;Kyoto;Kyoto region;7777;Japan
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:email@email.com
URL;TYPE=WORK:www.web-site.com
END:VCARD""" % {'name': name}
        response = self._post_step0(content)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(form['organisation'].field.initial, orga.id)

    def test_parsing_vcf05(self):
        "Multi line, escape chars"
        self.login()

        first_name = u'Fûka'
        last_name = 'Naritaki'
        content  = r"""BEGIN:VCARD
VERSION:3.0
FN:%(long_name)s
N:%(last_name)s;%(first_name)s
NICKNAME:The twins
ACCOUNT;type=HOME:123-145789-10
ADR;type=HOME:;;Main Street 256\;\n1rst floor\, Pink door;Mahora;;598;Japan
ORG:University of Mahora\, Department of
  Robotics
END:VCARD""" % {'first_name': first_name,
                'last_name':  last_name,
                'long_name':  first_name + last_name + ' (& Fumika)',
               }
        response = self._post_step0(content)

        #with self.assertNoException():
            #fields = response.context['form'].fields

        vobj = read_vcf(content)

        version = vobj.version
        self.assertIsInstance(version, ContentLine)
        #self.assertEqual('<VERSION{}3.0>', str(version))

        n_value = vobj.n.value
        self.assertEqual(first_name, n_value.given)
        self.assertEqual(last_name,  n_value.family)

        self.assertEqual('University of Mahora, Department of Robotics',
                         vobj.org.value[0]
                        )

        self.assertEqual('Main Street 256;\n1rst floor, Pink door',
                         vobj.adr.value.street
                        )

    def test_add_contact_vcf00(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content = u"""BEGIN:VCARD
VERSION:3.0
FN:Ako IZUMI
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

        contact = self.get_object_or_fail(Contact, first_name=first_name,
                                          last_name=last_name,
                                          phone=phone, mobile=mobile, fax=fax,
                                          email=email, url_site=url_site,
                                         )
        self.assertRedirects(response, contact.get_absolute_url())

    def test_add_contact_vcf01(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content = u"""BEGIN:VCARD
FN:Yue AYASE
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
FN:Asuna Kagurazaka
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

        content = u"""BEGIN:VCARD
FN:Haruna Saotome
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
        content = u"""BEGIN:VCARD
FN:Chisame Hasegawa
ADR;TYPE=HOME:78;;Geek avenue;New-York;;6969;USA
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
        content = u"""BEGIN:VCARD
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
        content = """BEGIN:VCARD
FN:Setsuna Sakurazaki
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
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
        content = """BEGIN:VCARD
FN:Makie SASAKI
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
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

        name = 'Negima'
        Organisation.objects.create(user=self.user, name=name, phone='00 00 00 00 00',
                                    email='corp@corp.com', url_site='www.corp.com',
                                   )
        content = u"""BEGIN:VCARD
FN:Akira Ookôchi
ORG:%s
END:VCARD""" % name
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

        name = 'Robotic club'
        orga = Organisation.objects.create(user=self.user, name=name, phone='00 00 00 00 00',
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

        content = u"""BEGIN:VCARD
FN:Chachamaru KARAKURI
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
TEL;TYPE=WORK:11 11 11 11 11
EMAIL;TYPE=WORK:work@work.com
URL;TYPE=WORK:www.work.com
ORG:%s
END:VCARD""" % name
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

        vobj = read_vcf(content)
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

        name = 'Astronomy club'
        Organisation.objects.create(user=self.user, name=name, phone='00 00 00 00 00',
                                    email='corp@corp.com', url_site='www.corp.com',
                                   )

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD
FN:Chizuru NABA
ADR;TYPE=WORK:99;;Tree place;Mahora;Kanto;42;Japan
ORG:%s
END:VCARD""" % name
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

        vobj = read_vcf(content)
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

        content = """BEGIN:VCARD
FN:Kazumi ASAKURA
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
        first_name = 'Negi'
        last_name  = 'Springfield'
        content = 'BEGIN:VCARD\nN;ENCODING=8BIT:%(last_name)s;%(first_name)s;;%(civility)s;\nTITLE:%(position)s\nEND:VCARD' % {
                            'first_name': first_name,
                            'last_name':  last_name,
                            'civility':   _('Mr.'),
                            'position':   _('CEO'),
                        }
        response = self._post_step0(content)

        with self.assertNoException():
            fields = response.context['form'].fields
            user_id      = fields['user'].initial
            first_name_f = fields['first_name']
            last_name_f  = fields['last_name']
            civility_id  = fields['civility'].initial
            position_id  = fields['position'].initial

        self.assertEqual(self.user.id, user_id)
        self.assertEqual(first_name, first_name_f.initial)
        self.assertEqual(last_name, last_name_f.initial)
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

        content = """BEGIN:VCARD
FN:Sakurako SHIINA
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
        self.assertTrue(os_path.exists(path_base))
        path = 'file:///' + os_path.normpath(path_base)

        contact_count = Contact.objects.count()
        #image_count   = Image.objects.count()
        self.assertEqual(0, Image.objects.count())

        content  = """BEGIN:VCARD
FN:Ayaka YUKIHIRO
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

        content = u"""BEGIN:VCARD
FN:Kaede NAGASE
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
FN:Satomi HAKASE
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
