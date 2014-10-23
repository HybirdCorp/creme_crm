# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from future_builtins import filter
from functools import partial
from itertools import chain, izip_longest
import logging
from os.path import splitext

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core import validators
from django.db.models import Q, ManyToManyField, BooleanField as ModelBooleanField
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import modelform_factory
from django.forms import (ValidationError, Field, BooleanField, MultipleChoiceField,
        ModelChoiceField, ModelMultipleChoiceField, IntegerField)
from django.forms.widgets import SelectMultiple, HiddenInput
from django.forms.util import flatatt
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.utils.html import escape

from creme.creme_core.forms.base import _CUSTOM_NAME
from creme.creme_core.gui.list_view_import import import_form_registry
from creme.creme_core.models import (CremePropertyType, CremeProperty,
        RelationType, Relation, CremeEntity, EntityCredentials,
        CustomField, CustomFieldValue,
        #CustomFieldEnum
        CustomFieldEnumValue,
        )
from creme.creme_core.registry import import_backend_registry
from creme.creme_core.utils.collections import LimitedList
#from creme.creme_core.views.entity import EXCLUDED_FIELDS

from creme.documents.models import Document

from ..utils.meta import ModelFieldEnumerator
from .base import CremeForm, CremeModelForm, FieldBlockManager
from .fields import MultiRelationEntityField, CreatorEntityField
from .widgets import UnorderedMultipleChoiceWidget, ChainedInput, SelectorList
from .validators import validate_linkable_entities


logger = logging.getLogger(__name__)


class UploadForm(CremeForm):
    step       = IntegerField(widget=HiddenInput)
    document   = CreatorEntityField(label=_(u'File to import'), model=Document,
                                    create_action_url='/documents/quickforms/from_widget/document/csv/add/1',
                                   )
    has_header = BooleanField(label=_(u'Header present ?'), required=False,
                              help_text=_(u'Does the first line of the line contain the header of the columns (eg: "Last name","First name") ?')
                             )

    def __init__(self, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)
        self._header = None
        document = self.fields['document']
        document.user = self.user
        document.help_text = mark_safe("<ul>%s</ul>" %
                                       u''.join(("<li>%s: %s</li>" %
                                                (unicode(be.verbose_name), unicode(be.help_text))
                                                for be in import_backend_registry.iterbackends())))

    @property
    def header(self):
        return self._header

    def clean(self):
        cleaned_data = super(UploadForm, self).clean()

        if not self._errors:
            document = cleaned_data['document']
            filedata = document.filedata
            filename = filedata.name

            if not self.user.has_perm_to_view(document):
                raise ValidationError(ugettext("You have not the credentials to read this document."))

            pathname, extension = splitext(filename)
            backend = import_backend_registry.get_backend(extension.replace('.', ''))
            if backend is None:
                raise ValidationError(ugettext("Error reading document, unsupported file type: %s.") % filename)

            if cleaned_data['has_header']:
                try:
                    filedata.open()
                    self._header = backend(filedata).next()
                except Exception as e:
                    raise ValidationError(ugettext("Error reading document: %s.") % e)
                finally:
                    filedata.close()

        return cleaned_data


#Extractors (and related field/widget) for regular model's fields-------------

class Extractor(object):
    def __init__(self, column_index, default_value, value_castor):
        self._column_index  = column_index
        self._default_value = default_value
        self._value_castor  = value_castor
        self._subfield_search = None
        self._fk_model = None
        self._m2m = None
        self._fk_form = None

    def set_subfield_search(self, subfield_search, subfield_model, multiple, create_if_unfound):
        self._subfield_search = str(subfield_search)
        self._fk_model  = subfield_model
        self._m2m = multiple

        if create_if_unfound:
            self._fk_form = modelform_factory(subfield_model) #TODO: creme_config form ??

    def extract_value(self, line):
        value = None
        err_msg = None

        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            #if self._subfield_search:
            if self._subfield_search and value:
                data = {self._subfield_search: value}

                try:
                    retriever = self._fk_model.objects.filter if self._m2m else \
                                self._fk_model.objects.get
                    return retriever(**data), err_msg #TODO: improve self._value_castor avoid the direct 'return' ?
                except Exception as e:
                    fk_form = self._fk_form

                    if fk_form: #try to create the referenced instance
                        creator = fk_form(data=data)

                        if creator.is_valid():
                            creator.save()
                            return creator.instance, err_msg #TODO: improve self._value_castor avoid the direct 'return' ?
                        else:
                            err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                                'and then build "%(value)s" (column %(column)s) on %(model)s. '
                                                'Raw error: [%(raw_error)s]') % {
                                                        'raw_error': e,
                                                        'column':    self._column_index,
                                                        'value':     value,
                                                        'model':     self._fk_model._meta.verbose_name,
                                                    }
                    else:
                        err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                            '"%(value)s" (column %(column)s) on %(model)s. '
                                            'Raw error: [%(raw_error)s]') % {
                                                    'raw_error': e,
                                                    'column':    self._column_index,
                                                    'value':     value,
                                                    'model':     self._fk_model._meta.verbose_name,
                                                }

                    value = None

                if not value:
                    value = self._default_value

                return value, err_msg

            #if not value:
                #value = self._default_value
        #else:
            #value = self._default_value

        #return self._value_castor(value), err_msg
        return (self._value_castor(value) if value else self._default_value), err_msg


