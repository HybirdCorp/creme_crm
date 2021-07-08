# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
import os
import shutil
import subprocess
import sys
from functools import partial
from itertools import chain
from tempfile import mkdtemp
from typing import List, Optional, Tuple, Type

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.fields import EmailField, Field
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import fields
from creme.creme_core.utils.meta import is_date_field
from creme.creme_core.utils.secure_filename import secure_filename
from creme.documents import get_document_model
from creme.documents.models import fields as doc_fields

from ..backends.models import CrudityBackend
from ..utils import generate_guid_for_field

logger = logging.getLogger(__name__)
Document = get_document_model()

INFOPATH_LANGUAGES_CODES = {
    'fr':    '1036',  # http://support.microsoft.com/kb/12739/fr
    'en-gb': '2057',
    'en':    '1033',
}


def get_none(x):
    return None


def get_element_template(element_type, template_name):
    return f'crudity/infopath/create_template/frags/{element_type}/element/{template_name}'


# TODO: use ClassKeyedMap
_ELEMENT_TEMPLATE = {
    models.AutoField: get_none,
    models.BooleanField: partial(get_element_template, template_name='boolean_field.xml'),
    models.CharField: partial(get_element_template, template_name='string_field.xml'),
    models.CommaSeparatedIntegerField: get_none,
    models.DateField: partial(get_element_template, template_name='date_field.xml'),
    models.DateTimeField: partial(get_element_template, template_name='datetime_field.xml'),
    models.DecimalField: partial(get_element_template, template_name='decimal_field.xml'),
    models.EmailField: partial(get_element_template, template_name='string_field.xml'),
    models.FileField: partial(get_element_template, template_name='foreignkey_field.xml'),
    models.FilePathField: get_none,
    models.FloatField: partial(get_element_template, template_name='decimal_field.xml'),
    models.ImageField: partial(get_element_template, template_name='foreignkey_field.xml'),
    models.IntegerField: partial(get_element_template, template_name='integer_field.xml'),
    models.IPAddressField: get_none,
    models.NullBooleanField: partial(get_element_template, template_name='boolean_field.xml'),
    models.PositiveIntegerField: partial(get_element_template, template_name='integer_field.xml'),
    models.PositiveSmallIntegerField: partial(
        get_element_template, template_name='integer_field.xml',
    ),
    models.SlugField: partial(get_element_template, template_name='string_field.xml'),
    models.SmallIntegerField: partial(get_element_template, template_name='integer_field.xml'),
    models.TextField: partial(get_element_template, template_name='text_field.xml'),
    models.TimeField: partial(get_element_template, template_name='time_field.xml'),
    models.URLField: partial(get_element_template, template_name='url_field.xml'),
    models.ForeignKey: partial(get_element_template, template_name='foreignkey_field.xml'),
    models.ManyToManyField: partial(get_element_template, template_name='m2m_field.xml'),
    models.OneToOneField: get_none,

    fields.PhoneField: partial(get_element_template, template_name='string_field.xml'),
    fields.DurationField: get_none,
    fields.ModificationDateTimeField: partial(
        get_element_template, template_name='datetime_field.xml'
    ),
    fields.CreationDateTimeField: partial(
        get_element_template, template_name='datetime_field.xml',
    ),
    fields.CremeUserForeignKey: partial(get_element_template, template_name='integer_field.xml'),

    # TODO: remove when ClassKeyedMap is used
    doc_fields.ImageEntityForeignKey: partial(
        get_element_template, template_name='foreignkey_field.xml',
    ),
    doc_fields.ImageEntityManyToManyField: partial(
        get_element_template, template_name='m2m_field.xml',
    ),
}

XSL_VIEW_FIELDS_TEMPLATES_PATH = 'crudity/infopath/create_template/frags/xsl/view/{}.xml'
# Types which could be nil="true" in template.xml
_TEMPLATE_NILLABLE_TYPES: Tuple[Type[Field], ...] = (
    models.DecimalField,
    models.IntegerField,
    models.TimeField,
    models.DateField,
    models.DateTimeField,
    models.FileField,
    models.ForeignKey
)


