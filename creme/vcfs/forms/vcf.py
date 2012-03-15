# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

import base64
import os

from urllib import urlretrieve
from urllib2 import urlopen

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.forms import IntegerField,FileField, ModelChoiceField, CharField, EmailField, URLField, BooleanField, HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation
from creme_core.forms import CremeForm, CremeEntityForm, CremeEntityField, CremeModelWithUserForm
from creme_core.utils.secure_filename import secure_filename
from creme_core.views.file_handling import handle_uploaded_file

from media_managers.models import Image

from persons.models import Contact, Civility, Position, Organisation, Address
from persons.constants import REL_SUB_EMPLOYED_BY

from vcfs import vcf_lib

URL_START = ('http://', 'https://', 'www.')
IMG_UPLOAD_PATH = Image._meta.get_field('image').upload_to

class VcfForm(CremeForm):
    vcf_step = IntegerField(widget=HiddenInput)
    vcf_file = FileField(label=_(u'VCF file'), max_length=500)

    def clean_vcf_file(self):
        file = self.cleaned_data['vcf_file']
        try:
            vcf_data = vcf_lib.readOne(file)
        except Exception as e:
           raise ValidationError(_(u'VCF file is invalid') + ' [%s]' % str(e))

        return vcf_data

_get_ct = ContentType.objects.get_for_model