class ExtractorWidget(SelectMultiple):
    def __init__(self, *args, **kwargs):
        super(ExtractorWidget, self).__init__(*args, **kwargs)
        self.default_value_widget = None
        self.subfield_select = None
        self.propose_creation = False

    def _render_select(self, name, choices, sel_val, attrs=None):
        output = ['<select %s>' % flatatt(self.build_attrs(attrs, name=name))]

        output.extend(u'<option value="%s" %s>%s</option>' % (
                            opt_value,
                            (u'selected="selected"' if sel_val == opt_value else u''),
                            escape(opt_label)
                        ) for opt_value, opt_label in choices
                     )

        output.append('</select>')

        return u'\n'.join(output)

    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        attrs = self.build_attrs(attrs, name=name)
        output = [u'<table %s><tbody><tr><td>' % flatatt(attrs)]

        out_append = output.append
        rselect    = self._render_select

        try:
            sel_val = int(value.get('selected_column', -1))
        except TypeError:
            sel_val = 0

        out_append(rselect("%s_colselect" % name,
                           choices=chain(self.choices, choices),
                           sel_val=sel_val,
                           attrs={'class': 'csv_col_select'}
                          )
                  )

        if self.subfield_select:
            hide_select = (len(self.subfield_select) == 1) #the <select> is annoying if there is only one option

            out_append(u"""</td>
                           <td class="csv_subfields_select">%(label)s %(select)s %(check)s
                            <script type="text/javascript">
                                $(document).ready(function() {
                                    creme.forms.toImportField('%(id)s');
                                });
                            </script>""" % {
                          'label':  ugettext(u'Search by:') if not hide_select else '',
                          'select': rselect("%s_subfield" % name, choices=self.subfield_select,
                                            sel_val=value.get('subfield_search'),
                                            attrs={'hidden': 'True'} if hide_select else None
                                           ),
                          'check':  '' if not self.propose_creation else
                                    '&nbsp;%s <input type="checkbox" name="%s_create" %s>' % (
                                           ugettext(u'Create if not found ?'),
                                           name,
                                           'checked' if value.get('subfield_create') else '',
                                        ),
                          'id':     attrs['id'],
                        })

        out_append(u'</td><td>&nbsp;%s:%s</td></tr></tbody></table>' % (
                        ugettext(u"Default value"),
                        self.default_value_widget.render("%s_defval" % name, value.get('default_value')),
                    )
                  )

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {'selected_column':  get("%s_colselect" % name),
                'subfield_search':  get("%s_subfield" % name),
                'subfield_create':  get("%s_create" % name, False),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name)
               }


class ExtractorField(Field):
    #default_error_messages = {
    #}

    def __init__(self, choices, modelfield, modelform_field, *args, **kwargs):
        super(ExtractorField, self).__init__(widget=ExtractorWidget, *args, **kwargs)
        self.required = modelform_field.required
        modelform_field.required = False

        self._modelfield = modelfield
        self._user = None
        self._can_create = False #if True and field is a FK/M2M -> the referenced model can be created

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = modelform_field
        widget.default_value_widget = modelform_field.widget

    @property
    def user(self, user):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        rel = self._modelfield.rel

        if rel:
            from creme.creme_config.registry import config_registry, NotRegisteredInConfig
            model = rel.to
            creation_perm = False
            app_name = model._meta.app_label

            try:
                config_registry.get_app(app_name) \
                               .get_model_conf(ContentType.objects.get_for_model(model).id)
            except (KeyError, NotRegisteredInConfig):
                pass
            else:
                creation_perm = user.has_perm_to_admin(app_name)

            #sf_choices = ModelFieldEnumerator(model).filter(viewable=True).choices()
            #TODO: we should improve this (use the Form from creme_config ?)
            #NB: we exclude BooleanField because it is certainly useless to search on it
            #    (a model with only 2 valid values could be replaced by static values)
            sf_choices = ModelFieldEnumerator(model).filter(viewable=True) \
                                                    .exclude(lambda field, deep: isinstance(field, ModelBooleanField)) \
                                                    .choices()

            widget = self.widget
            widget.subfield_select = sf_choices
            widget.propose_creation = self._can_create = creation_perm and (len(sf_choices) == 1)

    def clean(self, value):
        try:
            col_index = int(value['selected_column'])
        except TypeError:
            raise ValidationError(self.error_messages['invalid'])

        #def_value = value['default_value']
        def_value = self._original_field.clean(value['default_value'])

        #if def_value:
            #self._original_field.clean(def_value) #to raise ValidationError if needed
        #elif self.required and not col_index:
        if self.required and def_value in validators.EMPTY_VALUES and not col_index:
            raise ValidationError(self.error_messages['required'])

        #TODO: check that col_index is in self._choices ???

        subfield_create = value['subfield_create']

        if not self._can_create and subfield_create:
            raise ValidationError('You can not create instances')

        extractor = Extractor(col_index, def_value, self._original_field.clean)

        subfield_search = value['subfield_search']
        if subfield_search:
            modelfield = self._modelfield
            extractor.set_subfield_search(subfield_search, modelfield.rel.to,
                                          multiple=isinstance(modelfield, ManyToManyField),
                                          create_if_unfound=subfield_create, #TODO: improve widget to disable creation check instead of hide it.
                                         )

        return extractor

