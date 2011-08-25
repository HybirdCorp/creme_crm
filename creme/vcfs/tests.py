# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import os
from tempfile import NamedTemporaryFile

from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from creme_core.tests.base import CremeTestCase
from creme_core.models import Relation, RelationType

from media_managers.models import Image

from persons.models import Contact, Organisation, Address
from persons.constants import *

from vcfs import vcf_lib
from vcfs.forms import vcf


class VcfTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'persons', 'vcfs')

    def test_populate(self): #test relationtype creation with constraints
        def get_relationtype_or_fail(pk):
            try:
                return RelationType.objects.get(pk=pk)
            except RelationType.DoesNotExist:
                self.fail('Bad populate: unfoundable RelationType with pk=%s' % pk)

        rel_sub_employed = get_relationtype_or_fail(REL_SUB_EMPLOYED_BY)
        rel_obj_employed = get_relationtype_or_fail(REL_OBJ_EMPLOYED_BY)
        rel_sub_customer_supplier = get_relationtype_or_fail(REL_SUB_CUSTOMER_SUPPLIER)
        rel_obj_customer_supplier = get_relationtype_or_fail(REL_OBJ_CUSTOMER_SUPPLIER)

        assertEqual = self.assertEqual
        assertEqual(rel_sub_employed.symmetric_type_id, rel_obj_employed.id)
        assertEqual(rel_obj_employed.symmetric_type_id, rel_sub_employed.id)

        get_ct = ContentType.objects.get_for_model
        ct_id_contact = get_ct(Contact).id
        ct_id_orga    = get_ct(Organisation).id
        assertEqual([ct_id_contact], [ct.id for ct in rel_sub_employed.subject_ctypes.all()])
        assertEqual([ct_id_orga],    [ct.id for ct in rel_obj_employed.subject_ctypes.all()])

        ct_id_set = set((ct_id_contact, ct_id_orga))
        assertEqual(ct_id_set, set(ct.id for ct in rel_sub_customer_supplier.subject_ctypes.all()))
        assertEqual(ct_id_set, set(ct.id for ct in rel_obj_customer_supplier.subject_ctypes.all()))

    def _build_filedata(self, content_str):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(content_str)
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        return tmpfile

    def _post_form_step_0(self, url, file):
        return self.client.post(url,
                                follow=True,
                                data={
                                        'user':     self.user,
                                        'vcf_step': 0,
                                        'vcf_file': file,
                                     }
                                )

    def _no_from_error(self, response):
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

    def test_add_vcf(self):
        self.login()

        url = '/vcfs/vcf'
        self.assertEqual(200, self.client.get(url).status_code)

        content  = """BEGIN:VCARD\nFN:Test\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0(url, filedata.file)

        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_('value="1"' in unicode(form['vcf_step']))

    def test_parsing_vcf00(self):
        self.login()

        content  = """BEGIN:VCARD\nFN:Prénom Nom\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0('/vcfs/vcf', filedata.file)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assert_('value="1"' in unicode(form['vcf_step']))

        firt_name, sep, last_name = vcf_lib.readOne(content).fn.value.partition(' ')
        assertEqual = self.assertEqual
        assertEqual(form['first_name'].field.initial, firt_name)
        assertEqual(form['last_name'].field.initial,  last_name)

    def test_parsing_vcf01(self):
        self.login()

        content  = """BEGIN:VCARD\nN:Nom;Prénom;;Civilité;\nTITLE:Directeur adjoint\nADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nEMAIL;TYPE=HOME:email@email.com\nURL;TYPE=HOME:www.my-website.com\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0('/vcfs/vcf', filedata.file)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        vobj = vcf_lib.readOne(content)
        n_value = vobj.n.value

        assertEqual = self.assertEqual
        assertEqual(form['civility'].field.help_text, ''.join([_(u'Read in VCF File : '), n_value.prefix]))
        assertEqual(form['first_name'].field.initial, n_value.given)
        assertEqual(form['last_name'].field.initial,  n_value.family)

        tel = vobj.contents['tel']
        assertEqual(form['phone'].field.initial,  tel[0].value)
        assertEqual(form['mobile'].field.initial, tel[1].value)
        assertEqual(form['fax'].field.initial,    tel[2].value)

        assertEqual(form['position'].field.help_text, ''.join([_(u'Read in VCF File : '), vobj.title.value]))
        assertEqual(form['email'].field.initial,       vobj.email.value)
        assertEqual(form['url_site'].field.initial,    vobj.url.value)

        adr_value = vobj.adr.value
        assertEqual(form['adr_last_name'].field.initial, n_value.family)
        assertEqual(form['address'].field.initial,       ' '.join([adr_value.box, adr_value.street]))
        assertEqual(form['city'].field.initial,          adr_value.city)
        assertEqual(form['country'].field.initial,       adr_value.country)
        assertEqual(form['code'].field.initial,          adr_value.code)
        assertEqual(form['region'].field.initial,        adr_value.region)

    def test_parsing_vcf02(self):
        self.login()

        content  = """BEGIN:VCARD\nFN:Prénom Nom\nORG:Corporate\nADR;TYPE=WORK:Numéro de rue;;Nom de la rue;Ville;Region;Code Postal;Pays\nTEL;TYPE=WORK:00 00 00 00 00\nEMAIL;TYPE=WORK:corp@corp.com\nURL;TYPE=WORK:www.corp.com\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0('/vcfs/vcf', filedata.file)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        vobj = vcf_lib.readOne(content)
        assertEqual = self.assertEqual
        assertEqual(form['work_name'].field.initial,     vobj.org.value[0])
        assertEqual(form['work_phone'].field.initial,    vobj.tel.value)
        assertEqual(form['work_email'].field.initial,    vobj.email.value)
        assertEqual(form['work_url_site'].field.initial, vobj.url.value)
        assertEqual(form['work_adr_name'].field.initial, vobj.org.value[0])
        assertEqual(form['work_address'].field.initial,  ' '.join([vobj.adr.value.box, vobj.adr.value.street]))
        assertEqual(form['work_city'].field.initial,     vobj.adr.value.city)
        assertEqual(form['work_region'].field.initial,   vobj.adr.value.region)
        assertEqual(form['work_code'].field.initial,     vobj.adr.value.code)
        assertEqual(form['work_country'].field.initial,  vobj.adr.value.country)

    def test_parsing_vcf03(self):
        self.login()

        content  = """BEGIN:VCARD\nFN:Prénom Nom\nADR:Numéro de rue;;Nom de la rue;Ville;Région;Code Postal;Pays\nTEL:00 00 00 00 00\nEMAIL:email@email.com\nURL:www.url.com\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0('/vcfs/vcf', filedata.file)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        vobj = vcf_lib.readOne(content)
        help_prefix = _(u'Read in VCF File without type : ')
        adr_value = vobj.adr.value
        adr = ', '.join([adr_value.box, adr_value.street, adr_value.city, adr_value.region, adr_value.code, adr_value.country])
        assertEqual = self.assertEqual
        assertEqual(form['address'].field.help_text,  ''.join([help_prefix, adr]))
        assertEqual(form['phone'].field.help_text,    ''.join([help_prefix, vobj.tel.value]))
        assertEqual(form['email'].field.help_text,    ''.join([help_prefix, vobj.email.value]))
        assertEqual(form['url_site'].field.help_text, ''.join([help_prefix, vobj.url.value]))

    def test_parsing_vcf04(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Corporate')
        content  = """BEGIN:VCARD\nN:Prénom Nom\nORG:Corporate\nADR;TYPE=WORK:Numéro de rue;;Nom de la rue;Ville;Region;Code Postal;Pays\nTEL;TYPE=WORK:11 11 11 11 11\nEMAIL;TYPE=WORK:email@email.com\nURL;TYPE=WORK:www.web-site.com\nEND:VCARD"""
        filedata = self._build_filedata(content)
        response = self._post_form_step_0('/vcfs/vcf', filedata.file)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(form['organisation'].field.initial, orga.id)

    def test_add_contact_vcf00(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nEMAIL;TYPE=HOME:email@email.com\nURL;TYPE=HOME:http://www.url.com/\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        self.assert_('value="1"' in unicode(form['vcf_step']))

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':        user,
                                            'vcf_step':    1,
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
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())
        assertEqual(address_count,     Address.objects.count())

        try:
            Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email, url_site=url_site)
        except Exception, e:
            self.fail(str(e) + str(Contact.objects.all()))

    def test_add_contact_vcf01(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nEMAIL;TYPE=HOME:email@email.com\nURL;TYPE=HOME:www.url.com\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':        user,
                                            'vcf_step':    1,
                                            'first_name':  first_name,
                                            'last_name':   last_name,
                                            'phone':       phone,
                                            'mobile':      mobile,
                                            'fax':         fax,
                                            'email':       email,
                                            'url_site':    url_site,
                                            'create_or_attach_orga': True,
                                         }
                                    )
        validation_text = _(u'Required, if you want to create organisation')
        assertFormError = self.assertFormError
        assertFormError(response, 'form', 'work_name', validation_text)
        assertFormError(response, 'form', 'relation',  validation_text)

        assertEqual = self.assertEqual
        assertEqual(contact_count, Contact.objects.count())
        assertEqual(orga_count,    Organisation.objects.count())

    def test_add_contact_vcf02(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nTEL;TYPE=WORK:33 33 33 33 33\nEMAIL;TYPE=HOME:email@email.com\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=HOME:http://www.url.com/\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'phone':         phone,
                                            'mobile':        mobile,
                                            'fax':           fax,
                                            'email':         email,
                                            'url_site':      url_site,
                                            'create_or_attach_orga': False,
                                            'work_name':     work_name,
                                            'work_phone':    work_phone,
                                            'work_email':    work_email,
                                            'work_url_site': work_url_site,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())

        try:
            Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email, url_site=url_site)
        except Exception, e:
            self.fail(str(e))

    def test_add_contact_vcf03(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nTEL;TYPE=WORK:33 33 33 33 33\nEMAIL;TYPE=HOME:email@email.com\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=HOME:www.url.com\nURL;TYPE=WORK:http://www.work.com/\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial


        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
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
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count + 1,    Organisation.objects.count())

        try:
            orga = Organisation.objects.get(name=work_name, phone=work_phone, email=work_email, url_site=work_url_site)
            contact = Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email)
            Relation.objects.get(subject_entity=contact.id, type=REL_SUB_EMPLOYED_BY, object_entity=orga.id)
        except Exception, e:
            self.fail(str(e))

    def test_add_contact_vcf04(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()
        orga = Organisation.objects.create(user=self.user, name='Corporate', phone='33 33 33 33 33', email='work@work.com', url_site='www.work.com')
        self.assertEqual(orga_count + 1, Organisation.objects.count())

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nTEL;TYPE=WORK:33 33 33 33 33\nEMAIL;TYPE=HOME:email@email.com\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=HOME:www.url.com\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        orga_id       = form['organisation'].field.initial
        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'phone':         phone,
                                            'mobile':        mobile,
                                            'fax':           fax,
                                            'email':         email,
                                            'url_site':      url_site,
                                            'create_or_attach_orga': True,
                                            'organisation':  orga_id,
                                            'relation':      REL_SUB_EMPLOYED_BY,
                                            'work_name':     work_name,
                                            'work_phone':    work_phone,
                                            'work_email':    work_email,
                                            'work_url_site': work_url_site,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count + 1,    Organisation.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email)
            Relation.objects.get(subject_entity=contact.id, type=REL_SUB_EMPLOYED_BY, object_entity=orga.id)
        except Exception, e:
            self.fail(str(e))

    def test_add_contact_vcf05(self):
        self.login()

        contact_count = Contact.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nEMAIL;TYPE=HOME:email@email.com\nURL;TYPE=HOME:www.url.com\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        adr_last_name = form['adr_last_name'].field.initial
        address       = form['address'].field.initial
        city          = form['city'].field.initial
        country       = form['country'].field.initial
        code          = form['code'].field.initial
        region        = form['region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'phone':         phone,
                                            'mobile':        mobile,
                                            'fax':           fax,
                                            'email':         email,
                                            'url_site':      url_site,
                                            'adr_last_name': adr_last_name,
                                            'address':       address,
                                            'city':          city,
                                            'country':       country,
                                            'code':          code,
                                            'region':        region,
                                            'create_or_attach_orga': False,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(address_count + 1, Address.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email)
            address = Address.objects.get(name=adr_last_name, address=address, city=city, zipcode=code, country=country, department=region)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(contact.billing_address, address)

    def test_add_contact_vcf06(self):
        self.login()

        contact_count = Contact.objects.count()
        address_count = Address.objects.count()
        orga_count    = Organisation.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=HOME:Numéro de rue;;Nom de rue;Ville;Région;Code postal;Pays\nADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nTEL;TYPE=WORK:33 33 33 33 33\nEMAIL;TYPE=HOME:email@email.com\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=HOME:www.url.com\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        adr_last_name = form['adr_last_name'].field.initial
        address       = form['address'].field.initial
        city          = form['city'].field.initial
        country       = form['country'].field.initial
        code          = form['code'].field.initial
        region        = form['region'].field.initial

        work_name      = form['work_name'].field.initial
        work_adr_name  = form['work_adr_name'].field.initial
        work_address   = form['work_address'].field.initial
        work_city      = form['work_city'].field.initial
        work_country   = form['work_country'].field.initial
        work_code      = form['work_code'].field.initial
        work_region    = form['work_region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'phone':         phone,
                                            'mobile':        mobile,
                                            'fax':           fax,
                                            'email':         email,
                                            'url_site':      url_site,
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
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count + 1,    Organisation.objects.count())
        assertEqual(address_count + 2, Address.objects.count())

        try:
            contact         = Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email)
            orga            = Organisation.objects.get(name=work_name)
            address_contact = Address.objects.get(name=adr_last_name, address=address, city=city, zipcode=code, country=country, department=region)
            address_orga    = Address.objects.get(name=work_adr_name, address=work_address, city=work_city, zipcode=work_code, country=work_country, department=work_region)
        except Exception, e:
            self.fail(str(e))

        assertEqual(contact.billing_address, address_contact)
        assertEqual(orga.billing_address,    address_orga)

    def test_add_contact_vcf07(self):
        self.login()

        contact_count = Contact.objects.count()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00', email='corp@corp.com', url_site='www.corp.com')
        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays\nTEL;TYPE=WORK:11 11 11 11 11\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial

        orga_id       = form['organisation'].field.initial
        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial

        work_adr_name  = form['work_adr_name'].field.initial
        work_address   = form['work_address'].field.initial
        work_city      = form['work_city'].field.initial
        work_country   = form['work_country'].field.initial
        work_code      = form['work_code'].field.initial
        work_region    = form['work_region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':                 user,
                                            'vcf_step':             1,
                                            'first_name':           first_name,
                                            'last_name':            last_name,
                                            'create_or_attach_orga': False,
                                            'organisation':         orga_id,
                                            'relation':             REL_SUB_EMPLOYED_BY,
                                            'work_name':            work_name,
                                            'work_phone':           work_phone,
                                            'work_email':           work_email,
                                            'work_url_site':        work_url_site,
                                            'work_adr_name':        work_adr_name,
                                            'work_address':         work_address,
                                            'work_city':            work_city,
                                            'work_country':         work_country,
                                            'work_code':            work_code,
                                            'work_region':          work_region,
                                            'update_orga_name':     True,
                                            'update_orga_phone':    True,
                                            'update_orga_email':    True,
                                            'update_orga_fax':      True,
                                            'update_orga_url_site': True,
                                            'update_orga_address':  True,
                                         }
                                    )
        validation_text = _(u'Create organisation not checked')
        assertFormError = self.assertFormError
        assertFormError(response, 'form', 'update_orga_name',     validation_text)
        assertFormError(response, 'form', 'update_orga_phone',    validation_text)
        assertFormError(response, 'form', 'update_orga_email',    validation_text)
        assertFormError(response, 'form', 'update_orga_fax',      validation_text)
        assertFormError(response, 'form', 'update_orga_url_site', validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

    def test_add_contact_vcf08(self):
        self.login()

        contact_count = Contact.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays\nTEL;TYPE=WORK:11 11 11 11 11\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial

        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial

        work_adr_name  = form['work_adr_name'].field.initial
        work_address   = form['work_address'].field.initial
        work_city      = form['work_city'].field.initial
        work_country   = form['work_country'].field.initial
        work_code      = form['work_code'].field.initial
        work_region    = form['work_region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':                 user,
                                            'vcf_step':             1,
                                            'first_name':           first_name,
                                            'last_name':            last_name,
                                            'create_or_attach_orga': True,
                                            'relation':             REL_SUB_EMPLOYED_BY,
                                            'work_name':            work_name,
                                            'work_phone':           work_phone,
                                            'work_email':           work_email,
                                            'work_url_site':        work_url_site,
                                            'work_adr_name':        work_adr_name,
                                            'work_address':         work_address,
                                            'work_city':            work_city,
                                            'work_country':         work_country,
                                            'work_code':            work_code,
                                            'work_region':          work_region,
                                            'update_orga_name':     True,
                                            'update_orga_phone':    True,
                                            'update_orga_email':    True,
                                            'update_orga_fax':      True,
                                            'update_orga_url_site': True,
                                            'update_orga_address':  True,
                                         }
                                    )
        validation_text = _(u'Organisation not selected')
        assertFormError = self.assertFormError
        assertFormError(response, 'form', 'update_orga_name',     validation_text)
        assertFormError(response, 'form', 'update_orga_phone',    validation_text)
        assertFormError(response, 'form', 'update_orga_email',    validation_text)
        assertFormError(response, 'form', 'update_orga_fax',      validation_text)
        assertFormError(response, 'form', 'update_orga_url_site', validation_text)
        assertFormError(response, 'form', 'update_orga_address',  validation_text)

        self.assertEqual(contact_count, Contact.objects.count())

    def test_add_contact_vcf09(self):
        self.login()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00', email='corp@corp.com', url_site='www.corp.com')

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial

        orga_id = form['organisation'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':                 user,
                                            'vcf_step':             1,
                                            'first_name':           first_name,
                                            'last_name':            last_name,
                                            'create_or_attach_orga': True,
                                            'organisation':         orga_id,
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
        assertFormError = self.assertFormError
        assertFormError(response, 'form', 'work_phone',    validation_text)
        assertFormError(response, 'form', 'work_email',    validation_text)
        assertFormError(response, 'form', 'work_fax',      validation_text)
        assertFormError(response, 'form', 'work_url_site', validation_text)

    def test_add_contact_vcf10(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00', email='corp@corp.com', url_site='www.corp.com')
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

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays\nTEL;TYPE=WORK:11 11 11 11 11\nEMAIL;TYPE=WORK:work@work.com\nURL;TYPE=WORK:www.work.com\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial

        orga_id       = form['organisation'].field.initial
        work_name     = form['work_name'].field.initial
        work_phone    = form['work_phone'].field.initial
        work_email    = form['work_email'].field.initial
        work_url_site = form['work_url_site'].field.initial

        work_adr_name  = form['work_adr_name'].field.initial
        work_address   = form['work_address'].field.initial
        work_city      = form['work_city'].field.initial
        work_country   = form['work_country'].field.initial
        work_code      = form['work_code'].field.initial
        work_region    = form['work_region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':                 user,
                                            'vcf_step':             1,
                                            'first_name':           first_name,
                                            'last_name':            last_name,
                                            'create_or_attach_orga': True,
                                            'organisation':         orga_id,
                                            'relation':             REL_SUB_EMPLOYED_BY,
                                            'work_name':            work_name,
                                            'work_phone':           work_phone,
                                            'work_email':           work_email,
                                            'work_url_site':        work_url_site,
                                            'work_adr_name':        work_adr_name,
                                            'work_address':         work_address,
                                            'work_city':            work_city,
                                            'work_country':         work_country,
                                            'work_code':            work_code,
                                            'work_region':          work_region,
                                            'update_orga_name':     True,
                                            'update_orga_phone':    True,
                                            'update_orga_email':    True,
                                            'update_orga_url_site': True,
                                            'update_orga_address':  True,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())
        assertEqual(address_count,     Address.objects.count())

        try:
            orga = Organisation.objects.get(id=orga.id)
        except Exception, e:
            self.fail(str(e))

        billing_address = orga.billing_address

        vobj = vcf_lib.readOne(content)
        adr = vobj.adr.value
        org = vobj.org.value[0]
        assertEqual(orga.name,                  org)
        assertEqual(orga.phone,                 vobj.tel.value)
        assertEqual(orga.email,                 vobj.email.value)
        assertEqual(orga.url_site,              'http://www.work.com/')
        assertEqual(billing_address.name,       org)
        assertEqual(billing_address.address,    ' '.join([adr.box, adr.street]))
        assertEqual(billing_address.city,       adr.city)
        assertEqual(billing_address.country,    adr.country)
        assertEqual(billing_address.zipcode,    adr.code)
        assertEqual(billing_address.department, adr.region)

    def test_add_contact_vcf11(self):
        self.login()

        Organisation.objects.create(user=self.user, name='Corporate', phone='00 00 00 00 00', email='corp@corp.com', url_site='www.corp.com')

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nADR;TYPE=WORK:Orga Numéro de rue;;Orga Nom de rue;Orga Ville;Orga Région;Orga Code postal;Orga Pays\nORG:Corporate\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial

        orga_id       = form['organisation'].field.initial

        work_name     = form['work_name'].field.initial
        work_adr_name  = form['work_adr_name'].field.initial
        work_address   = form['work_address'].field.initial
        work_city      = form['work_city'].field.initial
        work_country   = form['work_country'].field.initial
        work_code      = form['work_code'].field.initial
        work_region    = form['work_region'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':                 user,
                                            'vcf_step':             1,
                                            'first_name':           first_name,
                                            'last_name':            last_name,
                                            'create_or_attach_orga': True,
                                            'organisation':         orga_id,
                                            'relation':             REL_SUB_EMPLOYED_BY,
                                            'work_name':            work_name,
                                            'work_adr_name':        work_adr_name,
                                            'work_address':         work_address,
                                            'work_city':            work_city,
                                            'work_country':         work_country,
                                            'work_code':            work_code,
                                            'work_region':          work_region,
                                            'update_orga_address':  True,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())
        assertEqual(address_count + 1, Address.objects.count())

        try:
            address = Address.objects.get(name=work_adr_name, address=work_address, city=work_city, zipcode=work_code, country=work_country, department=work_region)
            orga    = Organisation.objects.get(id=orga_id)
        except Exception, e:
            self.fail(str(e))

        vobj = vcf_lib.readOne(content)
        adr = vobj.adr.value

        assertEqual(address.name,       vobj.org.value[0])
        assertEqual(address.address,    ' '.join([adr.box, adr.street]))
        assertEqual(address.city,       adr.city)
        assertEqual(address.country,    adr.country)
        assertEqual(address.zipcode,    adr.code)
        assertEqual(address.department, adr.region)

        assertEqual(orga.billing_address.id, address.id)

    def test_add_contact_vcf12(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Image.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nTEL;TYPE=HOME:00 00 00 00 00\nTEL;TYPE=CELL:11 11 11 11 11\nTEL;TYPE=FAX:22 22 22 22 22\nEMAIL;TYPE=HOME:email@email.com\nURL;TYPE=HOME:www.url.com\nPHOTO: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\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        phone      = form['phone'].field.initial
        mobile     = form['mobile'].field.initial
        fax        = form['fax'].field.initial
        email      = form['email'].field.initial
        url_site   = form['url_site'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'phone':         phone,
                                            'mobile':        mobile,
                                            'fax':           fax,
                                            'email':         email,
                                            'url_site':      url_site,
                                            'create_or_attach_orga': False,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(image_count,       Image.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())
        assertEqual(address_count,     Address.objects.count())

        try:
            Contact.objects.get(first_name=first_name, last_name=last_name, phone=phone, mobile=mobile, fax=fax, email=email, url_site='http://www.url.com/')
            # url_site='http://www.url.com/' and not url_site=url_site because URLField add 'http://' and '/'
        except Exception, e:
            self.fail(str(e))

    def test_add_contact_vcf13(self):
        self.login()

        contact_count = Contact.objects.count()

        content  = """BEGIN:VCARD\nN;ENCODING=8BIT:HUDARD;Jean;;Monsieur;\nTITLE:PDG\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name  = form['first_name'].field.initial
        last_name   = form['last_name'].field.initial
        civility_id = form['civility'].field.initial
        position_id = form['position'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':       user,
                                            'vcf_step':   1,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                            'civility':   civility_id,
                                            'position':   position_id,
                                         }
                                    )
        self._no_from_error(response)
        self.assertEqual(contact_count + 1, Contact.objects.count())

        try:
            Contact.objects.get(civility=civility_id, first_name=first_name, last_name=last_name, position=position_id)
        except Exception, e:
            self.fail(str(e))

    def test_add_contact_vcf14(self):
        self.login()

        contact_count = Contact.objects.count()
        orga_count    = Organisation.objects.count()
        image_count   = Image.objects.count()
        address_count = Address.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nPHOTO;TYPE=JPEG:/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCABIAEgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD274v3SR6BaWpKk3FyNyHuqqxzj0DbPzFcBpfi3VdKnSC01RnO3cLe4bzVKj2PzAfQirfxYnW78ZTRhgrW1vHCD12kgvn/AMfH5V53ptpcWeoXUrzRuojQSSeUQ0n3jnO4+o/LAxXl16j9o2naxvGOiPWbf4jaodYtHuooItPACXCRrvJ6kuucEH7oxk9Cea9D0nxLo2rMq2OoQPK3SJjskP8AwBsN+lfMkd1cSzWk7SyB5SJViVsLHFjncO5PHXueOlW4dTjvbpoY4d0CoHMrdGyTjaO44PPtxVQxVSHxag4J7H1PRXH/AAqhuI/CMUtzNLJ9oleSNZHLeWg+UAZ6A7d2B/era1fXbfTrhbYI092y7/KQgbVJIDMT0GQfU8HAODXowfMk+5koOUuWOprUVzieJXA3TWJ2+kMoZvyYKP1rZ07ULXUYTLaShwp2spBVkPoynkH61TTW5U6U6fxKxaooopGZm6roWlatzqOn21w+MCR4xvH0bqPwNcH4y8A6Vp2h6hqWnTXVvJbwvIkBfzEdgOF+b5uTgfe716dXEfF2+Nr4WWBAWe5nVdq9Sq5f+aqPxrKrGLi3JXKi3fQ8s8PeCtcu/DkGqW2k2qrc7i9vDKu8bWZcnIAIOMjBPWq3hzwksnjKzs7vTTbvcTqWSW28siJBlxyOhAYZHrX0NolkNN0axsQQfs8CREjuQoBP41HrN7LbokFmqm8nDCNn+5Hjq7eoGRwOSSOgyRksJG6aG6llqUL3WbXSVTTdLtllkt0VPKQ7I4FAGFJwcHGMKAT0zgEGuK1bSZdV1Oa/urx45ZNvFugUDAA/i3HtXU6ZpiWMo2I7sAMTuwJJPLE+rM2ST/8AXrXViHbKhlwWKkDFdcKtPmUY6s0o4qFD3lG773PMbjS9VtkLWl804H8BJRvwOSCfypnhHVLyHxZZEySFpH+zTRvnLKexHsfm/A9ia7m8sHkQy2qpuGSUJwCPb0Nc/BcWmn+JtP1CaJROJPskocfMgfgN9QcfN/dZvWtm1JO2p6X1mGIoy5d7bHptFFFYHjBXmzXei6gI4tb+0nUIcGXz2cNHJwTgA/KMjoBjGO1ek1nXmh6Te3gu7zS7G4uwnliaW3R32+m4jOPasqtP2itewGTa6u4GYtVtLiP/AKeAA4/FcDH/AAH8axtd1p0sdR1cG21CbT08m1jjUxqZnxwSSepMYz2Ga6VvCuiM2RYRoP7sbMij6AEAVzN/Dp2la3faRcWcKaXqEaSbQuE5Gw59/l5PuDWFSNSEbyldCN3RoNUtbKKPX7mzur7AaR7SBooxn+EBmYnHrkZ9BT9R1fTIbyK0uLjZcybQoCMQpY4UMwGFyeBuIyeBmrCABFALMMdWYsT+J5NV2tcmdQwEU8iSyKVySy7cYPb7q/l2rnjNKbktA30ZbtowMovTaep9q43x3bxSaFJKkam8VgsZH3jk8gfgc/hXSatcNa2TzI8SuvTzDgH2rlNKaXXr6aG6kVfkaRFA4VvlAOO+OP8AJropV406ad9bkxcozUo9D0+iqul3f22ximZQkhysiA52upIYZ74IPNFdidyy1RRRQAEgDJ4Fcl4ttItZu4beIjzraF5N47FiAq/Q7W/75FberXLI8dvBEZbhwWAMhRFHqxH6DH5da5bWfM062itbW4I1G+nUPIRyc8FsdlUAcDsPqa5sRUVuRbsTOcs9Yv7FfLimOxeNjjIH51NL4i1OQf68IP8AZUCro8Kodxm1C4ZyfvRKqD64YMf1qfw7Z2tsdSS+jWaa0bPmMvDRldwIHr1B9xXHOjKCuxJ3OYvb2WYGW8nZggyWduAK3fD2lNbPp2o3GYrq4uTEiHhkh8qRiCOxYqpI/wBlehBqHw9pq3942oTxgW0chNvF2Lg/ex6KeB7gnsprptV0+We0RlYwTo4kglI+649R3BBIPsTW9Kh7rb3YrmlprNaavJA3+qux5qE9pFABH4qAQP8AZaiq2kWWr3F9a3OqGxjgt8ui27s5kcqVySQMDDH3+lFdNFSUEpFnS0UUVqBU1GxW8RSsjQzpnZKmMrnGRzwQcDg+x6gVmWuhSHU0vdQuFneNDHGiJtUAkZJ568CiipcIt81tRWNa6j2WkxgijMgQ7QVyM444rBFlBHDOEkJmm5kLnIc4xyOgHHQAe1FFc2K6AzT8PWEdjpNrGI9rLGODyV9vw6VY1G2a4jXYRuU9D3oorqS0sFtB2nxSQwbJcZzwM9BRRRTGf//Z\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        image      = form['image_encoded'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'create_or_attach_orga': False,
                                            'image_encoded': image,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(image_count + 1,   Image.objects.count())
        assertEqual(orga_count,        Organisation.objects.count())
        assertEqual(address_count,     Address.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name, last_name=last_name)
        except Exception, e:
            self.fail(str(e))

        self.assert_(contact.image)
        assertEqual(_(u'Image of %s') % contact, contact.image.name)
        contact.image.image.delete()

    def test_add_contact_vcf15(self):
        self.login()

        vcf.URL_START = vcf.URL_START + ('file',)

        os_path = os.path
        path_base = os_path.join(settings.CREME_ROOT, 'static', 'images', '500.png')
        path = 'file:///' + os_path.normpath(path_base)

        contact_count = Contact.objects.count()
        image_count   = Image.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nPHOTO;VALUE=URL:%s\nEND:VCARD""" % path
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        image      = form['image_encoded'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'image_encoded': image,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(image_count + 1,   Image.objects.count())

        try:
            contact = Contact.objects.get(first_name=first_name, last_name=last_name)
        except Exception, e:
            self.fail(str(e))

        self.assert_(contact.image)
        assertEqual(_(u'Image of %s') % contact, contact.image.name)
        contact.image.image.delete()

    def test_add_contact_vcf16(self):
        self.login()

        contact_count = Contact.objects.count()
        image_count   = Image.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nPHOTO;VALUE=URL:http://wwwwwwwww.wwwwwwwww.wwwwwwww/wwwwwww.jpg\nEND:VCARD"""
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        image      = form['image_encoded'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'image_encoded': image,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(image_count,       Image.objects.count())

    def test_add_contact_vcf17(self):
        self.login()

        settings.VCF_IMAGE_MAX_SIZE = 10240 #(10 kB)
        vcf.URL_START = vcf.URL_START + ('file',)

        os_path = os.path
        path_base = os_path.join(settings.CREME_ROOT, 'static', 'images', '500.png')
        path = 'file:///' + os_path.normpath(path_base)

        contact_count = Contact.objects.count()
        image_count   = Image.objects.count()

        content  = """BEGIN:VCARD\nFN:Jean HUDARD\nPHOTO;VALUE=URL:%s\nEND:VCARD""" % path
        filedata = self._build_filedata(content)

        url = '/vcfs/vcf'
        response = self._post_form_step_0(url, filedata.file)

        form = response.context['form']
        user       = form['user'].field.initial
        first_name = form['first_name'].field.initial
        last_name  = form['last_name'].field.initial
        image      = form['image_encoded'].field.initial

        response = self.client.post(url,
                                    follow=True,
                                    data={
                                            'user':          user,
                                            'vcf_step':      1,
                                            'first_name':    first_name,
                                            'last_name':     last_name,
                                            'image_encoded': image,
                                         }
                                    )
        self._no_from_error(response)

        assertEqual = self.assertEqual
        assertEqual(contact_count + 1, Contact.objects.count())
        assertEqual(image_count,       Image.objects.count())