class VcfImportForm(CremeModelWithUserForm):
    class Meta:
        model = Contact
        fields = ('user',)

    vcf_step      = IntegerField(widget=HiddenInput)

    civility      = ModelChoiceField(label=_('Civility'), required=False, queryset=Civility.objects.all())
    first_name    = CharField(label=_('First name'))
    last_name     = CharField(label=_('Last name'))
    position      = ModelChoiceField(label=_('Position'), required=False, queryset=Position.objects.all())
    image_encoded = CharField(required=False, widget=HiddenInput)

    phone         = CharField(label=_('Phone number'), required=False)
    mobile        = CharField(label=_('Mobile'),       required=False)
    fax           = CharField(label=_('Fax'),          required=False)
    email         = EmailField(label=_('Email'),       required=False)
    url_site      = URLField(label=_('Web Site'),      required=False)
    adr_last_name = CharField(label=_('Name'),         required=False)
    address       = CharField(label=_('Address'),      required=False)
    city          = CharField(label=_('City'),         required=False)
    country       = CharField(label=_('Country'),      required=False)
    code          = CharField(label=_('Zip code'),     required=False)
    region        = CharField(label=_('Region'),       required=False)

    create_or_attach_orga = BooleanField(label=_('Create or attach organisation'), required=False, initial=False)
    organisation          = CremeEntityField(label=_('Organisation'), required=False, model=Organisation)

    #TODO : Composite field
    update_orga_name     = BooleanField(label=_('Update name'),     required=False, initial=False, help_text=_(u'Update organisation selected name'))
    update_orga_phone    = BooleanField(label=_('Update phone'),    required=False, initial=False, help_text=_(u'Update organisation selected phone'))
    update_orga_fax      = BooleanField(label=_('Update fax'),      required=False, initial=False, help_text=_(u'Update organisation selected fax'))
    update_orga_email    = BooleanField(label=_('Update email'),    required=False, initial=False, help_text=_(u'Update organisation selected email'))
    update_orga_url_site = BooleanField(label=_('Update web site'), required=False, initial=False, help_text=_(u'Update organisation selected web site'))
    update_orga_address  = BooleanField(label=_('Update address'),  required=False, initial=False, help_text=_(u'Update organisation selected address'))

    relation      = ModelChoiceField(label=_('Position in the organisation'),
                                     #queryset=RelationType.objects.filter(subject_ctypes=_get_ct(Contact), object_ctypes=_get_ct(Organisation)),
                                     queryset=RelationType.objects.none(),
                                     initial=REL_SUB_EMPLOYED_BY, required=False
                                    )
    work_name     = CharField(label=_('Name'),         required=False)
    work_phone    = CharField(label=_('Phone number'), required=False)
    work_fax      = CharField(label=_('Fax'),          required=False)
    work_email    = EmailField(label=_('Email'),       required=False)
    work_url_site = URLField(label=_('Web Site'),      required=False)
    work_adr_name = CharField(label=_('Name'),         required=False)
    work_address  = CharField(label=_('Address'),      required=False)
    work_city     = CharField(label=_('City'),         required=False)
    work_country  = CharField(label=_('Country'),      required=False)
    work_code     = CharField(label=_('Zip code'),     required=False)
    work_region   = CharField(label=_('Region'),       required=False)

    blocks = CremeEntityForm.blocks.new(
        ('coordinates',                  _(u'Coordinates'),                  ['phone', 'mobile', 'fax', 'email', 'url_site']),
        ('contact_billing_address',      _(u'Billing address'),              ['adr_last_name', 'address', 'city', 'country', 'code', 'region']),
        ('organisation',                 _(u'Organisation'),                 ['create_or_attach_orga', 'organisation', 'relation', 'update_orga_name', 'work_name', 'update_orga_phone', 'work_phone', 'update_orga_fax', 'work_fax', 'update_orga_email', 'work_email', 'update_orga_url_site', 'work_url_site']),
        ('organisation_billing_address', _(u'Organisation billing address'), ['update_orga_address', 'work_adr_name', 'work_address', 'work_city', 'work_country', 'work_code', 'work_region']),
    )

    tel_dict = {'HOME': 'phone',
                'CELL': 'mobile',
                'FAX':  'fax',
               }

    email_dict = {'HOME':     'email',
                  'INTERNET': 'email',
                 }

    url_dict = {'HOME':     'url_site',
                'INTERNET': 'url_site',
               }

    adr_dict = {'HOME': '',
               }

    type_help_text  = _(u'Read in VCF File without type : ')
    other_help_text = _(u'Read in VCF File : ')

    def __init__(self, vcf_data=None, *args, **kwargs):
        super(VcfImportForm, self).__init__(*args, **kwargs)
        fields = self.fields

        if vcf_data:
            other_help_text = self.other_help_text

            tel_dict   = dict(self.tel_dict)
            email_dict = dict(self.email_dict)
            url_dict   = dict(self.url_dict)
            adr_dict   = dict(self.adr_dict)

            contents = vcf_data.contents

            contact_data = contents.get('n')
            if contact_data:
                value = vcf_data.n.value
                last_name = value.family
                fields['first_name'].initial    = value.given
                fields['last_name'].initial     = last_name
                fields['adr_last_name'].initial = last_name
                prefix = value.prefix
                if prefix:
                    civil = Civility.objects.filter(title__icontains=prefix)[:1]
                    if civil:
                        fields['civility'].initial = civil[0].id
                    else:
                        fields['civility'].help_text = other_help_text + prefix
            else:
                first_name, sep, last_name = vcf_data.fn.value.partition(' ')
                fields['first_name'].initial    = first_name
                fields['last_name'].initial     = last_name
                fields['adr_last_name'].initial = last_name

            if contents.get('org'):
                org_name = vcf_data.org.value[0]

                orga = Organisation.objects.filter(name=org_name)[:1]
                if orga:
                    fields['organisation'].initial = orga[0].id
                    fields['create_or_attach_orga'].initial  = True

                fields['work_name'].initial     = org_name
                fields['work_adr_name'].initial = org_name

                tel_dict['WORK']   = 'work_phone'
                email_dict['WORK'] = 'work_email'
                url_dict['WORK']   = 'work_url_site'
                adr_dict['WORK']   = 'work_'

            if contents.get('title'):
                title = vcf_data.title.value
                position = Position.objects.filter(title__icontains=title)[:1]
                if position:
                    fields['position'].initial = position[0].id
                else:
                    fields['position'].help_text = other_help_text + title

            if contents.get('photo'):
                fields['image_encoded'].initial = vcf_data.photo.value.replace('\n', '')

            manage_coordinates = self._manage_coordinates
            manage_coordinates(vcf_data, fields, 'tel',   tel_dict)
            manage_coordinates(vcf_data, fields, 'email', email_dict)
            manage_coordinates(vcf_data, fields, 'url',   url_dict)

            for adr in contents.get('adr', ()):
                param = adr.params.get('TYPE')
                value = adr.value
                if param:
                    param = param[0]
                    if value.box:
                        fields[adr_dict[param] + 'address'].initial = value.box + ' ' + value.street
                    else:
                        fields[adr_dict[param] + 'address'].initial = value.street
                    fields[adr_dict[param] + 'city'].initial    = value.city
                    fields[adr_dict[param] + 'country'].initial = value.country
                    fields[adr_dict[param] + 'code'].initial    = value.code
                    fields[adr_dict[param] + 'region'].initial  = value.region
                else:
                    value = ', '.join([value.box, value.street, value.city, value.region, value.code, value.country])
                    self._generate_help_text(fields, 'address', value)

        #Beware: this queryset diretcly in the field declaration does not work on some systems in unit tests...
        #        (it seems that the problem it caused by the M2M - other fields work, but why ???)
        fields['relation'].queryset = RelationType.objects.filter(subject_ctypes=_get_ct(Contact), object_ctypes=_get_ct(Organisation))

    def _generate_help_text(self, fields, field_name, value):
        field = fields[field_name]

        if not field.help_text:
            field.help_text = self.type_help_text + value
        else:
            field.help_text = '%s | %s' % (field.help_text, value)

    def _manage_coordinates(self, vcf_data, fields, key, field_dict):
        """
        @param vcf_data (vcf_lib.base.Component) : data read in VCF file
        @param fields : fields of form
        @param key : key in dict vcf_data.contents
        @param field_dict : dict used for field (tel_dict for field 'tel')
        """
        data = vcf_data.contents.get(key)
        if data:
            for key in data:
                param = key.params.get('TYPE')
                if param:
                    fields[field_dict[param[0]]].initial = key.value
                else:
                    self._generate_help_text(fields, field_dict['HOME'], key.value)

    def _clean_orga_field(self, field_name):
        cleaned_data = self.cleaned_data
        cleaned = cleaned_data.get(field_name)

        if cleaned_data['create_or_attach_orga'] and not cleaned:
            raise ValidationError(ugettext(u'Required, if you want to create organisation'))

        return cleaned

    clean_work_name = lambda self: self._clean_orga_field('work_name')
    clean_relation  = lambda self: self._clean_orga_field('relation')

    def _clean_update_checkbox(self, checkbox_name):
        cleaned_data = self.cleaned_data
        checked = cleaned_data[checkbox_name]

        if checked:
            if not cleaned_data['create_or_attach_orga']:
                raise ValidationError(ugettext(u'Create organisation not checked'))
            elif not cleaned_data['organisation']:
                raise ValidationError(ugettext(u'Organisation not selected'))

        return checked

    clean_update_orga_name     = lambda self: self._clean_update_checkbox('update_orga_name')
    clean_update_orga_phone    = lambda self: self._clean_update_checkbox('update_orga_phone')
    clean_update_orga_email    = lambda self: self._clean_update_checkbox('update_orga_email')
    clean_update_orga_fax      = lambda self: self._clean_update_checkbox('update_orga_fax')
    clean_update_orga_url_site = lambda self: self._clean_update_checkbox('update_orga_url_site')
    clean_update_orga_address  = lambda self: self._clean_update_checkbox('update_orga_address')

    def clean_update_field(self, checkbox_name, field_name):
        cleaned_data = self.cleaned_data
        cleaned_data_field_name = cleaned_data[field_name]

        if not cleaned_data_field_name and all(cleaned_data[k] for k in ('create_or_attach_orga', 'organisation', checkbox_name)):
            raise ValidationError(ugettext(u'Required, if you want to update organisation'))

        return cleaned_data_field_name

    clean_work_phone    = lambda self: self.clean_update_field('update_orga_phone', 'work_phone')
    clean_work_email    = lambda self: self.clean_update_field('update_orga_email', 'work_email')
    clean_work_fax      = lambda self: self.clean_update_field('update_orga_fax', 'work_fax')
    clean_work_url_site = lambda self: self.clean_update_field('update_orga_url_site', 'work_url_site')
    clean_work_address  = lambda self: self.clean_update_field('update_orga_address', 'work_address')

    def save(self, *args, **kwargs):
        cleaned_data = self.cleaned_data
        user         = cleaned_data['user']
        save_contact = False
        save_org     = False

        contact = Contact.objects.create(user=user,
                                         civility=cleaned_data['civility'],
                                         first_name=cleaned_data['first_name'],
                                         last_name=cleaned_data['last_name'],
                                         phone=cleaned_data['phone'],
                                         mobile=cleaned_data['mobile'],
                                         fax=cleaned_data['fax'],
                                         position=cleaned_data['position'],
                                         email=cleaned_data['email'],
                                         url_site=cleaned_data['url_site'],
                                        )

        image_encoded = cleaned_data['image_encoded']
        if image_encoded:
            img_name = secure_filename('_'.join([contact.last_name, contact.first_name, str(contact.id)]))
            img_path = ''

            if image_encoded.startswith(URL_START):
                try:
                    if int(urlopen(image_encoded).info()['content-length']) <= settings.VCF_IMAGE_MAX_SIZE:
                        os_path = os.path
                        img_name = ''.join([img_name, os_path.splitext(image_encoded)[1]])

                        img_path = os_path.join(IMG_UPLOAD_PATH, img_name)
                        img_path = os_path.normpath(img_path)

                        path = os_path.join(settings.MEDIA_ROOT, img_path)
                        path = os_path.normpath(path)

                        urlretrieve(image_encoded, path)
                except:
                    img_path = ''
            else: #TODO: manage urls encoded in base64 ??
                try:
                    #TODO: factorise with activesync ??
                    image_format = Image.get_image_format(image_encoded)
                    img_path     = handle_uploaded_file(ContentFile(base64.decodestring(image_encoded)), path=[IMG_UPLOAD_PATH], name='.'.join([img_name, image_format]))
                except:
                    img_path = ''

            if img_path:
                contact.image = Image.objects.create(user=user,
                                                     name=ugettext(u'Image of %s') % contact,
                                                     image=img_path,
                                                    )
                save_contact = True

        if any(cleaned_data[k] for k in ('adr_last_name', 'address', 'city', 'country', 'code', 'region')):
            contact.billing_address = Address.objects.create(name=cleaned_data['adr_last_name'],
                                                             address=cleaned_data['address'],
                                                             city=cleaned_data['city'],
                                                             country=cleaned_data['country'],
                                                             zipcode=cleaned_data['code'],
                                                             department=cleaned_data['region'],
                                                             content_type_id=ContentType.objects.get_for_model(Contact).id,
                                                             object_id=contact.id,
                                                            )
            save_contact = True

        if cleaned_data['create_or_attach_orga']:
            organisation = cleaned_data.get('organisation')
            if organisation:
                update_coordinates_dict = {'update_orga_phone':    'phone',
                                           'update_orga_email':    'email',
                                           'update_orga_fax':      'fax',
                                           'update_orga_url_site': 'url_site',
                                           }

                for key, value in update_coordinates_dict.iteritems():
                    if cleaned_data[key]:
                         setattr(organisation, value, cleaned_data['work_' + value])

                if cleaned_data['update_orga_address']:
                    billing_address = organisation.billing_address

                    if billing_address:
                        update_address_dict = {'work_adr_name': 'name',
                                               'work_address':  'address',
                                               'work_city':     'city',
                                               'work_country':  'country',
                                               'work_code':     'zipcode',
                                               'work_region':   'department',
                                               }

                        for key, value in update_address_dict.iteritems():
                            if cleaned_data[key]:
                                setattr(billing_address, value, cleaned_data[key])

                        organisation.billing_address.save()
                    else:
                        organisation.billing_address = Address.objects.create(name=cleaned_data['work_adr_name'],
                                                                              address=cleaned_data['work_address'],
                                                                              city=cleaned_data['work_city'],
                                                                              country=cleaned_data['work_country'],
                                                                              zipcode=cleaned_data['work_code'],
                                                                              department=cleaned_data['work_region'],
                                                                              content_type_id=ContentType.objects.get_for_model(Organisation).id,
                                                                              object_id=organisation.id,
                                                                             )
                save_org = True
            else:
                organisation = Organisation.objects.create(user=user,
                                                           name=cleaned_data['work_name'],
                                                           phone=cleaned_data['work_phone'],
                                                           email=cleaned_data['work_email'],
                                                           url_site=cleaned_data['work_url_site'],
                                                          )

                if any(cleaned_data[k] for k in ('work_adr_name', 'work_address', 'work_city', 'work_country', 'work_code', 'work_region')):
                    organisation.billing_address = Address.objects.create(name=cleaned_data['work_adr_name'],
                                                                          address=cleaned_data['work_address'],
                                                                          city=cleaned_data['work_city'],
                                                                          country=cleaned_data['work_country'],
                                                                          zipcode=cleaned_data['work_code'],
                                                                          department=cleaned_data['work_region'],
                                                                          content_type_id=ContentType.objects.get_for_model(Organisation).id,
                                                                          object_id=organisation.id,
                                                                         )
                    save_org = True

            if save_org:
                organisation.save()

            Relation.objects.create(user=user,
                                    subject_entity=contact,
                                    type=cleaned_data['relation'],
                                    object_entity=organisation
                                   )

        if save_contact:
            contact.save()

        return contact