#Extractors (and related field/widget) for entities---------------------------

class EntityExtractionCommand(object):
    def __init__(self, model, field_name, column_index, create):
        self.model = model
        self.field_name = field_name
        self.column_index_str = column_index
        self.create = create

    def build_column_index(self):
        "@throw TypeError"
        self.column_index = index = int(self.column_index_str)
        return index


class EntityExtractor(object):
    def __init__(self, extraction_cmds):
        "@params extraction_cmds List of EntityExtractionCommands"
        self._commands = extraction_cmds

    def _extract_entity(self, line, user, command):
        index = command.column_index

        #TODO: manage credentials (linkable (& viewable ?))
        if not index: #0 -> not in csv
            return None, None

        value = line[index - 1]
        if not value:
            return None, None

        model = command.model
        error_msg = None
        extracted = None
        kwargs = {command.field_name: value}

        try:
            extracted = model.objects.get(**kwargs)
        except Exception as e:
            if command.create:
                created = model(user=user, **kwargs)

                try:
                    created.full_clean() #can raise ValidationError
                    created.save() #TODO should we use save points for this line ?
                except Exception as e:
                    error_msg = _(u'Error while extracting value [%(raw_error)s]: '
                                   'tried to retrieve and then build "%(value)s" on %(model)s') % {
                                        'raw_error': e,
                                        'value': value,
                                        'model': model._meta.verbose_name,
                                    }
                else:
                    extracted = created
            else:
                error_msg = _(u'Error while extracting value [%(raw_error)s]: '
                               'tried to retrieve "%(value)s" on %(model)s') % {
                                    'raw_error': e,
                                    'value':     value,
                                    'model':     model._meta.verbose_name,
                                }

        return extracted, error_msg

    def extract_value(self, line, user):
        extracted = None
        extract_entity = partial(self._extract_entity, line, user)
        err_msg = None
        error_parts = []

        for cmd in self._commands:
            extracted, error_part = extract_entity(cmd)

            if extracted is not None:
                break

            if error_part:
                error_parts.append(error_part)
        else:
            err_msg = u'\n'.join(error_parts)

        return extracted, err_msg


#TODO: use ul/li instead of table...
class EntityExtractorWidget(ExtractorWidget):
    def __init__(self, *args, **kwargs):
        super(EntityExtractorWidget, self).__init__(*args, **kwargs)
        #self.propose_creation = False #TODO

    def _build_model_id(self, model):
        return model._meta.app_label, model.__name__.lower()

    def _build_colselect_id(self, name, model_id):
        return "{0}_{1}_{2}_colselect".format(name, *model_id)

    def _build_create_id(self, name, model_id):
        return "{0}_{1}_{2}_create".format(name, *model_id)

    def _render_column_select(self, name, cmd, choices, model_id):
        sel_val = 0

        if cmd:
            try:
                sel_val = cmd.build_column_index()
            except TypeError:
                pass

        return self._render_select(self._build_colselect_id(name, model_id),
                                   choices=chain(self.choices, choices),
                                   sel_val=sel_val,
                                   attrs={'class': 'csv_col_select'},
                                  )

    def _render_line(self, output, name, cmd, choices, model):
        append = output.append
        model_id = self._build_model_id(model)

        append(u'<tr><td>%s: </td><td>' % model._meta.verbose_name)
        append(self._render_column_select(name, cmd, choices, model_id))
        append(u'</td><td>&nbsp;%(label)s <input type="checkbox" name="%(name)s" %(checked)s></td></tr>' % {
                            'label':   _(u'Create if not found ?'),
                            'name':    self._build_create_id(name, model_id),
                            'checked': 'checked' if cmd and cmd.create else '',
                        }
                     )

    def render(self, name, value, attrs=None, choices=()):
        output = [u'<table %s><tbody>' % flatatt(self.build_attrs(attrs, name=name))]
        render_line = self._render_line

        for info, cmd in izip_longest(self.models_info, value or ()):
            render_line(output, name, cmd, choices, info[0])

        output.append(u'</tbody></table>')

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        build_model_id = self._build_model_id
        build_colselect_id = partial(self._build_colselect_id, name)
        build_create_id = partial(self._build_create_id, name)

        value = []
        for model, field_name in self.models_info:
            model_id = build_model_id(model)
            value.append(EntityExtractionCommand(
                            model, field_name,
                            column_index=get(build_colselect_id(model_id)),
                            create=get(build_create_id(model_id), False),
                           )
                        )

        return value


