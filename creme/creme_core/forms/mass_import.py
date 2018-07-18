# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from itertools import zip_longest
import logging
from os.path import splitext

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import validators
from django.db.models import Q, ManyToManyField, BooleanField as ModelBooleanField
from django.db.models.fields import FieldDoesNotExist
from django.db.transaction import atomic
from django.forms.models import modelform_factory
from django.forms import (ValidationError, Field, BooleanField, MultipleChoiceField,
        ModelChoiceField, ModelMultipleChoiceField, IntegerField)
from django.forms.widgets import Widget, Select, HiddenInput
from django.template.defaultfilters import slugify
from django.urls import reverse_lazy as reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.documents import get_document_model

from ..backends import import_backend_registry
from ..gui.mass_import import import_form_registry
from ..models import (CremePropertyType, CremeProperty,
        RelationType, Relation, CremeEntity, EntityCredentials, FieldsConfig,
        CustomField, CustomFieldValue, CustomFieldEnumValue, MassImportJobResult)
from ..utils.meta import ModelFieldEnumerator
from ..utils.url import TemplateURLBuilder
from .base import CremeForm, CremeModelForm, FieldBlockManager, _CUSTOM_NAME
from .fields import MultiRelationEntityField, CreatorEntityField
from .widgets import UnorderedMultipleChoiceWidget, ChainedInput, SelectorList


logger = logging.getLogger(__name__)
Document = get_document_model()


def get_backend(filedata):
    filename = filedata.name
    pathname, extension = splitext(filename)
    backend = import_backend_registry.get_backend(extension.replace('.', ''))

    error_msg = ugettext(u'Error reading document, unsupported file type: {file}.')\
                        .format(file=filename) if backend is None else None

    return backend, error_msg


def get_header(filedata, has_header):
    backend, error_msg = get_backend(filedata)

    if error_msg:
        raise ValidationError(error_msg)

    header = None

    if has_header:
        try:
            # filedata.open()
            filedata.open(mode='r')  # TODO: 'mode' given by backend ?
            header = next(backend(filedata))
        except Exception as e:
            logger.exception('Error when reading doc header in clean()')
            raise ValidationError(ugettext(u'Error reading document: {error}.').format(error=e)) from e
        finally:
            filedata.close()

    return header


class UploadForm(CremeForm):
    step       = IntegerField(widget=HiddenInput)
    document   = CreatorEntityField(label=_(u'File to import'), model=Document,
                                    create_action_url=reverse('documents__create_document_from_widget'),
                                    credentials=EntityCredentials.VIEW,
                                   )
    has_header = BooleanField(label=_(u'Header present ?'), required=False,
                              help_text=_(u'Does the first line of the line contain '
                                          u'the header of the columns (eg: "Last name","First name") ?'
                                         )
                             )

    def __init__(self, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)
        self._header = None
        document_f = self.fields['document']
        document_f.user = self.user
        document_f.help_text = format_html(
            u'<ul class="help-texts">{}</ul>',
            format_html_join(u'', u'<li>{}: {}</li>',
                             ((be.verbose_name, be.help_text) for be in import_backend_registry.backends)
                            )
        )

    @property
    def header(self):
        return self._header

    def clean(self):
        # cdata = super(UploadForm, self).clean()
        cdata = super().clean()

        if not self._errors:
            self._header = get_header(cdata['document'].filedata, cdata['has_header'])

        return cdata


# Extractors (and related field/widget) for regular model's fields--------------

class Extractor:
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
        self._fk_model = subfield_model
        self._m2m = multiple

        if create_if_unfound:
            self._fk_form = modelform_factory(subfield_model, fields='__all__')  # TODO: creme_config form ??

    def extract_value(self, line):
        value = self._default_value
        err_msg = None

        if self._column_index:  # 0 -> not in csv
            line_value = line[self._column_index - 1]

            if line_value:
                if self._subfield_search:
                    data = {self._subfield_search: line_value}
                    retriever = self._fk_model.objects.filter if self._m2m else \
                                self._fk_model.objects.get

                    try:
                        value = retriever(**data)
                    except Exception as e:
                        fk_form = self._fk_form

                        if fk_form:  # Try to create the referenced instance
                            creator = fk_form(data=data)

                            if creator.is_valid():
                                creator.save()

                                value = creator.instance
                            else:
                                err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                                   u'and then build «{value}» (column {column}) on {model}. '
                                                   u'Raw error: [{raw_error}]').format(
                                                        raw_error=e,
                                                        column=self._column_index,
                                                        value=line_value,
                                                        model=self._fk_model._meta.verbose_name,
                                )
                        else:
                            err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                               u'«{value}» (column {column}) on {model}. '
                                               u'Raw error: [{raw_error}]').format(
                                                    raw_error=e,
                                                    column=self._column_index,
                                                    value=line_value,
                                                    model=self._fk_model._meta.verbose_name,
                            )
                else:
                    try:
                        value = self._value_castor(line_value)
                    except ValidationError as e:
                        err_msg = e.messages[0]  # TODO: are several messages possible ??
                    except Exception as e:
                        err_msg = str(e)

        return value, err_msg