class InfopathFormField:
    def __init__(self, urn, model, field_name, request):
        self.request     = request
        self.uuid        = generate_guid_for_field(urn, model, field_name)
        self.name        = field_name
        self.model       = model
        self.model_field = self._get_model_field()
        self.validation  = self._get_validation()
        self.editing     = self._get_editing()
        self.xsd_element = self._get_xsd_element()
        self.xsl_element = self._get_xsl_element()

    def _get_model_field(self) -> Field:
        """Returns the field of the model by its name.
        name can be either its field name or its field attribute name (e.g: cached fields for Fk)
        """
        name = self.name

        try:
            return self.model._meta.get_field(name)
        except FieldDoesNotExist as e:
            for field in self.model._meta.fields:
                if field.get_attname() == name:
                    return field

            raise e

    def _get_element(self, element_type: str) -> Optional[str]:
        model_field = self.model_field
        field_type  = model_field.__class__

        element_builder = _ELEMENT_TEMPLATE.get(field_type)
        if element_builder is None:
            logger.warning(
                'The field "%s" has a type which is not managed (%s)',
                model_field, field_type,
            )
            return None

        template_name = element_builder(element_type)

        return (
            render_to_string(template_name, {'field': self}, request=self.request)
            if template_name is not None else
            None
        )

    def _get_xsd_element(self) -> Optional[str]:
        return self._get_element('xsd')

    def _get_xsl_element(self) -> Optional[str]:
        return self._get_element('xsl')

    def _get_validation(self) -> List[str]:  # TODO: Could be cool to match django validators
        validation = []
        if isinstance(self.model_field, EmailField):
            validation.append(render_to_string(
                'crudity/infopath/create_template/frags/validation/email_field.xml',
                {'field': self}, request=self.request,
            ))

        return validation

    def _get_editing(self) -> Optional[str]:
        model_field = self.model_field
        template_name = None
        tpl_dict = {'field': self}

        if isinstance(model_field, models.TextField):
            template_name = 'crudity/infopath/create_template/frags/editing/text_field.xml'

        elif is_date_field(model_field):
            template_name = 'crudity/infopath/create_template/frags/editing/date_field.xml'

        elif isinstance(model_field, models.FileField):
            tpl_dict.update({'allowed_file_types': settings.ALLOWED_EXTENSIONS})
            template_name = 'crudity/infopath/create_template/frags/editing/file_field.xml'

        elif (
            isinstance(model_field, models.ImageField)
            or (
                isinstance(model_field, models.ForeignKey)
                and issubclass(model_field.remote_field.model, Document)
            )
        ):
            tpl_dict.update({'allowed_file_types': settings.ALLOWED_IMAGES_EXTENSIONS})
            template_name = 'crudity/infopath/create_template/frags/editing/file_field.xml'

        elif isinstance(model_field, models.ManyToManyField):
            template_name = 'crudity/infopath/create_template/frags/editing/m2m_field.xml'

        return render_to_string(
            template_name, tpl_dict, request=self.request,
        ) if template_name is not None else None

    def get_view_element(self) -> str:
        template_name = XSL_VIEW_FIELDS_TEMPLATES_PATH.format(
            self.model_field.get_internal_type()
        )
        try:
            return render_to_string(
                template_name,
                {
                    'field': self,
                    'choices': self._get_choices(),
                },
                request=self.request,
            )
        except TemplateDoesNotExist:
            return ''

    def _get_choices(self) -> List[Tuple[int, str]]:
        if isinstance(self.model_field, (models.ForeignKey, models.ManyToManyField)):
            choices = [
                (entity.pk, str(entity))
                for entity in self.model_field.remote_field.model._default_manager.all()
            ]
        else:
            choices = []

        return choices

    @property
    def is_nillable(self) -> bool:
        model_field = self.model_field
        return bool(model_field.null and isinstance(model_field, _TEMPLATE_NILLABLE_TYPES))

    @property
    def is_file_field(self) -> bool:
        model_field = self.model_field
        return (
            issubclass(model_field.__class__, models.FileField)
            or (
                isinstance(model_field, models.ForeignKey)
                and issubclass(model_field.remote_field.model, Document)
            )
        )

    @property
    def is_m2m_field(self) -> bool:
        return isinstance(self.model_field, models.ManyToManyField)

    @property
    def is_bool_field(self) -> bool:
        return isinstance(self.model_field, models.BooleanField)

    def get_m2m_xsl_choices_str(self):
        return ' and '.join(f'.!="{c[0]}"' for c in self._get_choices())