class EntityExtractorField(Field):
    default_error_messages = {
        'nocreationperm': _(u'You are not allowed to create: %s'),
    }

    def __init__(self, models_info, choices, *args, **kwargs):
        """@param model_info Sequence of tuple (Entity class, field name)
                             Field name if used to get or create class instances.
        """
        super(EntityExtractorField, self).__init__(widget=EntityExtractorWidget, *args, **kwargs)
        self.models_info = models_info
        self.allowed_indexes = {c[0] for c in choices}

        widget = self.widget
        widget.choices = choices
        widget.models_info = models_info

    def _clean_commands(self, value):
        one_active_command = False
        allowed_indexes = self.allowed_indexes
        can_create = self.user.has_perm_to_create

        try:
            for cmd in value:
                index = cmd.build_column_index()

                if not index in allowed_indexes:
                    raise ValidationError(self.error_messages['invalid'])

                if cmd.create and not can_create(cmd.model):
                    raise ValidationError(self.error_messages['nocreationperm'] %
                                            cmd.model._meta.verbose_name
                                         )

                one_active_command |= bool(index)
        except TypeError:
            raise ValidationError(self.error_messages['invalid'])

        return one_active_command

    def clean(self, value):
        one_active_command = self._clean_commands(value)

        if self.required and not one_active_command:
            raise ValidationError(self.error_messages['required'])

        return EntityExtractor(value)


#Extractors (and related field/widget) for relations----------------------------

class RelationExtractor(object):
    def __init__(self, column_index, rtype, subfield_search, related_model, create_if_unfound):
        self._column_index    = column_index
        self._rtype           = rtype
        self._subfield_search = str(subfield_search)
        self._related_model   = related_model
        self._related_form    = modelform_factory(related_model) if create_if_unfound else None

    related_model = property(lambda self: self._related_model)

    def create_if_unfound(self):
        return self._related_form is not None

    #TODO: link credentials
    #TODO: constraint on properties for relationtypes (wait for cache in RelationType)
    def extract_value(self, line, user):
        object_entity = None
        err_msg = None
        value = line[self._column_index - 1]

        if value:
            data = {self._subfield_search: value}
            model = self._related_model

            try:
                object_entities = EntityCredentials.filter(user, model.objects.filter(**data))[:1]
            except Exception as e:
                err_msg = ugettext('Error while extracting value to build a Relation: '
                                   'tried to retrieve %(field)s="%(value)s" (column %(column)s) on %(model)s. '
                                   'Raw error: [%(raw_error)s]') % {
                                        'raw_error': e,
                                        'column':    self._column_index,
                                        'field':     self._subfield_search,
                                        'value':     value,
                                        'model':     model._meta.verbose_name,
                                    }
            else:
                if object_entities:
                    object_entity = object_entities[0]
                elif self._related_form: #try to create the referenced instance
                    data['user'] = user.id
                    creator = self._related_form(data=data)

                    if creator.is_valid():
                        object_entity = creator.save()
                    else:
                        err_msg = ugettext('Error while extracting value: '
                                           'tried to build %(model)s with data=%(data)s '
                                           '(column %(column)s) => errors=%(errors)s') % {
                                                    'model':  model._meta.verbose_name,
                                                    'column': self._column_index,
                                                    'data':   data,
                                                    'errors': creator.errors
                                                }
                else:
                    err_msg = ugettext('Error while extracting value to build a Relation: '
                                       'tried to retrieve %(field)s="%(value)s" '
                                       '(column %(column)s) on %(model)s') % {
                                            'field': self._subfield_search,
                                            'column': self._column_index,
                                            'value': value,
                                            'model': model._meta.verbose_name,
                                        }

        return (self._rtype, object_entity), err_msg


class MultiRelationsExtractor(object):
    def __init__(self, extractors):
        self._extractors = extractors

    def extract_value(self, line, user):
        for extractor in self._extractors:
            yield extractor.extract_value(line, user)

    def __iter__(self):
        return iter(self._extractors)