class BaseExtractorWidget(Widget):
    def __init__(self, *args, **kwargs):
        # super(BaseExtractorWidget, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.column_select = Select()

    @property
    def choices(self):
        return self.column_select.choices

    @choices.setter
    def choices(self, choices):
        self.column_select.choices = choices


class ExtractorWidget(BaseExtractorWidget):  # TODO: rename (Regular/Base)FieldExtractorWidget ??
    template_name = 'creme_core/forms/widgets/mass-import/extractor.html'

    def __init__(self, *args, **kwargs):
        # super(ExtractorWidget, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.default_value_widget = None
        self.subfield_select = None  # TODO: rename 'subfield_choices'
        self.propose_creation = False

    def get_context(self, name, value, attrs):
        value = value or {}
        # context = super(ExtractorWidget, self).get_context(name=name, value=value, attrs=attrs)
        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']

        final_attrs = widget_cxt['attrs']
        id_attr = final_attrs['id']
        required = final_attrs.pop('required', False)

        # Column <select> ------
        try:
            selected_col = int(value.get('selected_column', -1))
        except TypeError:
            selected_col = 0

        widget_cxt['column_select'] = self.column_select.get_context(name='{}_colselect'.format(name),
                                                                     value=selected_col,
                                                                     attrs={
                                                                        'id': '{}_colselect'.format(id_attr),
                                                                        'class': 'csv_col_select',
                                                                        'required': required,
                                                                     },
                                                                    )['widget']

        # Sub-field <select> ------
        widget_cxt['subfield_choices'] = self.subfield_select
        widget_cxt['searched_subfield'] = value.get('subfield_search')
        widget_cxt['propose_creation'] = self.propose_creation
        widget_cxt['creation_checked'] = value.get('subfield_create', False)

        # Default value widget ------
        widget_cxt['default_value_widget'] = self.default_value_widget \
                                                 .get_context(name='{}_defval'.format(name),
                                                              value=value.get('default_value'),
                                                              attrs={
                                                                  'id': '{}_defval'.format(id_attr),
                                                                  'required': required,
                                                              },
                                                             )['widget']

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
            'selected_column':  get('{}_colselect'.format(name)),
            'subfield_search':  get('{}_subfield'.format(name)),
            'subfield_create':  get('{}_create'.format(name), False),
            'default_value':    self.default_value_widget
                                    .value_from_datadict(data=data, files=files, name='{}_defval'.format(name)),
        }


class ExtractorField(Field):
    widget = ExtractorWidget
    default_error_messages = {
        'invalid': _(u'Enter a valid value.'),
    }

    # TODO: default values + properties which update widget
    def __init__(self, choices, modelfield, modelform_field, *args, **kwargs):
        # super(ExtractorField, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.required = modelform_field.required
        modelform_field.required = False

        self._modelfield = modelfield
        self._user = None
        self._can_create = False  # If True and field is a FK/M2M -> the referenced model can be created

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = modelform_field
        widget.default_value_widget = modelform_field.widget

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        remote_field = self._modelfield.remote_field

        if remote_field:
            from creme.creme_config.registry import config_registry, NotRegisteredInConfig
            model = remote_field.model
            creation_perm = False
            app_name = model._meta.app_label

            try:
                config_registry.get_app(app_name).get_model_conf(model=model)
            except (KeyError, NotRegisteredInConfig):
                pass
            else:
                creation_perm = user.has_perm_to_admin(app_name)

            # TODO: we should improve this (use the Form from creme_config ?)
            # NB: we exclude BooleanField because it is certainly useless to search on it
            #     (a model with only 2 valid values could be replaced by static values)
            sf_choices = ModelFieldEnumerator(model).filter(viewable=True) \
                                                    .exclude(lambda field, deep: isinstance(field, ModelBooleanField)) \
                                                    .choices()

            widget = self.widget
            widget.subfield_select = sf_choices
            widget.propose_creation = self._can_create = creation_perm and (len(sf_choices) == 1)

    def clean(self, value):
        try:
            col_index = int(value['selected_column'])
        except TypeError as e:
            raise ValidationError(self.error_messages['invalid'], code='invalid') from e

        def_value = self._original_field.clean(value['default_value'])

        if self.required and def_value in validators.EMPTY_VALUES and not col_index:
            raise ValidationError(self.error_messages['required'], code='required')

        # TODO: check that col_index is in self._choices ???

        subfield_create = value['subfield_create']

        if not self._can_create and subfield_create:
            raise ValidationError('You can not create instances')

        extractor = Extractor(col_index, def_value, self._original_field.clean)

        subfield_search = value['subfield_search']
        if subfield_search:
            modelfield = self._modelfield
            extractor.set_subfield_search(subfield_search, modelfield.remote_field.model,
                                          multiple=isinstance(modelfield, ManyToManyField),
                                          # TODO: improve widget to disable creation check instead of hide it.
                                          create_if_unfound=subfield_create,
                                         )

        return extractor


