# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
import logging
from itertools import chain
from os import path
from urllib.request import urlopen, urlretrieve

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from django.forms import (
    BooleanField,
    CharField,
    EmailField,
    FileField,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    URLField,
)
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import documents, persons
from creme.creme_core.forms import (
    CreatorEntityField,
    CremeForm,
    CremeModelForm,
)
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import FieldsConfig, Relation, RelationType
from creme.creme_core.utils.secure_filename import secure_filename
from creme.creme_core.views.file_handling import handle_uploaded_file
from creme.documents.constants import UUID_FOLDER_IMAGES
from creme.documents.utils import get_image_format
from creme.persons.constants import REL_SUB_EMPLOYED_BY
from creme.persons.models import Civility, Position

from ..vcf_lib import readOne as read_vcf

logger = logging.getLogger(__name__)

Document = documents.get_document_model()
Folder = documents.get_folder_model()

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Address = persons.get_address_model()

URL_START = ('http://', 'https://', 'www.')
IMG_UPLOAD_PATH = Document._meta.get_field('filedata').upload_to

HOME_ADDR_PREFIX = 'homeaddr_'
WORK_ADDR_PREFIX = 'workaddr_'


class VcfForm(CremeForm):
    vcf_step = IntegerField(widget=HiddenInput)
    vcf_file = FileField(label=_('VCF file'), max_length=500)

    error_messages = {
        'invalid_file': _('VCF file is invalid [%(error)s]'),
    }

    def clean_vcf_file(self):
        file_obj = self.cleaned_data['vcf_file']
        try:
            vcf_data = read_vcf(file_obj)
        except Exception as e:
            logger.exception('VcfForm -> error when reading file')
            raise ValidationError(self.error_messages['invalid_file'],
                                  params={'error': e}, code='invalid_file',
                                 ) from e

        return vcf_data


_get_ct = ContentType.objects.get_for_model