class InfopathFormBuilder:
    def __init__(self, request, backend: CrudityBackend):
        # assert backend.model is not None
        assert hasattr(backend, 'model')
        self.backend   = backend
        self.now       = now()
        self.namespace = self.get_namespace()
        self.urn       = self.get_urn()
        self.request   = request
        self._fields: Optional[List[InfopathFormField]] = None

    def get_namespace(self) -> str:
        return 'http://schemas.microsoft.com/office/infopath/2003/myXSD/{}'.format(
            self.now.strftime('%Y-%m-%dT%H:%M:%S'),
        )

    def get_urn(self) -> str:
        # TODO: change 'create' ? Make a constant ?
        return 'urn:schemas-microsoft-com:office:infopath:{}-{}:-myXSD-{}'.format(
            'create',
            self.backend.subject.lower(),
            self.now.strftime('%Y-%m-%dT%H:%M:%S'),
        )

    def _get_lang_code(self, code) -> str:
        return INFOPATH_LANGUAGES_CODES.get(code, '1033')

    @property
    def fields(self) -> List[InfopathFormField]:
        if self._fields is None:
            backend = self.backend
            build_field = partial(
                InfopathFormField, self.urn, backend.model, request=self.request,
            )
            self._fields = [
                build_field(field_name)
                for field_name in backend.body_map
                if field_name != 'password'
            ]

        return self._fields

    @property
    def file_fields(self) -> List[InfopathFormField]:
        """File fields have extra xml tags
        N.B: ForeignKey of (Creme) Image type is considered as file type
        """
        return [field for field in self.fields if field.is_file_field]

    def _render(self, file_name) -> bytes:
        request = self.request
        cab_files_renderers = {
            'manifest.xsf': self._render_manifest_xsf,
            'myschema.xsd': self._render_myschema_xsd,
            'template.xml': self._render_template_xml,
            'upgrade.xsl':  self._render_upgrade_xsl,
            'view1.xsl':    self._render_view_xsl,
        }

        media_files = {'creme.png'}
        backend_path = None

        try:
            backend_path = mkdtemp(prefix='creme_crudity_infopath')
            os_path = os.path
            path_join = os_path.join
            copy2 = shutil.copy2

            crudity_media_path = path_join(
                settings.CREME_ROOT,
                'crudity', 'templates', 'crudity', 'infopath', 'create_template',
            )

            for name in media_files:
                media_path = path_join(crudity_media_path, name)
                copy2(media_path, path_join(backend_path, name))

            for file_name, renderer in cab_files_renderers.items():
                with open(path_join(backend_path, file_name), 'wb') as f:
                    f.write(renderer(request).encode('utf8'))

            final_files_paths = (
                path_join(backend_path, cab_file)
                for cab_file in chain(cab_files_renderers, media_files)
            )
            infopath_form_filepath = path_join(backend_path, file_name)

            if sys.platform.startswith('win'):
                ddf_file_content = render_to_string(
                    'crudity/infopath/create_template/create_cab.ddf',
                    {
                        'file_name':    file_name,
                        'backend_path': backend_path,
                    },
                    request=request,
                )

                ddf_path = path_join(backend_path, 'create_cab.ddf')
                with open(ddf_path, 'wb') as f:
                    f.write(ddf_file_content)

                cabify_content = render_to_string(
                    'crudity/infopath/create_template/cabify.bat',
                    {'ddf_path': ddf_path},
                    request=request,
                )

                cabify_path = path_join(backend_path, 'cabify.bat')
                with open(cabify_path, 'wb') as f:
                    f.write(cabify_content)

                subprocess.call([cabify_path])
                # Clean because  .Set GenerateInf=off doesn't seems to work...
                os.unlink(path_join(settings.CREME_ROOT, 'setup.inf'))
                os.unlink(path_join(settings.CREME_ROOT, 'setup.rpt'))
            else:
                subprocess.call(['lcab', '-qn', *final_files_paths, infopath_form_filepath])

            with open(infopath_form_filepath, 'rb') as f:
                return f.read()
        finally:
            if backend_path:
                shutil.rmtree(backend_path)

    def render(self) -> HttpResponse:
        file_name = '{}.xsn'.format(
            secure_filename(CrudityBackend.normalize_subject(self.backend.subject))
        )
        # response = HttpResponse(
        #     self._render(file_name), content_type='application/vnd.ms-infopath',
        # )
        # response['Content-Disposition'] = f'attachment; filename={file_name}'
        #
        # return response
        return HttpResponse(
            self._render(file_name),
            headers={
                'Content-Type': 'application/vnd.ms-infopath',
                'Content-Disposition': f'attachment; filename="{file_name}"',
            },
        )

    def _render_manifest_xsf(self, request) -> str:
        return render_to_string(
            'crudity/infopath/create_template/manifest.xsf',
            {
                'creme_namespace': self.namespace,
                'form_urn':        self.urn,
                'lang_code':       self._get_lang_code(request.LANGUAGE_CODE),
                'form_name':       self.backend.subject,
                'fields':          self.fields,
                'file_fields':     self.file_fields,
                'to':              settings.CREME_GET_EMAIL,
                'password':        self.backend.password,
            },
            request=request,
        )

    def _render_myschema_xsd(self, request) -> str:
        return render_to_string(
            'crudity/infopath/create_template/myschema.xsd',
            {
                'creme_namespace': self.namespace,
                'fields':          self.fields,
            },
            request=request,
        )

    def _render_template_xml(self, request) -> str:
        return render_to_string(
            'crudity/infopath/create_template/template.xml',
            {
                'creme_namespace': self.namespace,
                'form_urn':        self.urn,
                'fields':          self.fields,
            },
            request=request,
        )

    def _render_upgrade_xsl(self, request) -> str:
        return render_to_string(
            'crudity/infopath/create_template/upgrade.xsl',
            {
                'creme_namespace': self.namespace,
                'fields':          self.fields,
            },
            request=request,
        )

    def _render_view_xsl(self, request) -> str:
        backend = self.backend
        return render_to_string(
            'crudity/infopath/create_template/view1.xsl',
            {
                'creme_namespace': self.namespace,
                'fields':          self.fields,
                'form_title':      '{} {}'.format(
                    _('Create'),
                    backend.model._meta.verbose_name,
                ),
            },
            request=request,
        )