# Extractors (and related field/widget) for entities----------------------------

class EntityExtractionCommand:
    def __init__(self, model, field_name, column_index, create):
        self.model = model
        self.field_name = field_name
        self.column_index_str = column_index
        self.create = create

    def build_column_index(self):
        "@throw TypeError"
        self.column_index = index = int(self.column_index_str)
        return index


class EntityExtractor:
    def __init__(self, extraction_cmds):
        "@params extraction_cmds: List of EntityExtractionCommands"
        self._commands = extraction_cmds

    def _extract_entity(self, line, user, command):
        index = command.column_index

        # TODO: manage credentials (linkable (& viewable ?))
        if not index:  # 0 -> not in csv
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
                    created.full_clean()  # Can raise ValidationError
                    created.save()  # TODO should we use save points for this line ?
                except Exception as e:
                    error_msg = _(u'Error while extracting value [{raw_error}]: '
                                  u'tried to retrieve and then build «{value}» on {model}').format(
                                        raw_error=e,
                                        value=value,
                                        model=model._meta.verbose_name,
                    )
                else:
                    extracted = created
            else:
                error_msg = _(u'Error while extracting value [{raw_error}]: '
                              u'tried to retrieve «{value}» on {model}').format(
                                    raw_error=e,
                                    value=value,
                                    model=model._meta.verbose_name,
                )

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


# TODO: use ul/li instead of table...
class EntityExtractorWidget(BaseExtractorWidget):
    template_name = 'creme_core/forms/widgets/mass-import/entity-extractor.html'

    def __init__(self, models_info=(), *args, **kwargs):
        # super(EntityExtractorWidget, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        # self.propose_creation = False # TODO
        self.models_info = models_info

    def _build_model_id(self, model):
        return model._meta.app_label, model.__name__.lower()

    def _build_colselect_id(self, name, model_id):
        return '{0}_{1}_{2}_colselect'.format(name, *model_id)

    def _build_create_id(self, name, model_id):
        return '{0}_{1}_{2}_create'.format(name, *model_id)

    def get_context(self, name, value, attrs):
        # context = super(EntityExtractorWidget, self).get_context(name=name, value=value, attrs=attrs)
        context = super().get_context(name=name, value=value, attrs=attrs)

        def build_selected_value(cmd):
            sel_val = 0

            if cmd:
                try:
                    sel_val = cmd.build_column_index()
                except TypeError:
                    pass

            return sel_val

        widget_cxt = context['widget']
        get_sel_context = self.column_select.get_context
        get_ct = ContentType.objects.get_for_model
        id_attr = widget_cxt['attrs']['id']
        build_ident = '{main}_{app}_{model}_colselect'.format
        widget_cxt['lines'] = lines = []

        for info, cmd in zip_longest(self.models_info, value or ()):
            ctype = get_ct(info[0])
            fmt_kwargs = {'app': ctype.app_label, 'model': ctype.model}

            lines.append(
                (ctype, cmd,
                 get_sel_context(name=build_ident(main=name, **fmt_kwargs),
                                 value=build_selected_value(cmd),
                                 attrs={'id':    build_ident(main=id_attr, **fmt_kwargs),
                                        'class': 'csv_col_select',
                                       },
                                )['widget']
                )
            )

        return context

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
    widget = EntityExtractorWidget
    default_error_messages = {
        'invalid': _(u'Enter a valid value.'),
        'nocreationperm': _(u'You are not allowed to create: %(model)s'),
    }

    # TODO: default values + properties which update widget
    def __init__(self, models_info, choices, *args, **kwargs):
        """@param model_info: Sequence of tuple (Entity class, field name)
                  Field name if used to get or create class instances.
        """
        # super(EntityExtractorField, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
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
                    raise ValidationError(self.error_messages['invalid'], code='invalid')

                if cmd.create and not can_create(cmd.model):
                    raise ValidationError(self.error_messages['nocreationperm'],
                                          params={'model': cmd.model._meta.verbose_name},
                                          code='nocreationperm',
                                         )

                one_active_command |= bool(index)
        except TypeError as e:
            raise ValidationError(self.error_messages['invalid'], code='invalid') from e

        return one_active_command

    def clean(self, value):
        one_active_command = self._clean_commands(value)

        if self.required and not one_active_command:
            raise ValidationError(self.error_messages['required'], code='required')

        return EntityExtractor(value)


