# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from functools import partial
from itertools import chain
import os
import sys
import shutil
import subprocess
from tempfile import mkdtemp
from unicodedata import normalize

from django.conf import settings
from django.db import models
from django.db.models.fields import FieldDoesNotExist, EmailField
from django.core.files.base import File
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import fields
from creme.creme_core.utils.meta import is_date_field

from creme.media_managers.models import Image

from ..utils import generate_guid_for_field
from ..backends.models import CrudityBackend

#Don't forget to include xml templates when generating locales !! (django-admin.py makemessages -l fr -e html,xml)

INFOPATH_LANGUAGES_CODES = {
#http://support.microsoft.com/kb/12739/fr
    'fr':    '1036',
    'en-gb': '2057',
    'en':    '1033',
}

get_none = lambda x: None
get_element_template = lambda element_type, template_name: "crudity/infopath/create_template/frags/%s/element/%s" % (element_type, template_name)

_ELEMENT_TEMPLATE = {
    models.AutoField:                  get_none,
    models.BooleanField:               lambda element_type: get_element_template(element_type, "boolean_field.xml"),
    models.CharField:                  lambda element_type: get_element_template(element_type, "string_field.xml"),
    models.CommaSeparatedIntegerField: get_none,
    models.DateField:                  lambda element_type: get_element_template(element_type, "date_field.xml"),
    models.DateTimeField:              lambda element_type: get_element_template(element_type, "datetime_field.xml"),
    models.DecimalField:               lambda element_type: get_element_template(element_type, "decimal_field.xml"),
    models.EmailField:                 lambda element_type: get_element_template(element_type, "string_field.xml"),
    models.FileField:                  lambda element_type: get_element_template(element_type, "foreignkey_field.xml"),
    models.FilePathField:              get_none,
    models.FloatField:                 lambda element_type: get_element_template(element_type, "decimal_field.xml"),
    models.ImageField:                 lambda element_type: get_element_template(element_type, "foreignkey_field.xml"),
    models.IntegerField:               lambda element_type: get_element_template(element_type, "integer_field.xml"),
    models.IPAddressField:             get_none,
    models.NullBooleanField:           lambda element_type: get_element_template(element_type, "boolean_field.xml"),
    models.PositiveIntegerField:       lambda element_type: get_element_template(element_type, "integer_field.xml"),
    models.PositiveSmallIntegerField:  lambda element_type: get_element_template(element_type, "integer_field.xml"),
    models.SlugField:                  lambda element_type: get_element_template(element_type, "string_field.xml"),
    models.SmallIntegerField:          lambda element_type: get_element_template(element_type, "integer_field.xml"),
    models.TextField:                  lambda element_type: get_element_template(element_type, "text_field.xml"),
    models.TimeField:                  lambda element_type: get_element_template(element_type, "time_field.xml"),
    models.URLField:                   lambda element_type: get_element_template(element_type, "url_field.xml"),
    models.ForeignKey:                 lambda element_type: get_element_template(element_type, "foreignkey_field.xml"),
    models.ManyToManyField:            lambda element_type: get_element_template(element_type, "m2m_field.xml"),
    models.OneToOneField:              get_none,

    fields.PhoneField:                 lambda element_type: get_element_template(element_type, "string_field.xml"),
    fields.DurationField:              get_none,
    fields.ModificationDateTimeField:  lambda element_type: get_element_template(element_type, "datetime_field.xml"),
    fields.CreationDateTimeField:      lambda element_type: get_element_template(element_type, "datetime_field.xml"),
    fields.CremeUserForeignKey:        lambda element_type: get_element_template(element_type, "integer_field.xml"),
}

XSL_VIEW_FIELDS_TEMPLATES_PATH = "crudity/infopath/create_template/frags/xsl/view/%s.xml"
_TEMPLATE_NILLABLE_TYPES = (#Types which could be nil="true" in template.xml
    models.DecimalField,
    models.IntegerField,
    models.TimeField,
    models.DateField,
    models.DateTimeField,
    models.FileField,
    models.ForeignKey
)


