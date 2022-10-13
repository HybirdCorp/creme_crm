# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
# from os import path
# from urllib.request import urlopen, urlretrieve
from typing import Optional, Tuple
from urllib.error import URLError
from urllib.request import urlopen

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
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    CreatorEntityField,
    CremeForm,
    CremeModelForm,
    FieldBlockManager,
)
from creme.creme_core.forms.base import _CUSTOM_NAME
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.models import (
    CustomField,
    CustomFieldValue,
    FieldsConfig,
    Relation,
    RelationType,
)
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.utils import split_filter
# from creme.creme_core.utils.secure_filename import secure_filename
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
# IMG_UPLOAD_PATH = Document._meta.get_field('filedata').upload_to

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
            raise ValidationError(
                self.error_messages['invalid_file'],
                params={'error': e}, code='invalid_file',
            ) from e

        return vcf_data


_get_ct = ContentType.objects.get_for_model


class VcfImportForm(CremeModelForm):
    # class Meta:
    class Meta(CremeModelForm.Meta):
        model = Contact
        # fields = ('user', 'civility', 'first_name', 'last_name', 'position')

    vcf_step = IntegerField(widget=HiddenInput)

    # NB: label because there can be validation error on it
    image_encoded = CharField(
        label=_('Embedded image'), required=False, widget=HiddenInput,
    )

    # # Details
    # phone    = CharField(label=_('Phone number'),   required=False)
    # mobile   = CharField(label=_('Mobile'),         required=False)
    # fax      = CharField(label=_('Fax'),            required=False)
    # email    = EmailField(label=_('Email address'), required=False)
    # url_site = URLField(label=_('Web Site'),        required=False)

    # Address
    homeaddr_name     = CharField(label=_('Name'),     required=False)
    homeaddr_address  = CharField(label=_('Address'),  required=False)
    homeaddr_city     = CharField(label=_('City'),     required=False)
    homeaddr_country  = CharField(label=_('Country'),  required=False)
    homeaddr_code     = CharField(label=_('Zip code'), required=False)
    homeaddr_region   = CharField(label=_('Region'),   required=False)

    # Related Organisation
    create_or_attach_orga = BooleanField(
        label=_('Create or attach organisation'), required=False, initial=False,
    )
    organisation = CreatorEntityField(
        label=_('Organisation'), required=False, model=Organisation,
    )
    relation = ModelChoiceField(
        label=_('Position in the organisation'),
        queryset=RelationType.objects.none(),
        initial=REL_SUB_EMPLOYED_BY, required=False,
        empty_label='',
        widget=DynamicSelect(attrs={'autocomplete': True}),
    )

    # TODO: Composite field
    update_work_name = BooleanField(
        label=_('Update name'), required=False, initial=False,
        help_text=_('Update organisation selected name'),
    )
    update_work_phone = BooleanField(
        label=_('Update phone'), required=False, initial=False,
        help_text=_('Update organisation selected phone'),
    )
    update_work_fax = BooleanField(
        label=_('Update fax'), required=False, initial=False,
        help_text=_('Update organisation selected fax'),
    )
    update_work_email = BooleanField(
        label=_('Update email'), required=False, initial=False,
        help_text=_('Update organisation selected email'),
    )
    update_work_url_site = BooleanField(
        label=_('Update web site'), required=False, initial=False,
        help_text=_('Update organisation selected web site'),
    )
    update_work_address = BooleanField(
        label=_('Update address'), required=False, initial=False,
        help_text=_('Update organisation selected address'),
    )

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
    # contact_details = ['phone', 'mobile', 'fax', 'email', 'url_site']
    contact_details = ['phone', 'mobile', 'fax', 'email', 'url_site', 'skype']

    # Names of the fields corresponding to the related Organisation (but not its Address).
    orga_fields = ['name', 'phone', 'email', 'fax', 'url_site']

    # Correspondence between VCF field types & form-field names.
    phone_dict = {
        'HOME': 'phone',
        'CELL': 'mobile',
        'FAX':  'fax',
        'WORK': 'work_phone',
    }
    email_dict = {
        'HOME':     'email',
        'INTERNET': 'email',
        'WORK':     'work_email',
    }
    url_dict = {
        'HOME':     'url_site',
        'INTERNET': 'url_site',
        'WORK':     'work_url_site',
    }

    # Form-field names prefix for address + correspondence with VCF field types.
    address_prefixes = {
        'HOME': HOME_ADDR_PREFIX,
        'WORK': WORK_ADDR_PREFIX,
    }
    # Mapping between form fields names (which use vcf lib names) & Address fields names.
    address_mapping = [
        ('name',     'name'),
        ('address',  'address'),
        ('city',     'city'),
        ('country',  'country'),
        ('code',     'zipcode'),
        ('region',   'department'),
    ]

    # blocks = CremeModelForm.blocks.new(
    #     {
    #         'id': 'details',
    #         'label': _('Details'),
    #         'fields': contact_details,
    #     }, {
    #         'id': 'contact_address',
    #         'label': _('Billing address'),
    #         'fields': [HOME_ADDR_PREFIX + n[0] for n in address_mapping],
    #     }, {
    #         'id': 'organisation',
    #         'label': _('Organisation'),
    #         'fields': [
    #             'create_or_attach_orga', 'organisation', 'relation',
    #             *chain.from_iterable(
    #                 (f'update_work_{fn}', f'work_{fn}') for fn in orga_fields
    #             ),
    #         ],
    #     }, {
    #         'id': 'organisation_address',
    #         'label': _('Organisation billing address'),
    #         'fields': [
    #             'update_work_address',
    #             *(WORK_ADDR_PREFIX + n[0] for n in address_mapping),
    #         ]
    #     },
    # )

    type_help_text  = _('Read in VCF File without type: ')
    other_help_text = _('Read in VCF File: ')

    def __init__(self, vcf_data=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        self.contact_address = self.organisation_address = None

        # Cleaned data about image embedded/linked in the file
        self._vcf_image_info: Optional[Tuple[ContentFile, str]] = None

        # Organisation chosen/created by the user (filled by clean())
        self.organisation = None

        # Organisation automatically found from VCF file
        self._found_organisation = None

        # Image fields ---------
        # TODO: separated method ?
        image_f = fields.get('image')
        fields_to_remove = set()
        if image_f:
            # If the field "image" has been configured to be required,
            # we do the same with the hidden input
            # (one of the 2 fields will be removed just after)
            fields['image_encoded'].required = image_f.required
        else:
            fields_to_remove.add('image_encoded')

        if vcf_data:
            self._init_contact_fields(vcf_data)
            self._init_orga_fields(vcf_data)
            self._init_addresses_fields(vcf_data)

            if vcf_data.contents.get('photo'):
                fields['image_encoded'].initial = vcf_data.photo.value.replace('\n', '')
                fields_to_remove.add('image')
            else:
                fields_to_remove.add('image_encoded')
        else:
            fields_to_remove.add('image' if 'image_encoded' in self.data else 'image_encoded')

        for field_to_remove in fields_to_remove:
            fields.pop(field_to_remove, None)

        # Beware: this queryset directly in the field declaration does not work
        #   on some systems in unit tests...
        #   (it seems that the problem it caused by the M2M - other fields work, but why ???)
        fields['relation'].queryset = RelationType.objects.filter(
            subject_ctypes=_get_ct(Contact),
            # object_ctypes=_get_ct(Organisation),
            symmetric_type__subject_ctypes=_get_ct(Organisation),
            is_internal=False,
            subject_properties__isnull=True,  # TODO: propose to add properties?
            # TODO: validates Organisation properties instead of ignoring the RelationType
            symmetric_type__subject_properties__isnull=True,
        )

        self._hide_fields()
        self._forced_orga_fields = self._build_missing_orga_fields()
        self._build_customfields()

    # TODO factorise with/use CustomFieldsMixin ?
    @staticmethod
    def _build_customfield_name(cfield):
        return _CUSTOM_NAME.format(cfield.id)

    def _build_customfields(self):
        fields = self.fields
        get_ct = ContentType.objects.get_for_model

        contact_cfields, orga_cfields = split_filter(
            lambda cfield: cfield.content_type.model_class() == Contact,
            CustomField.objects.filter(
                is_required=True,
                is_deleted=False,
                content_type__in=[get_ct(Contact), get_ct(Organisation)],
            ),
        )

        user = self.user
        build_name = self._build_customfield_name

        for cfield in contact_cfields:
            fields[build_name(cfield)] = cfield.get_formfield(None, user=user)

        orga = self._found_organisation
        if orga and orga_cfields:
            cvalues_map = CustomField.get_custom_values_map([orga], orga_cfields)

            def initial_value(cfield):
                return cvalues_map[orga.id].get(cfield.id)
        else:
            def initial_value(cfield):
                return None

        for cfield in orga_cfields:
            fields[build_name(cfield)] = cfield.get_formfield(initial_value(cfield), user=user)

        self._contact_cfields = contact_cfields
        self._orga_cfields    = orga_cfields

    def _build_missing_orga_fields(self):
        """Add the Organisation fields required by configuration which are missing."""
        fields = self.fields
        forced_fields = []

        orga = self._found_organisation
        if orga:
            def get_initial(field_name):
                return getattr(orga, field_name)
        else:
            def get_initial(field_name):
                return None

        for field in self.fields_configs.get_for_model(Organisation).required_fields:
            # TODO: specific block
            prefixed_name = f'work_{field.name}'
            if prefixed_name not in fields:
                fields[prefixed_name] = field.formfield(initial=get_initial(field.name))
                forced_fields.append(field.name)

        return forced_fields

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
                # civ = Civility.objects.filter(shortcut__icontains=prefix).first()
                # TODO: test __iexact
                # TODO: should use levenshtein distance
                civ = Civility.objects.filter(shortcut__iexact=prefix).first()
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

    # def _init_orga_field(self, vcf_data):
    def _init_orga_fields(self, vcf_data):
        if vcf_data.contents.get('org'):
            fields = self.fields

            org_name = vcf_data.org.value[0]
            self._found_organisation = orga = Organisation.objects.filter(name=org_name).first()

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
                fields[prefix + 'address'].initial = (
                    f'{box} {value.street}' if box else value.street
                )
                fields[f'{prefix}city'].initial    = value.city
                fields[f'{prefix}country'].initial = value.country
                fields[f'{prefix}code'].initial    = value.code
                fields[f'{prefix}region'].initial  = value.region
            else:
                self._generate_help_text(
                    'homeaddr_address',
                    ', '.join([
                        value.box, value.street, value.city,
                        value.region, value.code, value.country,
                    ]),
                )

    def _generate_help_text(self, field_name, value):
        field = self.fields[field_name]
        help_text = field.help_text

        if not help_text:
            field.help_text = self.type_help_text + value
        else:
            field.help_text = f'{help_text} | {value}'

    def clean_image_encoded(self):
        encoded_image = self.cleaned_data['image_encoded']

        if encoded_image:
            image_data = ''

            if encoded_image.startswith(URL_START):
                # TODO: only retrieve once (ie: what if several validation errors) ?

                try:
                    # TODO: smaller timeout than our own web server?
                    with urlopen(encoded_image) as f:
                        max_size = settings.VCF_IMAGE_MAX_SIZE
                        if int(f.info()['content-length']) > max_size:
                            raise ValidationError(
                                gettext(
                                    'The referenced image is too large '
                                    '(limit is {} bytes).'
                                ).format(max_size)
                            )

                        image_data = f.read()
                except URLError as e:
                    raise ValidationError(
                        gettext(
                            'An error occurred when trying to retrieve the referenced image '
                            '[original error: {}].'
                        ).format(e)
                    )
            else:  # TODO: manage urls encoded in base64 ??
                try:
                    image_data = base64.decodebytes(encoded_image.encode())
                except Exception as e:
                    raise ValidationError(
                        gettext(
                            'An error occurred when trying to decode the embedded image '
                            '[original error: {}].'
                        ).format(e)
                    )

            try:
                img_format = get_image_format(image_data)
            except Exception:
                logger.exception('Clean image encoded in VCF')
                raise ValidationError(gettext('Invalid image data'))

            # TODO: check with settings.ALLOWED_IMAGES_EXTENSIONS ?
            self._vcf_image_info = (ContentFile(image_data), img_format)

        return encoded_image

    def _clean_orga_field(self, field_name):
        cleaned_data = self.cleaned_data
        cleaned = cleaned_data.get(field_name)

        if cleaned_data['create_or_attach_orga'] and not cleaned:
            raise ValidationError(
                self.error_messages['required4orga'], code='required4orga',
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
                raise ValidationError(
                    self.error_messages['no_orga_creation'],
                    code='no_orga_creation',
                )
            elif not cleaned_data['organisation']:
                raise ValidationError(
                    self.error_messages['orga_not_selected'],
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

        if not value and all(
            cleaned_data[k]
            for k in ('create_or_attach_orga', 'organisation', f'update_{field_name}')
        ):
            raise ValidationError(
                self.error_messages['required2update'],
                code='required2update',
            )

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

    def _cleaned_address(self, cleaned_data, data_prefix, address=None):
        if address is None:
            address = Address()

        address_mapping = self.address_mapping

        # NB: we do not use cleaned_data.get() in order to not overload
        #     default fields values
        for form_fname, model_fname in address_mapping:
            try:
                value = cleaned_data[data_prefix + form_fname]
            except KeyError:
                pass
            else:
                if value:
                    setattr(address, model_fname, value)

        if address:
            try:
                address.full_clean()
            except ValidationError as e:
                for field_name, error in e.message_dict.items():
                    error_name = None

                    if field_name:
                        for form_fname, model_fname in address_mapping:
                            if model_fname == field_name:
                                error_name = data_prefix + form_fname
                                break

                    self.add_error(field=error_name, error=error)

            return address

        return None

    def clean(self):
        cleaned_data = self.cleaned_data
        contact = self.instance

        # NB: prevent error when the field "image" is required & image build later.
        if self._vcf_image_info:
            image = Document(
                user=cleaned_data['user'],
                title='Image of contact',
                filedata='TMP',
                linked_folder=Folder.objects.get(uuid=UUID_FOLDER_IMAGES),
                description=gettext('Imported by VCFs'),
            )

            # NB: sadly we do not clean with the final title/filedata...
            try:
                image.full_clean()
            except ValidationError as e:
                # TODO: test
                logger.exception(
                    f'{type(self).__name__}.clean(): error when build embedded image'
                )
                self.add_error(
                    field=None,
                    error=gettext(
                        'Error with image data in the VCF file [original error: {}]'
                    ).format(e)
                )
            else:
                contact.image = image

        super().clean()

        if not self._errors:
            self.contact_address = self._cleaned_address(
                cleaned_data, data_prefix=HOME_ADDR_PREFIX,
            )

            if cleaned_data['create_or_attach_orga']:
                get_data = cleaned_data.get
                organisation = get_data('organisation')

                if organisation:
                    # TODO: select_for_update() option in CreatorEntityField ?
                    organisation = Organisation.objects.select_for_update().get(id=organisation.id)

                    for fname in self.orga_fields:
                        if get_data(f'update_work_{fname}'):
                            setattr(organisation, fname, get_data(f'work_{fname}'))

                    for fname in self._forced_orga_fields:
                        setattr(organisation, fname, get_data(f'work_{fname}'))

                    if get_data('update_work_address'):
                        self.organisation_address = self._cleaned_address(
                            cleaned_data,
                            data_prefix=WORK_ADDR_PREFIX,
                            address=organisation.billing_address,
                        )
                else:
                    # NB: we do not use cleaned_data.get() in order to not overload
                    #     default fields values
                    orga_kwargs = {}
                    for fname in chain(self.orga_fields, self._forced_orga_fields):
                        try:
                            orga_kwargs[fname] = cleaned_data[f'work_{fname}']
                        except KeyError:
                            pass

                    organisation = Organisation(user=cleaned_data['user'], **orga_kwargs)
                    self.organisation_address = self._cleaned_address(
                        cleaned_data, data_prefix=WORK_ADDR_PREFIX,
                    )

                try:
                    organisation.full_clean()
                except ValidationError as e:
                    fields = self.fields
                    for field_name, error in e.message_dict.items():
                        if field_name:
                            prefixed_fname = f'work_{field_name}'

                            if prefixed_fname in fields:
                                field_name = prefixed_fname

                        self.add_error(field=field_name, error=error)
                else:
                    self.organisation = organisation

        return cleaned_data

    # def _create_contact(self, cleaned_data):
    #     get_data = cleaned_data.get
    #
    #     contact = Contact.objects.create(
    #         user=cleaned_data['user'],
    #         civility=cleaned_data['civility'],
    #         first_name=cleaned_data['first_name'],
    #         last_name=cleaned_data['last_name'],
    #         position=get_data('position'),
    #         # NB: we do not use cleaned_data.get() in order to not overload
    #         #     default fields values
    #         **{
    #             fname: cleaned_data[fname]
    #             for fname in self.contact_details
    #             if fname in cleaned_data
    #         }
    #     )
    #
    #     self._save_customfields(contact, self._contact_cfields)
    #
    #     return contact

    # def _create_address(self, cleaned_data, owner, data_prefix):
    #     # NB: we do not use cleaned_data.get() in order to not overload default fields values
    #     kwargs = {}
    #     for form_fname, model_fname in self.address_mapping:
    #         try:
    #             kwargs[model_fname] = cleaned_data[data_prefix + form_fname]
    #         except KeyError:
    #             pass
    #
    #     address = Address(owner=owner, **kwargs)
    #
    #     if address:
    #         address.save()
    #         return address

    # def _create_image(self, contact):
    #     cleaned_data = self.cleaned_data
    #     image_encoded = cleaned_data['image_encoded']
    #
    #     if image_encoded:
    #         img_name = secure_filename(
    #             f'{contact.last_name}_{contact.first_name}_{contact.id}'
    #         )
    #         img_path = None
    #
    #         if image_encoded.startswith(URL_START):
    #             tmp_img_path = None
    #
    #             try:
    #                 if (
    #                     int(urlopen(image_encoded).info()['content-length'])
    #                     <= settings.VCF_IMAGE_MAX_SIZE
    #                 ):
    #                     tmp_img_path = path.normpath(path.join(IMG_UPLOAD_PATH, img_name))
    #
    #                     urlretrieve(
    #                         image_encoded,
    #                         path.normpath(path.join(settings.MEDIA_ROOT, tmp_img_path)),
    #                     )
    #             except Exception:
    #                 logger.exception('Error with image')
    #             else:
    #                 img_path = tmp_img_path
    #         else:
    #             try:
    #                 img_data = base64.decodebytes(image_encoded.encode())
    #                 img_path = handle_uploaded_file(
    #                     ContentFile(img_data),
    #                     path=IMG_UPLOAD_PATH.split('/'),
    #                     name=f'{img_name}.{get_image_format(img_data)}',
    #                 )
    #             except Exception:
    #                 logger.exception('VcfImportForm.save()')
    #
    #         if img_path:
    #             return Document.objects.create(
    #                 user=cleaned_data['user'],
    #                 title=gettext('Image of {contact}').format(contact=contact),
    #                 filedata=img_path,
    #                 linked_folder=Folder.objects.get(uuid=UUID_FOLDER_IMAGES),
    #                 description=gettext('Imported by VCFs'),
    #             )

    # def _create_orga(self, contact):
    #     cleaned_data = self.cleaned_data
    #
    #     if cleaned_data['create_or_attach_orga']:
    #         get_data = cleaned_data.get
    #         organisation = get_data('organisation')
    #         save_orga    = False
    #         user         = cleaned_data['user']
    #         addr_prefix  = WORK_ADDR_PREFIX
    #
    #         if organisation:
    #             # todo: select_for_update() option in CreatorEntityField ?
    #             organisation = Organisation.objects.select_for_update().get(id=organisation.id)
    #
    #             for fname in self.orga_fields:
    #                 if get_data('update_work_' + fname):
    #                     setattr(organisation, fname, get_data('work_' + fname))
    #
    #             if get_data('update_work_address'):
    #                 billing_address = organisation.billing_address
    #
    #                 if billing_address is not None:
    #                     for form_fname, model_fname in self.address_mapping:
    #                         value = get_data(addr_prefix + form_fname)
    #
    #                         if value:
    #                             setattr(billing_address, model_fname, value)
    #
    #                     organisation.billing_address.save()
    #                 else:
    #                     organisation.billing_address = self._create_address(
    #                         cleaned_data, owner=organisation, data_prefix=addr_prefix,
    #                     )
    #
    #             save_orga = True
    #         else:
    #             # NB: we do not use cleaned_data.get() in order to not overload
    #             #     default fields values
    #             orga_kwargs = {}
    #             for fname in self.orga_fields:
    #                 try:
    #                     orga_kwargs[fname] = cleaned_data['work_' + fname]
    #                 except KeyError:
    #                     pass
    #
    #             organisation = Organisation.objects.create(user=user, **orga_kwargs)
    #
    #             orga_addr = self._create_address(
    #                 cleaned_data, owner=organisation, data_prefix=addr_prefix,
    #             )
    #             if orga_addr is not None:
    #                 organisation.billing_address = orga_addr
    #                 save_orga = True
    #
    #         if save_orga:
    #             organisation.save()
    #
    #         self._save_customfields(organisation, self._orga_cfields)
    #         Relation.objects.create(
    #             user=user,
    #             subject_entity=contact,
    #             type=cleaned_data['relation'],
    #             object_entity=organisation,
    #         )
    def _create_orga(self, contact):
        organisation = self.organisation
        cleaned_data = self.cleaned_data

        if organisation:
            save_orga = False
            if organisation.id:
                save_orga = True
            else:
                organisation.save()

            orga_addr = self.organisation_address
            if orga_addr is not None:
                orga_addr.owner = organisation
                orga_addr.save()

                organisation.billing_address = orga_addr
                save_orga = True

            if save_orga:
                organisation.save()

            self._save_customfields(organisation, self._orga_cfields)
            Relation.objects.create(
                user=cleaned_data['user'],
                subject_entity=contact,
                type=cleaned_data['relation'],
                object_entity=organisation,
            )

    def get_blocks(self):
        build_cfield_name = self._build_customfield_name

        return FieldBlockManager(
            {
                'id': 'general',
                'label': _('Main information on contact'),
                'fields': '*',
                'layout': LAYOUT_DUAL_FIRST,
            }, {
                'id': 'details',
                'label': _('Details on contact'),
                'fields': self.contact_details,
                'layout': LAYOUT_DUAL_SECOND,
            }, {
                'id': 'contact_address',
                'label': _('Contact billing address'),
                'fields': [HOME_ADDR_PREFIX + n[0] for n in self.address_mapping],
                'layout': LAYOUT_DUAL_SECOND,
            }, {
                # This block separates visually the blocks for contact & organisation
                'id': 'spacer',
                'label': 'Spacer',
                'fields': (),
            }, {
                'id': 'organisation',
                'label': _('Organisation'),
                'fields': [
                    'create_or_attach_orga', 'organisation', 'relation',
                    *chain.from_iterable(
                        (f'update_work_{fn}', f'work_{fn}') for fn in self.orga_fields
                    ),
                    # TODO: separated block(s)?
                    *(f'work_{fn}' for fn in self._forced_orga_fields),
                    *(build_cfield_name(cfield) for cfield in self._orga_cfields),
                ],
                'layout': LAYOUT_DUAL_FIRST,
            }, {
                'id': 'organisation_address',
                'label': _('Organisation billing address'),
                'fields': [
                    'update_work_address',
                    *(WORK_ADDR_PREFIX + n[0] for n in self.address_mapping),
                ],
                'layout': LAYOUT_DUAL_SECOND,
            },
        ).build(self)

    # TODO: factorise with CustomFieldsMixin
    def _save_customfields(self, entity, cfields):
        if cfields:
            cleaned_data = self.cleaned_data
            build_name = self._build_customfield_name
            save_values = CustomFieldValue.save_values_for_entities

            for cfield in cfields:
                save_values(cfield, [entity], cleaned_data[build_name(cfield)])

    def _save_image(self):
        if self._vcf_image_info:
            contact = self.instance
            image = contact.image
            file_field = type(image)._meta.get_field('filedata')
            img_data, img_format = self._vcf_image_info

            assign_2_charfield(
                image, 'title',
                gettext('Image of {contact}').format(contact=contact),
            )
            image.filedata = handle_uploaded_file(
                img_data,
                path=file_field.upload_to.split('/'),
                name=f'{contact.last_name}_{contact.first_name}.{img_format}',
                max_length=file_field.max_length
            )
            image.save()

    # @atomic
    # def save(self, *args, **kwargs):
    #     cleaned_data = self.cleaned_data
    #     save_contact = False
    #     contact = self._create_contact(cleaned_data)
    #
    #     image = self._create_image(contact)
    #     if image is not None:
    #         contact.image = image
    #         save_contact = True
    #
    #     contact_addr = self._create_address(cleaned_data, owner=contact,
    #                                         data_prefix=HOME_ADDR_PREFIX,
    #                                        )
    #     if contact_addr is not None:
    #         contact.billing_address = contact_addr
    #         save_contact = True
    #
    #     self._create_orga(contact)
    #
    #     if save_contact:
    #         contact.save()
    #
    #     return contact
    @atomic
    def save(self, *args, **kwargs):
        contact = self.instance
        self._save_image()
        super().save(*args, **kwargs)
        self._save_customfields(contact, self._contact_cfields)

        contact_addr = self.contact_address
        if contact_addr is not None:
            contact_addr.owner = contact
            contact_addr.save()

            contact.billing_address = contact_addr
            contact.save()

        self._create_orga(contact)

        return contact