# Extractors (and related field/widget) for relations---------------------------

class RelationExtractor:
    def __init__(self, column_index, rtype, subfield_search, related_model, create_if_unfound):
        self._column_index    = column_index
        self._rtype           = rtype
        self._subfield_search = str(subfield_search)
        self._related_model   = related_model
        self._related_form    = modelform_factory(related_model, fields='__all__') if create_if_unfound else None

    related_model = property(lambda self: self._related_model)

    def create_if_unfound(self):
        return self._related_form is not None

    # TODO: link credentials
    # TODO: constraint on properties for relationtypes (wait for cache in RelationType)
    def extract_value(self, line, user):
        object_entity = None
        err_msg = None
        value = line[self._column_index - 1]

        if value:
            data = {self._subfield_search: value}
            model = self._related_model

            try:
                object_entity = EntityCredentials.filter(user, model.objects.filter(**data)).first()
            except Exception as e:
                err_msg = ugettext(u'Error while extracting value to build a Relation: '
                                   u'tried to retrieve {field}=«{value}» (column {column}) on {model}. '
                                   u'Raw error: [{raw_error}]').format(
                                        raw_error=e,
                                        column=self._column_index,
                                        field=self._subfield_search,
                                        value=value,
                                        model=model._meta.verbose_name,
                )
            else:
                if object_entity is None:
                    if self._related_form:  # Try to create the referenced instance
                        data['user'] = user.id
                        creator = self._related_form(data=data)

                        if creator.is_valid():
                            object_entity = creator.save()
                        else:
                            err_msg = ugettext(u'Error while extracting value: '
                                               u'tried to build {model} with data={data} '
                                               u'(column {column}) ➔ errors={errors}').format(
                                                    model=model._meta.verbose_name,
                                                    column=self._column_index,
                                                    data=data,
                                                    errors=creator.errors,
                            )
                    else:
                        err_msg = ugettext(u'Error while extracting value to build a Relation: '
                                           u'tried to retrieve {field}=«{value}» '
                                           u'(column {column}) on {model}').format(
                                                field=self._subfield_search,
                                                column=self._column_index,
                                                value=value,
                                                model=model._meta.verbose_name,
                        )

        return (self._rtype, object_entity), err_msg


class MultiRelationsExtractor:
    def __init__(self, extractors):
        self._extractors = extractors

    def extract_value(self, line, user):
        for extractor in self._extractors:
            yield extractor.extract_value(line, user)

    def __iter__(self):
        return iter(self._extractors)