class InfopathFormField(object):
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

    def _get_model_field(self):
        """Returns the field of the model by its name.
        name can be either its field name or its field attribute name (e.g: cached fields for Fk)
        """
        try:
            return self.model._meta.get_field(self.name)
        except FieldDoesNotExist, e:
            name = self.name
            for field in self.model._meta.fields:
                if field.get_attname() == name:
                    return field
            raise e

    def _get_element(self, element_type):
        template_name = _ELEMENT_TEMPLATE.get(self.model_field.__class__)(element_type)
        return render_to_string(template_name, {'field': self}, context_instance=RequestContext(self.request)) if template_name is not None else None

    def _get_xsd_element(self):
        return self._get_element("xsd")

    def _get_xsl_element(self):
        return self._get_element("xsl")

    def _get_validation(self):#TODO: Could be cool to match django validators
        validation = []
        if isinstance(self.model_field, EmailField):
            validation.append(render_to_string("crudity/infopath/create_template/frags/validation/email_field.xml", {'field': self}, context_instance=RequestContext(self.request)))
        return validation

    def _get_editing(self):
        model_field = self.model_field
        template_name = None
        tpl_dict = {'field': self}

        if isinstance(model_field, models.TextField):
            template_name = "crudity/infopath/create_template/frags/editing/text_field.xml"

        elif is_date_field(model_field):
            template_name = "crudity/infopath/create_template/frags/editing/date_field.xml"

        elif isinstance(model_field, models.FileField):
            tpl_dict.update({'allowed_file_types': settings.ALLOWED_EXTENSIONS})
            template_name = "crudity/infopath/create_template/frags/editing/file_field.xml"

        elif isinstance(model_field, models.ImageField) or \
          (isinstance(model_field, models.ForeignKey) and issubclass(model_field.rel.to, Image)):
            tpl_dict.update({'allowed_file_types': settings.ALLOWED_IMAGES_EXTENSIONS})
            template_name = "crudity/infopath/create_template/frags/editing/file_field.xml"

        elif isinstance(model_field, models.ManyToManyField):
            template_name = "crudity/infopath/create_template/frags/editing/m2m_field.xml"

        return render_to_string(template_name, tpl_dict, context_instance=RequestContext(self.request)) if template_name is not None else None

    def get_view_element(self):
        template_name = XSL_VIEW_FIELDS_TEMPLATES_PATH % self.model_field.get_internal_type()
        try:
            return render_to_string(template_name, {'field': self, 'choices': self._get_choices()}, context_instance=RequestContext(self.request))
        except TemplateDoesNotExist:
            return ""

    def _get_choices(self):
        choices = []
        if isinstance(self.model_field, (models.ForeignKey, models.ManyToManyField)):
            choices = [(entity.pk, unicode(entity)) for entity in self.model_field.rel.to._default_manager.all()]
        return choices

    @property
    def is_nillable(self):
        model_field = self.model_field
        return bool(model_field.null and isinstance(model_field, _TEMPLATE_NILLABLE_TYPES))

    @property
    def is_file_field(self):
        model_field = self.model_field
        return issubclass(model_field.__class__, models.FileField) or (isinstance(model_field, models.ForeignKey) and issubclass(model_field.rel.to, Image))

    @property
    def is_m2m_field(self):
        return isinstance(self.model_field, models.ManyToManyField)

    @property
    def is_bool_field(self):
        return isinstance(self.model_field, models.BooleanField)

    def get_m2m_xsl_choices_str(self):
        return " and ".join(['.!="%s"' % c[0] for c in self._get_choices()]) #TODO: generator expression