class RelationExtractorSelector(SelectorList):
    def __init__(self, columns, relation_types, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        add = partial(chained_input.add_dselect, attrs=attrs)
        add("rtype",       options=relation_types, label=ugettext(u"The entity"))
        add("ctype",       options='/creme_core/relation/type/${rtype}/content_types/json')
        add("searchfield", options='/creme_core/entity/get_info_fields/${ctype}/json',
            label=ugettext(u"which field")
           )
        add("column",      options=columns, label=ugettext(u"equals to"))

        super(RelationExtractorSelector, self).__init__(chained_input)

    def render(self, name, value, attrs=None):
        value = value or {}

        return mark_safe('<input type="checkbox" name="%(name)s_can_create" %(checked)s/>%(label)s'
                         '%(super)s' % {
                        'name':    name,
                        'checked': 'checked' if value.get('can_create') else '',
                        'label':   ugettext(u'Create entities if they are not found ? (only fields followed by [CREATION] allows you to create, if they exist)'),
                        'super':   super(RelationExtractorSelector, self).render(name, value.get('selectorlist'), attrs),
                    })

    def value_from_datadict(self, data, files, name):
        return {'selectorlist': super(RelationExtractorSelector, self).value_from_datadict(data, files, name),
                'can_create':   data.get('%s_can_create' % name, False),
               }


class RelationExtractorField(MultiRelationEntityField):
    default_error_messages = {
        'fielddoesnotexist': _(u"This field doesn't exist in this ContentType."),
        'invalidcolunm':     _(u"This column is not a valid choice."),
    }

    def __init__(self, columns=(), *args, **kwargs):
        self._columns = columns
        super(RelationExtractorField, self).__init__(*args, **kwargs)

    def _create_widget(self):
        return RelationExtractorSelector(columns=self._columns,
                                         relation_types=self._get_options,
                                        )

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        self._build_widget()

    def clean(self, value):
        checked = value['can_create']
        selector_data = self.clean_json(value['selectorlist'])

        if not selector_data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return MultiRelationsExtractor([])

        if not isinstance(selector_data, list):
            raise ValidationError(self.error_messages['invalidformat'])

        clean_value = self.clean_value
        cleaned_entries = [(clean_value(entry, 'rtype',       str),
                            clean_value(entry, 'ctype',       int),
                            clean_value(entry, 'column',      int),
                            clean_value(entry, 'searchfield', str)
                           ) for entry in selector_data
                          ]

        extractors = []
        rtypes_cache = {}
        allowed_rtypes_ids = frozenset(self._get_allowed_rtypes_ids())

#        need_property_validation = False
        allowed_columns = frozenset(c[0] for c in self._columns)

        for rtype_pk, ctype_pk, column, searchfield in cleaned_entries:
            if column not in allowed_columns:
                raise ValidationError(self.error_messages['invalidcolunm'],
                                      params={'column': column}
                                     )

            if rtype_pk not in allowed_rtypes_ids:
                raise ValidationError(self.error_messages['rtypenotallowed'],
                                      params={'rtype': rtype_pk, 'ctype': ctype_pk}
                                     )

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = \
                self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

#            if rtype_allowed_properties:
#                need_property_validation = True

            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'],
                                      params={'ctype': ctype_pk}
                                     )

            try:
                ct = ContentType.objects.get_for_id(ctype_pk)
                model = ct.model_class()
                model._meta.get_field_by_name(searchfield)
            except ContentType.DoesNotExist:
                raise ValidationError(self.error_messages['ctypedoesnotexist'],
                                      params={'ctype': ctype_pk}
                                     )
            except FieldDoesNotExist:
                raise ValidationError(self.error_messages['fielddoesnotexist'],
                                      params={'field': searchfield}
                                     )

            #TODO: creation creds for entity (it is done, but in the form)
            #TODO: improve widget to answer for creation only if allowed

            extractors.append(RelationExtractor(column_index=column,
                                                rtype=rtype,
                                                subfield_search=searchfield,
                                                related_model=model,
                                                create_if_unfound=checked,
                                               )
                             )

        return MultiRelationsExtractor(extractors)

#Extractors (and related field/widget) for custom fields -----------------------

class CustomFieldExtractor(object):
    def __init__(self, column_index, default_value, value_castor, custom_field, create_if_unfound):
        self._column_index  = column_index
        self._default_value = default_value
        self._value_castor  = value_castor

        self._custom_field = custom_field
        self._create_if_unfound = create_if_unfound

        ftype = self._custom_field.field_type
        if ftype == CustomField.ENUM:
            self._manage_enum = lambda x: x
        elif ftype == CustomField.MULTI_ENUM:
            self._manage_enum = lambda x: [x]
        else:
            self._manage_enum = None

    def extract_value(self, line):
        err_msg = None

        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            if value and self._manage_enum:
                try:
                    return (self._manage_enum(CustomFieldEnumValue.objects.get(custom_field=self._custom_field,
                                                                               value__iexact=value,
                                                                              ).id
                                             ),
                            err_msg
                           )
                except CustomFieldEnumValue.DoesNotExist as e:
                    if self._create_if_unfound:
                        #TODO: improve self._value_castor avoid the direct 'return' ?
                        return (self._manage_enum(CustomFieldEnumValue.objects.create(custom_field=self._custom_field,
                                                                                      value=value,
                                                                                     ).id
                                                 ),
                                err_msg
                               )
                    else:
                        err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                            'the choice "%(value)s" (column %(column)s). '
                                            'Raw error: [%(raw_error)s]') % {
                                                        'raw_error': e,
                                                        'column':    self._column_index,
                                                        'value':     value,
                                                    }

                    value = None

            if not value:
                value = self._default_value
        else:
            value = self._default_value

        return self._value_castor(value), err_msg