class RelationExtractorSelector(SelectorList):
    template_name = 'creme_core/forms/widgets/mass-import/relations-extractor.html'

    def __init__(self, columns=(), relation_types=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.columns = columns
        self.relation_types = relation_types
        # TODO: autocomplete ?

    def get_context(self, name, value, attrs):
        value = value or {}
        self.selector = chained_input = ChainedInput(attrs)

        # TODO: use GET args instead of using TemplateURLBuilders ?
        add = partial(chained_input.add_dselect, attrs={'auto': False, 'autocomplete': True})
        add('rtype', options=self.relation_types, label=ugettext(u'The entity'))
        add('ctype',
            options=TemplateURLBuilder(rtype_id=(TemplateURLBuilder.Word, '${rtype}'))
                                      .resolve('creme_core__ctypes_compatible_with_rtype')
           )
        add('searchfield',
            options=TemplateURLBuilder(ct_id=(TemplateURLBuilder.Int, '${ctype}'))
                                      .resolve('creme_core__entity_info_fields'),
            label=ugettext(u'which field'),
           )
        add('column', options=self.columns, label=ugettext(u'equals to'))

        # context = super(RelationExtractorSelector, self).get_context(name=name, attrs=attrs,
        #                                                              value=value.get('selectorlist'),
        #                                                             )
        context = super().get_context(name=name, attrs=attrs, value=value.get('selectorlist'))
        context['widget']['can_create_checked'] = value.get('can_create', False)

        return context

    def value_from_datadict(self, data, files, name):
        return {
            # 'selectorlist': super(RelationExtractorSelector, self)
            #                      .value_from_datadict(data=data, files=files, name=name),
            'selectorlist': super().value_from_datadict(data=data, files=files, name=name),
            'can_create':   data.get('{}_can_create'.format(name), False),
        }


class RelationExtractorField(MultiRelationEntityField):
    widget = RelationExtractorSelector
    default_error_messages = {
        'fielddoesnotexist': _(u"This field doesn't exist in this ContentType."),
        'invalidcolunm':     _(u'This column is not a valid choice.'),
    }

    def __init__(self, columns=(), *args, **kwargs):
        # super(RelationExtractorField, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.columns = columns

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        self.widget.columns = columns

    def clean(self, value):
        checked = value['can_create']
        selector_data = self.clean_json(value['selectorlist'])

        if not selector_data:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')

            return MultiRelationsExtractor([])

        if not isinstance(selector_data, list):
            raise ValidationError(self.error_messages['invalidformat'], code='invalidformat')

        clean_value = self.clean_value
        cleaned_entries = [(clean_value(entry, 'rtype',       str),
                            clean_value(entry, 'ctype',       int),
                            clean_value(entry, 'column',      int),
                            clean_value(entry, 'searchfield', str),
                           ) for entry in selector_data
                          ]
        extractors = []
        rtypes_cache = {}
        allowed_rtypes_ids = frozenset(self._get_allowed_rtypes_ids())
        allowed_columns = frozenset(c[0] for c in self._columns)

        for rtype_pk, ctype_pk, column, searchfield in cleaned_entries:
            if column not in allowed_columns:
                raise ValidationError(self.error_messages['invalidcolunm'],
                                      params={'column': column},
                                      code='invalidcolunm',
                                     )

            if rtype_pk not in allowed_rtypes_ids:
                raise ValidationError(self.error_messages['rtypenotallowed'],
                                      params={'rtype': rtype_pk, 'ctype': ctype_pk},
                                      code='rtypenotallowed',
                                     )

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = \
                self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'],
                                      params={'ctype': ctype_pk},
                                      code='ctypenotallowed',
                                     )

            try:
                ct = ContentType.objects.get_for_id(ctype_pk)
                model = ct.model_class()
                model._meta.get_field(searchfield)
            except ContentType.DoesNotExist as e:
                raise ValidationError(self.error_messages['ctypedoesnotexist'],
                                      params={'ctype': ctype_pk},
                                      code='ctypedoesnotexist',
                                     ) from e
            except FieldDoesNotExist as e:
                raise ValidationError(self.error_messages['fielddoesnotexist'],
                                      params={'field': searchfield},
                                      code='fielddoesnotexist',
                                     ) from e

            # TODO: creation creds for entity (it is done, but in the form)
            # TODO: improve widget to answer for creation only if allowed

            extractors.append(RelationExtractor(column_index=column,
                                                rtype=rtype,
                                                subfield_search=searchfield,
                                                related_model=model,
                                                create_if_unfound=checked,
                                               )
                             )

        return MultiRelationsExtractor(extractors)


# Extractors (and related field/widget) for custom fields ----------------------

class CustomFieldExtractor:
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

        if self._column_index:  # 0 -> not in csv
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
                        # TODO: improve self._value_castor avoid the direct 'return' ?
                        return (self._manage_enum(CustomFieldEnumValue.objects.create(custom_field=self._custom_field,
                                                                                      value=value,
                                                                                     ).id
                                                 ),
                                err_msg
                               )
                    else:
                        err_msg = ugettext(u'Error while extracting value: tried to retrieve '
                                           u'the choice «{value}» (column {column}). '
                                           u'Raw error: [{raw_error}]').format(
                                                raw_error=e,
                                                column=self._column_index,
                                                value=value,
                        )

                    value = None

            if not value:
                value = self._default_value
        else:
            value = self._default_value

        return self._value_castor(value), err_msg