class InfopathFormBuilder(object):
    def __init__(self, request, backend):
        assert backend.model is not None
        self.backend   = backend
        self.now       = now()
        self.namespace = self.get_namespace()
        self.urn       = self.get_urn()
        self.request   = request
        self._fields   = None

    def get_namespace(self):
        return "http://schemas.microsoft.com/office/infopath/2003/myXSD/%s" % self.now.strftime('%Y-%m-%dT%H:%M:%S')

    def get_urn(self):
        #TODO:Change 'create' ? Make a constant ?
        return 'urn:schemas-microsoft-com:office:infopath:%s-%s:-myXSD-%s' % (
                    'create',
                    self.backend.subject.lower(),
                    self.now.strftime('%Y-%m-%dT%H:%M:%S'),
                )

    def _get_lang_code(self, code):
        return INFOPATH_LANGUAGES_CODES.get(code, '1033')

    @property
    def fields(self):
        if self._fields is None:
            backend      = self.backend
            build_field  = partial(InfopathFormField, self.urn, backend.model, request=self.request)
            self._fields = [build_field(field_name) for field_name in backend.body_map.iterkeys() if field_name != "password"]
        return self._fields

    @property
    def file_fields(self):
        """File fields have extra xml tags
        N.B: ForeignKey of (Creme) Image type is considered as file type
        """
        return [field for field in self.fields if field.is_file_field]

    def _render(self):
        request = self.request
        cab_files = {"manifest.xsf": self._render_manifest_xsf(request),
                     "myschema.xsd": self._render_myschema_xsd(request),
                     "template.xml": self._render_template_xml(request),
                     "upgrade.xsl":  self._render_upgrade_xsl(request),
                     "view1.xsl":    self._render_view_xsl(request),
                    }

        media_files = set(["creme.png"])
        backend_path = None

        try:
            backend_path = mkdtemp(prefix='creme_crudity_infopath')
            os_path = os.path
            path_join = os_path.join
            copy2 = shutil.copy2

            crudity_media_path = path_join(settings.CREME_ROOT, "crudity", "templates", "crudity", "infopath", "create_template")

            for name in media_files:
                media_path = path_join(crudity_media_path, name)
                copy2(media_path, path_join(backend_path, name))

            for file_name, content in cab_files.items():
                with open(path_join(backend_path, file_name), 'wb') as f:
                    f.write(content.encode('utf8'))

            final_files_paths = (path_join(backend_path, cab_file) for cab_file in chain(cab_files.iterkeys(), media_files))
            infopath_form_filepath = path_join(backend_path, "%s.xsn" % self.backend.subject)

            if sys.platform.startswith('win'):
                ddf_file_content = render_to_string("crudity/infopath/create_template/create_cab.ddf",
                                                    {'file_name': "%s.xsn" % self.backend.subject,
                                                     'backend_path':backend_path,
                                                    },
                                                    context_instance=RequestContext(request)
                                                   )

                ddf_path = path_join(backend_path, "create_cab.ddf")
                with open(ddf_path, 'wb') as f:
                    f.write(ddf_file_content)

                cabify_content = render_to_string("crudity/infopath/create_template/cabify.bat",
                                                  {'ddf_path': ddf_path},
                                                  context_instance=RequestContext(request)
                                                 )

                cabify_path = path_join(backend_path, "cabify.bat")
                with open(cabify_path, 'wb') as f:
                    f.write(cabify_content)

                subprocess.call([cabify_path])
                #clean because  .Set GenerateInf=off doesn't seems to work...
                os.unlink(path_join(settings.CREME_ROOT, "setup.inf"))
                os.unlink(path_join(settings.CREME_ROOT, "setup.rpt"))
            else:
                subprocess.call(chain(["lcab", "-qn"], final_files_paths, [infopath_form_filepath]))

            with open(infopath_form_filepath, 'rb') as f:
                for chunk in f.read(File.DEFAULT_CHUNK_SIZE):
                    yield chunk

        finally:
            if backend_path:
                shutil.rmtree(backend_path)

    def render(self):
        response =  HttpResponse(self._render(), mimetype="application/vnd.ms-infopath")
        response['Content-Disposition'] = 'attachment; filename=%s.xsn' % normalize('NFKD', unicode(CrudityBackend.normalize_subject(self.backend.subject))).encode('ascii', 'ignore')
        return response

    def _render_manifest_xsf(self, request):
        return render_to_string("crudity/infopath/create_template/manifest.xsf",
                                {'creme_namespace': self.namespace,
                                 'form_urn':        self.urn,
                                 'lang_code':       self._get_lang_code(request.LANGUAGE_CODE),
                                 'form_name':       self.backend.subject,
                                 'fields':          self.fields,
                                 'file_fields':     self.file_fields,
                                 'to':              settings.CREME_GET_EMAIL,
                                 'password':        self.backend.password
                                },
                                context_instance=RequestContext(request)
                               )

    def _render_myschema_xsd(self, request):
        return render_to_string("crudity/infopath/create_template/myschema.xsd",
                                {'creme_namespace': self.namespace,
                                 'fields':          self.fields,
                                },
                                context_instance=RequestContext(request)
                               )

    def _render_template_xml(self, request):
        return render_to_string("crudity/infopath/create_template/template.xml",
                                {'creme_namespace': self.namespace,
                                 'form_urn':        self.urn,
                                 'fields':          self.fields,
                                },
                                context_instance=RequestContext(request)
                               )

    def _render_upgrade_xsl(self, request):
        return render_to_string("crudity/infopath/create_template/upgrade.xsl",
                                {'creme_namespace': self.namespace,
                                 'fields':          self.fields,
                                },
                                context_instance=RequestContext(request)
                               )

    def _render_view_xsl(self, request):
        backend = self.backend
        return render_to_string("crudity/infopath/create_template/view1.xsl",
                                {'creme_namespace': self.namespace,
                                 'fields':          self.fields,
                                 'form_title':      u"%s %s" % (_(u"Create"), backend.model._meta.verbose_name)
                                },
                                context_instance=RequestContext(request)
                               )