#TODO: make a BaseExtractorWidget ??
class CustomFieldExtractorWidget(ExtractorWidget):
    def render(self, name, value, attrs=None, choices=()):
        get = (value or {}).get
        output = [u'<table %s><tbody><tr><td>' % flatatt(self.build_attrs(attrs, name=name))]
        out_append = output.append

        try:
            sel_val = int(get('selected_column', -1))
        except TypeError:
            sel_val = 0

        out_append(self._render_select('%s_colselect' % name,
                                       choices=chain(self.choices, choices),
                                       sel_val=sel_val,
                                       attrs={'class': 'csv_col_select'},
                                      )
                  )

        if self.propose_creation:
            create_id = '%s_create' % name
            out_append(u'</td><td>&nbsp;<label for="%(id)s">%(label)s:<input type="checkbox" name="%(id)s" %(checked)s></label>' % {
                            'id': create_id,
                            'label': ugettext('Create if not found ?'),
                            'checked': 'checked' if get('can_create') else '',
                        }
                      )

        defval_id = '%s_defval' % name
        out_append(u'</td><td>&nbsp;<label for="%s">%s:%s</label></td></tr></tbody></table>' % (
                        defval_id,
                        ugettext('Default value'),
                        self.default_value_widget.render(defval_id, get('default_value')),
                    )
                  )

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {'selected_column': get('%s_colselect' % name),
                'can_create':      get('%s_create' % name, False),
                'default_value':   self.default_value_widget.value_from_datadict(data, files, '%s_defval' % name),
               }

#TODO: factorise
class CustomfieldExtractorField(Field):
    def __init__(self, choices, custom_field, user, *args, **kwargs):
        super(CustomfieldExtractorField, self).__init__(widget=CustomFieldExtractorWidget,
                                                        label=custom_field.name,
                                                        *args, **kwargs
                                                       )

        self._custom_field = custom_field
        formfield = custom_field.get_formfield(None)
        self.required = formfield.required
        self.user = user

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = formfield
        widget.default_value_widget = formfield.widget

    @property
    def user(self, user):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = (
                self._custom_field.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM)
                and user.has_perm_to_admin('creme_config')
            )

    def clean(self, value):
        try:
            col_index = int(value['selected_column'])
        except TypeError:
            raise ValidationError(self.error_messages['invalid'])

        def_value = value['default_value']

        if def_value:
            self._original_field.clean(def_value) #to raise ValidationError if needed
        elif self.required and not col_index: #should be useful while CustomFields can not be marked as required
            raise ValidationError(self.error_messages['required'])

        #TODO: check that col_index is in self._choices ???

        create_if_unfound = value['can_create']

        if not self._can_create and create_if_unfound:
            raise ValidationError('You can not create choices')

        extractor = CustomFieldExtractor(col_index, def_value, self._original_field.clean,
                                         self._custom_field, create_if_unfound,
                                        )

        return extractor

#-------------------------------------------------------------------------------


class LVImportError(object):
    __slots__ = ('line', 'message', 'instance')

    def __init__(self, line, message, instance=None):
        self.line = line
        self.message = message
        self.instance = instance

    def __repr__(self):
        from django.utils.encoding import smart_str

        return 'LVImportError(line=%s, message=%s, instance=%s)' % (
                    self.line, smart_str(self.message), self.instance,
                )