# TODO: make a BaseFieldExtractorWidget ??
class CustomFieldExtractorWidget(ExtractorWidget):
    template_name = 'creme_core/forms/widgets/mass-import/cfield-extractor.html'

    def get_context(self, name, value, attrs):
        value = value or {}
        # context = super(CustomFieldExtractorWidget, self).get_context(name=name, value=value, attrs=attrs)
        context = super().get_context(name=name, value=value, attrs=attrs)
        context['widget']['can_create'] = value.get('can_create', False)

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
            'selected_column': get('{}_colselect'.format(name)),
            'can_create':      get('{}_create'.format(name), False),
            'default_value':   self.default_value_widget
                                   .value_from_datadict(data=data, files=files, name='{}_defval'.format(name)),
        }


# TODO: factorise
class CustomfieldExtractorField(Field):
    def __init__(self, choices, custom_field, user, *args, **kwargs):
        # super(CustomfieldExtractorField, self).__init__(widget=CustomFieldExtractorWidget,
        super().__init__(widget=CustomFieldExtractorWidget,
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
    def user(self):
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
        except TypeError as e:
            raise ValidationError(self.error_messages['invalid'], code='invalid') from e

        def_value = value['default_value']

        if def_value:
            self._original_field.clean(def_value)  # To raise ValidationError if needed
        elif self.required and not col_index:  # Should be useful while CustomFields can not be marked as required
            raise ValidationError(self.error_messages['required'], code='required')

        # TODO: check that col_index is in self._choices ???

        create_if_unfound = value['can_create']

        if not self._can_create and create_if_unfound:
            raise ValidationError('You can not create choices')

        extractor = CustomFieldExtractor(col_index, def_value, self._original_field.clean,
                                         self._custom_field, create_if_unfound,
                                        )

        return extractor

# ------------------------------------------------------------------------------


# TODO: merge with ImportForm4CremeEntity ? (no model that is not an entity is imported with csv...)
class ImportForm(CremeModelForm):
    step       = IntegerField(widget=HiddenInput)
    document   = IntegerField(widget=HiddenInput)
    has_header = BooleanField(widget=HiddenInput, required=False)
    key_fields = MultipleChoiceField(
                        label=_(u'Key fields'), required=False,
                        choices=(),
                        widget=UnorderedMultipleChoiceWidget(columntype='wide'),
                        help_text=_(u'Select at least one field if you want to use the "update" mode. '
                                    u'If an entity already exists with the same field values, it will be simply updated '
                                    u'(ie: a new entity will not be created).\n'
                                    u'But if several entities are found, a new entity is created (in order to avoid errors).'
                                   ),
                    )

    error_messages = {
        'invalid_document': _(u"This document doesn't exist or doesn't exist any more."),
        'forbidden_read': _(u"You have not the credentials to read this document."),
    }

    choices = [(0, 'Not in the file')] + [(i, 'Column {}'.format(i)) for i in range(1, 21)]  # Overloaded by factory
    header_dict = {}  # Idem

    blocks = FieldBlockManager(
        ('general', _(u'Update mode'),  ('step', 'document', 'has_header', 'key_fields',)),
        ('fields',  _(u'Field values'), '*'),
       )

    def __init__(self, *args, **kwargs):
        # super(ImportForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.import_errors = []

        get_fconf = FieldsConfig.LocalCache().get_4_model
        # TODO: exclude not extractor fields ?
        # TODO: factorise with HeaderFilter ???
        self.fields['key_fields'].choices = \
            ModelFieldEnumerator(self._meta.model, deep=1, only_leafs=False) \
                .filter(viewable=True) \
                .exclude(lambda field, deep: get_fconf(field.model).is_field_hidden(field)) \
                .choices()

    def append_error(self, err_msg):
        if err_msg:
            self.import_errors.append(str(err_msg))

    # NB: hack to bypass the model validation (see form_factory() comment)
    def _post_clean(self):
        pass

    def clean_document(self):
        document_id = self.cleaned_data['document']

        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_document'],
                                  code='invalid_document',
                                 )

        if not self.user.has_perm('creme_core.view_entity', document):
            raise ValidationError(self.error_messages['forbidden_read'],
                                  code='forbidden_read',
                                 )

        return document

    def _post_instance_creation(self, instance, line, updated):  # Overload me
        pass

    def _pre_instance_save(self, instance, line):  # Overload me
        pass

    def process(self, job):
        model_class = self._meta.model
        get_cleaned = self.cleaned_data.get

        exclude = frozenset(self._meta.exclude or ())
        regular_fields   = []  # Contains tuples (field_name, cleaned_field_value)
        extractor_fields = []  # Contains tuples (field_name, extractor)

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
        backend, error_msg = get_backend(filedata)

        if error_msg:
            raise self.Error(error_msg)

        # filedata.open()
        # TODO: mode depedns on the backend ?
        # TODO: use "with"
        filedata.open(mode='r')

        lines = backend(filedata)
        if get_cleaned('has_header'):
            # lines.next()
            next(lines)

        # Resuming
        for i in range(MassImportJobResult.objects.filter(job=job).count()):
            # lines.next()
            next(lines)

        append_error = self.append_error
        key_fields = frozenset(get_cleaned('key_fields'))
        is_empty_value = lambda s: s is None or isinstance(s, str) and not s.strip()

        for i, line in enumerate(filter(None, lines), start=1):
            job_result = MassImportJobResult(job=job, line=line)

            try:
                with atomic():
                    instance = model_class()
                    updated = False  # 'True' means: object has been updated, not created from scratch

                    extr_values = []
                    for fname, extractor in extractor_fields:
                        extr_value, err_msg = extractor.extract_value(line)

                        # TODO: Extractor.extract_value() should return a ExtractedValue
                        #       instead of a tuple (an so we could remove the ugly following line...)
                        is_empty = not extractor._column_index or is_empty_value(line[extractor._column_index - 1])
                        extr_values.append((fname, extr_value, is_empty))

                        append_error(err_msg)

                    if key_fields:
                        # We avoid using exception within 'atomic' block
                        found = model_class.objects.exclude(is_deleted=True) \
                                                   .filter(**dict((fname, extr_value)
                                                                    for fname, extr_value, __ in extr_values
                                                                        if fname in key_fields
                                                                 )
                                                          )[:2]

                        if found:
                            if len(found) == 1:
                                instance = found[0]
                                job_result.updated = updated = True
                            else:
                                append_error(ugettext(u'Several entities corresponding to the search have been found. '
                                                      u'So a new entity have been created to avoid errors.'
                                                     ),
                                            )

                    for fname, cleaned_value in regular_fields:
                        setattr(instance, fname, cleaned_value)

                    for fname, extr_value, is_empty in extr_values:
                        if updated and is_empty:
                            continue

                        setattr(instance, fname, extr_value)

                    self._pre_instance_save(instance, line)

                    instance.full_clean()
                    instance.save()

                    self._post_instance_creation(instance, line, updated)

                    for m2m in self._meta.model._meta.many_to_many:
                        extractor = get_cleaned(m2m.name)  # Can be a regular_field ????
                        if extractor:
                            # TODO: factorise
                            extr_value, err_msg = extractor.extract_value(line)
                            getattr(instance, m2m.name).set(extr_value)
                            append_error(err_msg)

                    job_result.entity = instance
                    if self.import_errors:
                        job_result.messages = self.import_errors
                    job_result.save()
            except Exception as e:
                logger.exception('Exception in Mass importing')

                try:
                    for messages in e.message_dict.values():
                        for message in messages:
                            append_error(str(message))
                except:
                    append_error(str(e))

                job_result.messages = self.import_errors
                job_result.save()

            self.import_errors[:] = ()

        filedata.close()