class VcfImportForm(CremeModelForm):
    class Meta:
        model = Contact
        fields = ('user', 'civility', 'first_name', 'last_name', 'position')

    vcf_step = IntegerField(widget=HiddenInput)

    image_encoded = CharField(required=False, widget=HiddenInput)

    # Details
    phone    = CharField(label=_('Phone number'),   required=False)
    mobile   = CharField(label=_('Mobile'),         required=False)
    fax      = CharField(label=_('Fax'),            required=False)
    email    = EmailField(label=_('Email address'), required=False)
    url_site = URLField(label=_('Web Site'),        required=False)

    # Address
    homeaddr_name     = CharField(label=_('Name'),     required=False)
    homeaddr_address  = CharField(label=_('Address'),  required=False)
    homeaddr_city     = CharField(label=_('City'),     required=False)
    homeaddr_country  = CharField(label=_('Country'),  required=False)
    homeaddr_code     = CharField(label=_('Zip code'), required=False)
    homeaddr_region   = CharField(label=_('Region'),   required=False)

    # Related Organisation
    create_or_attach_orga = BooleanField(label=_('Create or attach organisation'),
                                         required=False, initial=False,
                                        )
    organisation = CreatorEntityField(label=_('Organisation'), required=False, model=Organisation)
    relation = ModelChoiceField(label=_('Position in the organisation'),
                                queryset=RelationType.objects.none(),
                                initial=REL_SUB_EMPLOYED_BY, required=False,
                                empty_label='',
                                widget=DynamicSelect(attrs={'autocomplete': True}),
                               )

    # TODO: Composite field
    update_work_name     = BooleanField(label=_('Update name'),     required=False, initial=False, help_text=_('Update organisation selected name'))
    update_work_phone    = BooleanField(label=_('Update phone'),    required=False, initial=False, help_text=_('Update organisation selected phone'))
    update_work_fax      = BooleanField(label=_('Update fax'),      required=False, initial=False, help_text=_('Update organisation selected fax'))
    update_work_email    = BooleanField(label=_('Update email'),    required=False, initial=False, help_text=_('Update organisation selected email'))
    update_work_url_site = BooleanField(label=_('Update web site'), required=False, initial=False, help_text=_('Update organisation selected web site'))
    update_work_address  = BooleanField(label=_('Update address'),  required=False, initial=False, help_text=_('Update organisation selected address'))

    # Organisation name & details
    work_name     = CharField(label=_('Name'),           required=False)
    work_phone    = CharField(label=_('Phone number'),   required=False)
    work_fax      = CharField(label=_('Fax'),            required=False)
    work_email    = EmailField(label=_('Email address'), required=False)
    work_url_site = URLField(label=_('Web Site'),        required=False)

    # Organisation address
    workaddr_name    = CharField(label=_('Name'),     required=False)
    workaddr_address = CharField(label=_('Address'),  required=False)
    workaddr_city    = CharField(label=_('City'),     required=False)
    workaddr_country = CharField(label=_('Country'),  required=False)
    workaddr_code    = CharField(label=_('Zip code'), required=False)
    workaddr_region  = CharField(label=_('Region'),   required=False)

    error_messages = {
        'required4orga': _('Required, if you want to create organisation'),
        'no_orga_creation': _('Create organisation not checked'),
        'orga_not_selected': _('Organisation not selected'),
        'required2update': _('Required, if you want to update organisation'),
    }

    # Names of the fields corresponding to the Contact's details.
    contact_details = ['phone', 'mobile', 'fax', 'email', 'url_site']

    # Names of the fields corresponding to the related Organisation (but not its Address).
    orga_fields = ['name', 'phone', 'email', 'fax', 'url_site']

    # Correspondence between VCF field types & form-field names.
    phone_dict = {'HOME': 'phone',
                  'CELL': 'mobile',
                  'FAX':  'fax',
                  'WORK': 'work_phone',
                 }
    email_dict = {'HOME':     'email',
                  'INTERNET': 'email',
                  'WORK':     'work_email',
                 }
    url_dict = {'HOME':     'url_site',
                'INTERNET': 'url_site',
                'WORK':     'work_url_site',
               }

    # Form-field names prefix for address + correspondence with VCF field types.
    address_prefixes = {'HOME': HOME_ADDR_PREFIX,
                        'WORK': WORK_ADDR_PREFIX,
                       }
    # Mapping between form fields names (which use vcf lib names) & Address fields names.
    address_mapping = [('name',     'name'),
                       ('address',  'address'),
                       ('city',     'city'),
                       ('country',  'country'),
                       ('code',     'zipcode'),
                       ('region',   'department'),
                      ]

    # blocks = CremeModelWithUserForm.blocks.new(
    blocks = CremeModelForm.blocks.new(
        ('details', _('Details'), contact_details),
        ('contact_address', _('Billing address'),
         [HOME_ADDR_PREFIX + n[0] for n in address_mapping]
        ),
        ('organisation', _('Organisation'),
         ['create_or_attach_orga', 'organisation', 'relation',
          *chain.from_iterable(('update_work_' + fn, 'work_' + fn) for fn in orga_fields)
         ]
        ),
        ('organisation_address', _('Organisation billing address'),
         ['update_work_address', *(WORK_ADDR_PREFIX + n[0] for n in address_mapping)]
        ),
    )

    type_help_text  = _('Read in VCF File without type : ')
    other_help_text = _('Read in VCF File : ')

    def __init__(self, vcf_data=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        if vcf_data:
            self._init_contact_fields(vcf_data)
            self._init_orga_field(vcf_data)
            self._init_addresses_fields(vcf_data)

            if vcf_data.contents.get('photo'):
                fields['image_encoded'].initial = vcf_data.photo.value.replace('\n', '')

        # Beware: this queryset directly in the field declaration does not work on some systems in unit tests...
        #         (it seems that the problem it caused by the M2M - other fields work, but why ???)
        fields['relation'].queryset = RelationType.objects.filter(
            subject_ctypes=_get_ct(Contact),
            # object_ctypes=_get_ct(Organisation),
            symmetric_type__subject_ctypes=_get_ct(Organisation),
        )

        self._hide_fields()

    def _hide_fields(self):
        fields = self.fields
        address_mapping = self.address_mapping
        fconfigs = FieldsConfig.objects.get_for_models((Contact, Organisation, Address))

        # TODO: use shipping address if not hidden ?
        if fconfigs[Contact].is_fieldname_hidden('billing_address'):
            prefix = HOME_ADDR_PREFIX

            for form_fname, __ in address_mapping:
                del fields[prefix + form_fname]

        is_orga_field_hidden = fconfigs[Organisation].is_fieldname_hidden
        for fname in [*fields]:  # NB: Cannot mutate the OrderedDict during iteration.
            # NB: 5 == len('work_')
            if fname.startswith('work_') and is_orga_field_hidden(fname[5:]):
                del fields[fname]
                del fields['update_' + fname]

        if is_orga_field_hidden('billing_address'):
            prefix = WORK_ADDR_PREFIX

            for form_fname, __ in address_mapping:
                del fields[prefix + form_fname]

            del fields['update_work_address']

        is_addr_field_hidden = fconfigs[Address].is_fieldname_hidden
        addr_prefixes = self.address_prefixes.values()
        for form_fname, model_fname in address_mapping:
            if is_addr_field_hidden(model_fname):
                for prefix in addr_prefixes:
                    fields.pop(prefix + form_fname, None)

    def _init_contact_fields(self, vcf_data):
        contents = vcf_data.contents
        fields = self.fields
        contact_data = contents.get('n')

        if contact_data:
            value = vcf_data.n.value
            last_name = value.family
            fields['first_name'].initial = value.given
            fields['last_name'].initial  = last_name
            fields['homeaddr_name'].initial = last_name
            prefix = value.prefix

            if prefix:
                # TODO: find in title too ?
                civ = Civility.objects.filter(shortcut__icontains=prefix).first()
                if civ:
                    fields['civility'].initial = civ.id
                else:
                    fields['civility'].help_text = self.other_help_text + prefix
        else:
            first_name, sep, last_name = vcf_data.fn.value.partition(' ')
            fields['first_name'].initial = first_name
            fields['last_name'].initial  = last_name
            fields['homeaddr_name'].initial = last_name

        if contents.get('title'):
            title = vcf_data.title.value
            position = Position.objects.filter(title__icontains=title).first()

            if position:
                fields['position'].initial = position.id
            else:
                fields['position'].help_text = self.other_help_text + title

        init_detail = self._init_detail_field
        init_detail(contents.get('tel'),   self.phone_dict)
        init_detail(contents.get('email'), self.email_dict)
        init_detail(contents.get('url'),   self.url_dict)

    def _init_detail_field(self, detail_data, field_dict):
        if detail_data:
            fields = self.fields

            for key in detail_data:
                param = key.params.get('TYPE')

                if param:
                    try:
                        fields[field_dict[param[0]]].initial = key.value
                    except KeyError:  # eg: invalid type, hidden field
                        pass
                else:
                    self._generate_help_text(field_dict['HOME'], key.value)

    def _init_orga_field(self, vcf_data):
        if vcf_data.contents.get('org'):
            fields = self.fields

            org_name = vcf_data.org.value[0]
            orga = Organisation.objects.filter(name=org_name).first()

            if orga:
                fields['organisation'].initial = orga.id
                fields['create_or_attach_orga'].initial = True

            fields['work_name'].initial = org_name
            fields['workaddr_name'].initial = org_name

    def _init_addresses_fields(self, vcf_data):
        fields = self.fields
        get_prefix = self.address_prefixes.get

        for adr in vcf_data.contents.get('adr', ()):
            param = adr.params.get('TYPE')
            value = adr.value

            if param:
                prefix = get_prefix(param[0])

                if prefix is None:
                    continue

                box = value.box
                fields[prefix + 'address'].initial = (box + ' ' + value.street) if box else value.street
                fields[prefix + 'city'].initial    = value.city
                fields[prefix + 'country'].initial = value.country
                fields[prefix + 'code'].initial    = value.code
                fields[prefix + 'region'].initial  = value.region
            else:
                self._generate_help_text('homeaddr_address',
                                         ', '.join([value.box, value.street, value.city,
                                                    value.region, value.code, value.country,
                                                   ]
                                                  ),
                                        )

    def _generate_help_text(self, field_name, value):
        field = self.fields[field_name]
        help_text = field.help_text

        if not help_text:
            field.help_text = self.type_help_text + value
        else:
            field.help_text = f'{help_text} | {value}'

    def _clean_orga_field(self, field_name):
        cleaned_data = self.cleaned_data
        cleaned = cleaned_data.get(field_name)

        if cleaned_data['create_or_attach_orga'] and not cleaned:
            raise ValidationError(self.error_messages['required4orga'],
                                  code='required4orga',
                                 )

        return cleaned

    def clean_work_name(self):
        return self._clean_orga_field('work_name')

    def clean_relation(self):
        return self._clean_orga_field('relation')

    def _clean_update_checkbox(self, checkbox_name):
        cleaned_data = self.cleaned_data
        checked = cleaned_data[checkbox_name]

        if checked:
            if not cleaned_data['create_or_attach_orga']:
                raise ValidationError(self.error_messages['no_orga_creation'],
                                      code='no_orga_creation',
                                     )
            elif not cleaned_data['organisation']:
                raise ValidationError(self.error_messages['orga_not_selected'],
                                      code='orga_not_selected',
                                     )

        return checked

    def clean_update_work_name(self):
        return self._clean_update_checkbox('update_work_name')

    def clean_update_work_phone(self):
        return self._clean_update_checkbox('update_work_phone')

    def clean_update_work_email(self):
        return self._clean_update_checkbox('update_work_email')

    def clean_update_work_fax(self):
        return self._clean_update_checkbox('update_work_fax')

    def clean_update_work_url_site(self):
        return self._clean_update_checkbox('update_work_url_site')

    def clean_update_work_address(self):
        return self._clean_update_checkbox('update_work_address')

    def clean_update_field(self, field_name):
        cleaned_data = self.cleaned_data
        value = cleaned_data[field_name]

        if not value and \
           all(cleaned_data[k] for k in ('create_or_attach_orga', 'organisation', 'update_' + field_name)):
            raise ValidationError(self.error_messages['required2update'], code='required2update')

        return value

    def clean_work_phone(self):
        return self.clean_update_field('work_phone')

    def clean_work_email(self):
        return self.clean_update_field('work_email')

    def clean_work_fax(self):
        return self.clean_update_field('work_fax')

    def clean_work_url_site(self):
        return self.clean_update_field('work_url_site')

    def clean_work_address(self):
        return self.clean_update_field('work_address')

    def _create_contact(self, cleaned_data):
        get_data = cleaned_data.get

        return Contact.objects.create(user=cleaned_data['user'],
                                      civility=cleaned_data['civility'],
                                      first_name=cleaned_data['first_name'],
                                      last_name=cleaned_data['last_name'],
                                      position=get_data('position'),
                                      # NB: we do not use cleaned_data.get() in order to not overload
                                      #     default fields values
                                      **{fname: cleaned_data[fname]
                                            for fname in self.contact_details
                                                if fname in cleaned_data
                                        }
                                     )

    def _create_address(self, cleaned_data, owner, data_prefix):
        # NB: we do not use cleaned_data.get() in order to not overload default fields values
        kwargs = {}
        for form_fname, model_fname in self.address_mapping:
            try:
                kwargs[model_fname] = cleaned_data[data_prefix + form_fname]
            except KeyError:
                pass

        address = Address(owner=owner, **kwargs)

        if address:
            address.save()
            return address

    def _create_image(self, contact):
        cleaned_data = self.cleaned_data
        image_encoded = cleaned_data['image_encoded']

        if image_encoded:
            img_name = secure_filename(f'{contact.last_name}_{contact.first_name}_{contact.id}')
            img_path = None

            if image_encoded.startswith(URL_START):
                tmp_img_path = None

                try:
                    if int(urlopen(image_encoded).info()['content-length']) <= settings.VCF_IMAGE_MAX_SIZE:
                        tmp_img_path = path.normpath(path.join(IMG_UPLOAD_PATH, img_name))

                        urlretrieve(image_encoded, path.normpath(path.join(settings.MEDIA_ROOT, tmp_img_path)))
                except:
                    logger.exception('Error with image')
                else:
                    img_path = tmp_img_path
            else:  # TODO: manage urls encoded in base64 ??
                try:
                    img_data = base64.decodebytes(image_encoded.encode())
                    img_path = handle_uploaded_file(
                        ContentFile(img_data),
                        path=IMG_UPLOAD_PATH.split('/'),
                        name=f'{img_name}.{get_image_format(img_data)}',
                    )
                except Exception:
                    logger.exception('VcfImportForm.save()')

            if img_path:
                return Document.objects.create(
                    user=cleaned_data['user'],
                    title=gettext('Image of {contact}').format(contact=contact),
                    filedata=img_path,
                    linked_folder=Folder.objects.get(uuid=UUID_FOLDER_IMAGES),
                    description=gettext('Imported by VCFs'),
                )

    def _create_orga(self, contact):
        cleaned_data = self.cleaned_data

        if cleaned_data['create_or_attach_orga']:
            get_data = cleaned_data.get
            organisation = get_data('organisation')
            save_orga    = False
            user         = cleaned_data['user']
            addr_prefix  = WORK_ADDR_PREFIX

            if organisation:
                # TODO: select_for_update() option in CreatorEntityField ?
                organisation = Organisation.objects.select_for_update().get(id=organisation.id)

                for fname in self.orga_fields:
                    if get_data('update_work_' + fname):
                        setattr(organisation, fname, get_data('work_' + fname))

                if get_data('update_work_address'):
                    billing_address = organisation.billing_address

                    if billing_address is not None:
                        for form_fname, model_fname in self.address_mapping:
                            value = get_data(addr_prefix + form_fname)

                            if value:
                                setattr(billing_address, model_fname, value)

                        organisation.billing_address.save()
                    else:
                        organisation.billing_address = self._create_address(
                            cleaned_data, owner=organisation, data_prefix=addr_prefix,
                        )

                save_orga = True
            else:
                # NB: we do not use cleaned_data.get() in order to not overload default fields values
                orga_kwargs = {}
                for fname in self.orga_fields:
                    try:
                        orga_kwargs[fname] = cleaned_data['work_' + fname]
                    except KeyError:
                        pass

                organisation = Organisation.objects.create(user=user, **orga_kwargs)

                orga_addr = self._create_address(cleaned_data, owner=organisation,
                                                 data_prefix=addr_prefix,
                                                )
                if orga_addr is not None:
                    organisation.billing_address = orga_addr
                    save_orga = True

            if save_orga:
                organisation.save()

            Relation.objects.create(user=user,
                                    subject_entity=contact,
                                    type=cleaned_data['relation'],
                                    object_entity=organisation,
                                   )

    @atomic
    def save(self, *args, **kwargs):
        cleaned_data = self.cleaned_data
        save_contact = False
        contact = self._create_contact(cleaned_data)

        image = self._create_image(contact)
        if image is not None:
            contact.image = image
            save_contact = True

        contact_addr = self._create_address(cleaned_data, owner=contact,
                                            data_prefix=HOME_ADDR_PREFIX,
                                           )
        if contact_addr is not None:
            contact.billing_address = contact_addr
            save_contact = True

        self._create_orga(contact)

        if save_contact:
            contact.save()

        return contact