#TODO: merge with ImportForm4CremeEntity ? (no model that is not an entity is imported with csv...)
class ImportForm(CremeModelForm):
    step       = IntegerField(widget=HiddenInput)
    document   = IntegerField(widget=HiddenInput)
    has_header = BooleanField(widget=HiddenInput, required=False)
    key_fields = MultipleChoiceField(label=_(u'Key fields'), required=False,
                                     choices=(),
                                     widget=UnorderedMultipleChoiceWidget(columntype='wide'),
                                     help_text=_('Select at least one field if you want to use the "update" mode. '
                                                 'If an entity already exists with the same field values, it will be simply updated '
                                                 '(ie: a new entity will not be created).\n'
                                                 'But if several entities are found, a new entity is created (in order to avoid errors).'
                                                ),
                                    )

    choices = [(0, 'Not in the file')] + [(i, 'Column %s' % i) for i in xrange(1, 21)] #overload by factory
    header_dict = {} #idem

    blocks = FieldBlockManager(
        ('general', _(u'Update mode'),  ('step', 'document', 'has_header', 'key_fields',)),
        ('fields',  _(u'Field values'), '*'),
       )

    def __init__(self, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        self.import_errors = LimitedList(50) # contains LVImportErrors
        self.imported_objects_count = 0  # TODO: properties ??
        self.updated_objects_count = 0
        self.lines_count = 0

        #TODO: exclude not extractor fields ?
        #TODO: factorise with HeaderFilter ???
        self.fields['key_fields'].choices = \
            ModelFieldEnumerator(self._meta.model, deep=1, only_leafs=False) \
                .filter(viewable=True) \
                .choices()

    def append_error(self, line, err_msg, instance=None):
        if err_msg:
            self.import_errors.append(LVImportError(line, err_msg, instance))

    #NB: hack to bypass the model validation (see form_factory() comment)
    def _post_clean(self):
        pass

    def clean_document(self):
        document_id = self.cleaned_data['document']

        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(ugettext("This document doesn't exist or doesn't exist any more."))

        if not self.user.has_perm('creme_core.view_entity', document):
            raise ValidationError(ugettext("You have not the credentials to read this document."))

        return document

    def _post_instance_creation(self, instance, line): # overload me
        pass

    def _pre_instance_save(self, instance, line): # overload me
        pass

    def save(self):
        model_class = self._meta.model
        get_cleaned = self.cleaned_data.get
        append_error = self.append_error

        exclude = frozenset(self._meta.exclude or ())
        regular_fields   = [] #contains tuples (field_name, cleaned_field_value)
        extractor_fields = [] #contains tuples (field_name, extractor)

        for field in model_class._meta.fields:
            fname = field.name

            if fname in exclude:
                continue

            cleaned = get_cleaned(fname)
            if not cleaned:
                continue

            good_fields = extractor_fields if isinstance(cleaned, Extractor) else regular_fields
            good_fields.append((fname, cleaned))

        filedata = self.cleaned_data['document'].filedata
        pathname, extension = splitext(filedata.name)
        file_extension = extension.replace('.', '')

        filedata.open()
        backend = import_backend_registry.get_backend(file_extension)
        if backend is None:
            verbose_error = "Error reading document, unsupported file type: %s." % file_extension
            append_error(filedata.name, verbose_error)
            filedata.close()
            return

        lines = backend(filedata)
        if get_cleaned('has_header'):
            lines.next()

        key_fields = frozenset(get_cleaned('key_fields'))
        i = 0

        for i, line in enumerate(filter(None, lines), start=1):
            try:
                instance = model_class()
                updated = False #'True' means: object has been updated, not created from scratch

                extr_values = []
                for fname, extractor in extractor_fields:
                    extr_value, err_msg = extractor.extract_value(line)
                    extr_values.append((fname, extr_value))
                    append_error(line, err_msg, instance)

                if key_fields:
                    try:
                        instance = model_class.objects.get(**dict((fname, extr_value) 
                                                                    for fname, extr_value in extr_values
                                                                        if fname in key_fields
                                                                 )
                                                          )
                        updated = True
                    except model_class.MultipleObjectsReturned:
                        append_error(line,
                                     _('Several entities corresponding to the research have been found. '
                                       'So a new entity have been created to avoid errors.'
                                      ),
                                     instance
                                    )
                    except model_class.DoesNotExist:
                        pass
                    except Exception as e: #should not happen
                        append_error(line, str(e), instance)

                for fname, cleaned_value in regular_fields:
                    setattr(instance, fname, cleaned_value)

                for fname, extr_value in extr_values:
                    setattr(instance, fname, extr_value)

                self._pre_instance_save(instance, line)

                instance.full_clean()
                instance.save()

                if updated:
                    self.updated_objects_count += 1
                else:
                    self.imported_objects_count += 1

                self._post_instance_creation(instance, line)

                for m2m in self._meta.model._meta.many_to_many:
                    extractor = get_cleaned(m2m.name)  # can be a regular_field ????
                    if extractor:
                        #TODO: factorise
                        extr_value, err_msg = extractor.extract_value(line)
                        setattr(instance, m2m.name, extr_value)
                        append_error(line, err_msg, instance)
            except Exception as e:
                #logger.info('Exception in CSV importing: %s (%s)', e, type(e))
                logger.exception('Exception in CSV importing')

                try:
                    for messages in e.message_dict.itervalues():
                        for message in messages:
                            append_error(line, unicode(message), instance)
                except:
                    append_error(line, str(e), instance)

        self.lines_count = i

        filedata.close()


class ImportForm4CremeEntity(ImportForm):
    user            = ModelChoiceField(label=_('Owner user'), queryset=User.objects.filter(is_staff=False), empty_label=None) #label=_('User')
    property_types  = ModelMultipleChoiceField(label=_(u'Properties'), required=False,
                                               queryset=CremePropertyType.objects.none(),
                                               widget=UnorderedMultipleChoiceWidget)
    fixed_relations = MultiRelationEntityField(label=_(u'Fixed relationships'), required=False)
    dyn_relations   = RelationExtractorField(label=_(u'Relationships from CSV'), required=False)

    blocks = FieldBlockManager(
        ('general',    _(u'General'),                  ('step', 'document', 'has_header', 'user', 'key_fields')),
        ('fields',     _(u'Field values'),             '*'),
        ('properties', _(u'Related properties'),       ('property_types',)),
        ('relations',  _(u'Associated relationships'), ('fixed_relations', 'dyn_relations')),
       )

    #columns4dynrelations = [(i, 'Colunmn %s' % i) for i in xrange(1, 21)]

    #class Meta:
        #exclude = ('is_deleted', 'is_actived')

    def __init__(self, *args, **kwargs):
        super(ImportForm4CremeEntity, self).__init__(*args, **kwargs)

        fields = self.fields
        ct     = ContentType.objects.get_for_model(self._meta.model)

        fields['property_types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=ct) |
                                                                             Q(subject_ctypes__isnull=True)
                                                                            )

        rtypes = RelationType.get_compatible_ones(ct)
        fields['fixed_relations'].allowed_rtypes = rtypes

        fdyn_relations = fields['dyn_relations']
        fdyn_relations.allowed_rtypes = rtypes
        #fdyn_relations.columns = self.columns4dynrelations
        fdyn_relations.columns = self.choices[1:]

        fields['user'].initial = self.user.id

        #TODO: in a staticmethod of CustomField ?? (see models.entity.py)
        self.cfields = cfields = CustomField.objects.filter(content_type=ct)
        get_col = self.header_dict.get
        for cfield in cfields:
            fields[_CUSTOM_NAME % cfield.id] = CustomfieldExtractorField(
                                                    self.choices, cfield, user=self.user,
                                                    initial={'selected_column': get_col(slugify(cfield.name), 0)},
                                                )

    def clean_fixed_relations(self):
        relations = self.cleaned_data['fixed_relations']
        user = self.user

        #TODO: self._check_duplicates(relations, user) #see RelationCreateForm
        validate_linkable_entities([entity for rt_id, entity in relations], user)

        return relations

    def clean_dyn_relations(self): #TODO: move this validation in RelationExtractorField.clean()
        extractors = self.cleaned_data['dyn_relations']
        can_create = self.user.has_perm_to_create

        for extractor in extractors:
            if extractor.create_if_unfound and not can_create(extractor.related_model):
                raise ValidationError(_('You are not allowed to create: %s') %
                                        extractor.related_model._meta.verbose_name
                                     )

        return extractors

    def _post_instance_creation(self, instance, line):
        cdata = self.cleaned_data
        user = instance.user

        for cfield in self.cfields:
            try:
                value, err_msg = cdata[_CUSTOM_NAME % cfield.id].extract_value(line)
            except ValidationError as e:
                self.append_error(line, e.messages[0], instance)
            else:
                if err_msg is not None:
                    self.append_error(line, err_msg, instance)
                elif value is not None:
                    CustomFieldValue.save_values_for_entities(cfield, [instance], value)

        for prop_type in cdata['property_types']:
            CremeProperty(type=prop_type, creme_entity=instance).save()

        create_relation = partial(Relation.objects.create, user=user, subject_entity=instance)

        for rtype, entity in cdata['fixed_relations']:
            create_relation(type=rtype, object_entity=entity)

        for (rtype, entity), err_msg in cdata['dyn_relations'].extract_value(line, user):
            if err_msg:
                self.append_error(line, err_msg, instance)
            else:
                create_relation(type=rtype, object_entity=entity)


def extractorfield_factory(modelfield, header_dict, choices):
    formfield = modelfield.formfield()

    if not formfield: # happens for crementity_ptr (OneToOneField)
        return None

    selected_column = header_dict.get(slugify(modelfield.verbose_name))
    if selected_column is None:
        selected_column = header_dict.get(slugify(modelfield.name), 0)


    if formfield.required:
        # We remove the '----' choice when it is useless
        #TODO: improve (hook) the regular behaviour of ModelChoiceField ??
        options = getattr(formfield, 'choices', None)

        if options is not None and len(options) > 1:
            formfield.empty_label = None
            formfield.choices = options #we force the refreshing of widget's choices

    return ExtractorField(choices, modelfield, formfield,
                          label=modelfield.verbose_name,
                          initial={'selected_column': selected_column,
                                   'default_value':   formfield.initial,
                                  },
                         )


#NB: we use ModelForm to get the all the django machinery to build a form from a model
#    bit we need to avoid the model validation, because we are are not building a true
#    'self.instance', but a set of instances ; we just use the regular form validation.
def form_factory(ct, header):
    choices = [(0, _('Not in the file'))]
    header_dict = {}

    if header:
        fstring = ugettext(u'Column %(index)s - %(name)s')

        for i, col_name in enumerate(header):
            i += 1
            choices.append((i, fstring % {'index': i, 'name': col_name}))
            header_dict[slugify(col_name)] = i
    else:
        fstring = ugettext(u'Column %i')
        choices.extend((i, fstring % i) for i in xrange(1, 21))

    model_class = ct.model_class()
    customform_factory = import_form_registry.get(ct)

    if customform_factory:
        base_form_class = customform_factory(header_dict, choices)
    elif issubclass(model_class, CremeEntity):
        base_form_class = ImportForm4CremeEntity
    else:
        base_form_class = ImportForm

    modelform = modelform_factory(model_class, form=base_form_class,
                                  formfield_callback=partial(extractorfield_factory,
                                                             header_dict=header_dict,
                                                             choices=choices,
                                                            )
                                 )
    #modelform.columns4dynrelations = choices[1:]
    modelform.choices = choices
    modelform.header_dict = header_dict

    return modelform