class ImportForm4CremeEntity(ImportForm):
    user            = ModelChoiceField(label=_(u'Owner user'), empty_label=None,
                                       queryset=get_user_model().objects.filter(is_staff=False),
                                      )
    property_types  = ModelMultipleChoiceField(label=_(u'Properties'), required=False,
                                               queryset=CremePropertyType.objects.none(),
                                              )
    fixed_relations = MultiRelationEntityField(label=_(u'Fixed relationships'),
                                               required=False, autocomplete=True,
                                              )
    dyn_relations   = RelationExtractorField(label=_(u'Relationships from the file'), required=False)

    blocks = FieldBlockManager(
        ('general',    _(u'General'),                  ('step', 'document', 'has_header', 'user', 'key_fields')),
        ('fields',     _(u'Field values'),             '*'),
        ('properties', _(u'Related properties'),       ('property_types',)),
        ('relations',  _(u'Associated relationships'), ('fixed_relations', 'dyn_relations')),
       )

    error_messages = dict(ImportForm.error_messages,
                          creation_forbidden=_(u'You are not allowed to create: %(model)s'),
                         )

    def __init__(self, *args, **kwargs):
        # super(ImportForm4CremeEntity, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        user = self.user
        fields = self.fields
        ct = ContentType.objects.get_for_model(self._meta.model)
        fields['property_types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=ct) |
                                                                             Q(subject_ctypes__isnull=True)
                                                                            )

        rtypes = RelationType.get_compatible_ones(ct)
        fields['fixed_relations'].allowed_rtypes = rtypes

        fdyn_relations = fields['dyn_relations']
        fdyn_relations.allowed_rtypes = rtypes
        fdyn_relations.columns = self.choices[1:]

        fields['user'].initial = user.id

        # TODO: in a staticmethod of CustomField ?? (see models.entity.py)
        self.cfields = cfields = CustomField.objects.filter(content_type=ct)
        get_col = self.header_dict.get
        for cfield in cfields:
            # fields[_CUSTOM_NAME % cfield.id] = CustomfieldExtractorField(
            fields[_CUSTOM_NAME.format(cfield.id)] = CustomfieldExtractorField(
                                                    self.choices, cfield, user=user,
                                                    initial={'selected_column': get_col(slugify(cfield.name), 0)},
                                                )

    def clean_dyn_relations(self):  # TODO: move this validation in RelationExtractorField.clean()
        extractors = self.cleaned_data['dyn_relations']
        can_create = self.user.has_perm_to_create

        for extractor in extractors:
            if extractor.create_if_unfound and not can_create(extractor.related_model):
                raise ValidationError(self.error_messages['creation_forbidden'],
                                      params={'model': extractor.related_model._meta.verbose_name},
                                      code='creation_forbidden',
                                     )

        return extractors

    def _post_instance_creation(self, instance, line, updated):
        cdata = self.cleaned_data
        user = instance.user

        # Custom Fields -------
        for cfield in self.cfields:
            try:
                # value, err_msg = cdata[_CUSTOM_NAME % cfield.id].extract_value(line)
                value, err_msg = cdata[_CUSTOM_NAME.format(cfield.id)].extract_value(line)
            except ValidationError as e:
                self.append_error(e.messages[0])
            else:
                if err_msg is not None:
                    self.append_error(err_msg)
                elif value is not None and value != u'':
                    CustomFieldValue.save_values_for_entities(cfield, [instance], value)

        # Properties -----
        create_prop = partial(CremeProperty.objects.create if not updated else
                              CremeProperty.objects.get_or_create,
                              creme_entity=instance,
                             )

        for prop_type in cdata['property_types']:
            create_prop(type=prop_type)

        # Relationships -----
        create_relation = partial(Relation.objects.create, user=user, subject_entity=instance) \
                          if not updated else \
                          partial(Relation.objects.get_or_create, subject_entity=instance,
                                  defaults={'user': user},
                                 )

        for rtype, entity in cdata['fixed_relations']:
            create_relation(type=rtype, object_entity=entity)

        for (rtype, entity), err_msg in cdata['dyn_relations'].extract_value(line, user):
            if err_msg:
                self.append_error(err_msg)
            elif entity is not None:
                create_relation(type=rtype, object_entity=entity)


def extractorfield_factory(modelfield, header_dict, choices):
    formfield = modelfield.formfield()

    if not formfield:  # Happens for crementity_ptr (OneToOneField)
        return None

    selected_column = header_dict.get(slugify(modelfield.verbose_name))
    if selected_column is None:
        selected_column = header_dict.get(slugify(modelfield.name), 0)

    if formfield.required:
        # We remove the '----' choice when it is useless
        # TODO: improve (hook) the regular behaviour of ModelChoiceField ??
        options = getattr(formfield, 'choices', None)

        if options is not None and len(options) > 1:
            formfield.empty_label = None
            formfield.choices = options  # we force the refreshing of widget's choices

    return ExtractorField(choices, modelfield, formfield,
                          label=modelfield.verbose_name,
                          initial={'selected_column': selected_column,
                                   'default_value':   formfield.initial,
                                  },
                         )


# NB: we use ModelForm to get the all the django machinery to build a form from a model
#     bit we need to avoid the model validation, because we are are not building a true
#    'self.instance', but a set of instances ; we just use the regular form validation.
def form_factory(ct, header):
    choices = [(0, _(u'Not in the file'))]
    header_dict = {}

    if header:
        fstring = ugettext(u'Column {index} - {name}')

        for i, col_name in enumerate(header):
            i += 1
            choices.append((i, fstring.format(index=i, name=col_name)))
            header_dict[slugify(col_name)] = i
    else:
        fstring = ugettext(u'Column {}')
        choices.extend((i, fstring.format(i)) for i in range(1, 21))

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
                                                            ),
                                 )
    modelform.choices = choices
    modelform.header_dict = header_dict

    return modelform
