# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Field, FieldDoesNotExist, BooleanField, DateField
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext_lazy as _

from ..models import CremeEntity, RelationType, CustomField
from ..models import fields as core_fields
from ..models.fields import DatePeriodField
from ..utils.collections import ClassKeyedMap
from ..utils.db import populate_related
from ..utils.meta import FieldInfo
from .function_field import FunctionFieldDecimal, FunctionFieldResultsList


logger = logging.getLogger(__name__)
MULTILINE_FIELDS = (
    models.TextField, core_fields.UnsafeHTMLField, models.ManyToManyField,
)
FIELDS_DATA_TYPES = ClassKeyedMap([
    (DateField,                   'date'),
    (models.TimeField,            'time'),
    (models.DateTimeField,        'datetime'),

    (models.IntegerField,         'integer'),

    (models.TextField,            'text'),
    (models.EmailField,           'email'),

    (core_fields.PhoneField,      'phone'),
    (core_fields.DurationField,   'duration'),
    (core_fields.DatePeriod,      'period'),
    (core_fields.ColorField,      'color'),
    (core_fields.UnsafeHTMLField, 'html'),
    (core_fields.MoneyField,      'html'),
])


class EntityCellsRegistry:
    __slots__ = ('_cell_classes', )

    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._cell_classes = {}

    def __call__(self, cls):
        if self._cell_classes.setdefault(cls.type_id, cls) is not cls:
            raise self.RegistrationError("Duplicated Cell id: {}".format(cls.id))

        return cls

    def build_cells_from_dicts(self, model, dicts):
        "@return tuple(list_of_cells, errors) 'errors' is a boolean"
        cells = []
        errors = False

        try:
            for dict_cell in dicts:
                try:
                    cell = self._cell_classes[dict_cell['type']].build(model, dict_cell['value'])

                    if cell is not None:
                        cells.append(cell)
                    else:
                        errors = True
                except Exception as e:
                    logger.warning('EntityCellsRegistry: %s, %s', e.__class__, e)
                    errors = True
        except Exception as e:
            logger.warning('EntityCellsRegistry: %s, %s', e.__class__, e)
            errors = True

        return cells, errors

CELLS_MAP = EntityCellsRegistry()


class EntityCell:
    """Represents a value accessor ; it's a kind of super field. It can
    retrieve a value store in entities (of the same type).
    This values can be (see child classes) :
     - regular fields (in the django model way).
     - custom field (see models.CustomField).
     - function fields (see core.FunctionField).
     - other entities linked by a Relation (of a given RelationType)
     - ...
    """
    type_id = None  # Used for register ; overload in child classes (string type)

    _listview_css_class = None
    _header_listview_css_class = None

    def __init__(self, model, value='', title=u'Title', has_a_filter=False,
                 editable=False, sortable=False,
                 is_hidden=False, filter_string='',
                ):
        self._model = model
        self.value = value
        self.title = title
        self.has_a_filter = has_a_filter # TODO: refactor list view templatetags
        self.editable = editable # TODO: still useful ???
        self.sortable = sortable
        self.is_hidden = is_hidden
        self.filter_string = filter_string # TODO: remove from public interface when quick search has been refactored

    def __repr__(self):
        return u"<EntityCell(type={}, value='{}')>".format(self.type_id, self.value)

    def __str__(self):
        return self.title

    def _get_field_class(self):
        return Field

    def _get_listview_css_class(self, attr_name):
        from ..gui.field_printers import field_printers_registry

        listview_css_class = getattr(self, attr_name)

        if listview_css_class is None:
            registry_getter = getattr(field_printers_registry, 'get{}_for_field'.format(attr_name))
            listview_css_class = registry_getter(self._get_field_class())
            setattr(self, attr_name, listview_css_class)

        return listview_css_class

    @property
    def data_type(self):
        return FIELDS_DATA_TYPES[self._get_field_class()]

    @property
    def model(self):
        return self._model

    @property
    def key(self):
        "Return an ID that should be unique in a EntityCell set"
        return '{}-{}'.format(self.type_id, self.value)

    @property
    def listview_css_class(self):
        return self._get_listview_css_class('_listview_css_class')

    @property
    def header_listview_css_class(self):
        return self._get_listview_css_class('_header_listview_css_class')

    @property
    def is_multiline(self):
        return issubclass(self._get_field_class(), MULTILINE_FIELDS)

    @staticmethod
    def populate_entities(cells, entities, user):
        pass

    # TODO: factorise render_* => like FunctionField, result that can be html, csv...
    def render_html(self, entity, user):
        raise NotImplementedError

    def render_csv(self, entity, user):
        raise NotImplementedError

    def to_dict(self):
        return {'type': self.type_id, 'value': self.value}


# @CELLS_MAP TODO
class EntityCellActions(EntityCell):
    type_id = 'actions'

    # def __init__(self):
    def __init__(self, model):
        super(EntityCellActions, self).__init__(model=model,
                                                value='entity_actions',
                                                title=_(u'Actions'),
                                               )

    # def render_html(self, entity, user): TODO


@CELLS_MAP
class EntityCellRegularField(EntityCell):
    type_id = 'regular_field'

    def __init__(self, model, name, field_info, is_hidden=False):
        "Use build() instead of using this constructor directly."
        # self._model = model
        self._field_info = field_info
        self._printer_html = self._printer_csv = None

        field = field_info[0]
        has_a_filter = True
        sortable = True
        pattern = '{}__icontains'

        if len(field_info) > 1:
            field = field_info[-1]  # The sub-field is considered as the main field

        if isinstance(field, DateField):
            pattern = '{}__range'  # TODO: quick search overload this, to use gte/lte when it is needed
        elif isinstance(field, BooleanField):
            pattern = '{}__creme-boolean'
        elif isinstance(field, DatePeriodField):
            has_a_filter = False
            sortable = False
        elif field.is_relation:
            if not field.related_model:  # TODO: test
                has_a_filter = False
                sortable = False
            else:
                pattern = '{}__header_filter_search_field__icontains' \
                          if issubclass(field.remote_field.model, CremeEntity) else '{}'  # TODO '%s__exact' ?

        if any(f.many_to_many or f.one_to_many for f in field_info):
            sortable = False

        super(EntityCellRegularField, self).__init__(model=model,
                                                     value=name,
                                                     title=field_info.verbose_name,
                                                     has_a_filter=has_a_filter,
                                                     editable=True,
                                                     sortable=sortable,
                                                     is_hidden=is_hidden,
                                                     filter_string=pattern.format(name) if has_a_filter else '',
                                                    )

    @staticmethod
    def build(model, name, is_hidden=False):
        """ Helper function to build EntityCellRegularField instances.

        @param model: Class inheriting django.db.models.Model.
        @param name: String representing a 'chain' of fields; eg: 'book__author__name'.
        @param is_hidden: Boolean. See EntityCell.is_hidden.
        @return: An instance of EntityCellRegularField, or None (if an error occurred).
        """
        try:
            field_info = FieldInfo(model, name)
        except FieldDoesNotExist as e:
            logger.warning('EntityCellRegularField(): problem with field "%s" ("%s")', name, e)
            return None

        return EntityCellRegularField(model, name, field_info, is_hidden)

    @property
    def field_info(self):
        """ Getter for attribute 'field_info'.

        @return: An instance of creme_core.utils.meta.FieldInfo.
        """
        return self._field_info

    @property
    def is_multiline(self):
        return any(isinstance(f, MULTILINE_FIELDS) for f in self._field_info)

    # @property
    # def model(self):
    #     return self._model

    def _get_field_class(self):
        return self._field_info[-1].__class__

    @staticmethod
    def populate_entities(cells, entities, user):
        populate_related(entities, [cell.value for cell in cells])

    def render_html(self, entity, user):
        printer = self._printer_html

        if printer is None:
            from ..gui.field_printers import field_printers_registry

            self._printer_html = printer = \
                 field_printers_registry.build_field_printer(entity.__class__, self.value, output='html')

        return printer(entity, user)

    def render_csv(self, entity, user):
        printer = self._printer_csv

        if printer is None:
            from ..gui.field_printers import field_printers_registry

            self._printer_csv = printer = \
                field_printers_registry.build_field_printer(entity.__class__, self.value, output='csv')

        return printer(entity, user)


@CELLS_MAP
class EntityCellCustomField(EntityCell):
    type_id = 'custom_field'

    _CF_PATTERNS = {
            CustomField.BOOL:       '{}__value__creme-boolean',
            CustomField.DATETIME:   '{}__value__range',  # TODO: quick search overload this, to use gte/lte when it is needed
            CustomField.ENUM:       '{}__value__exact',
            CustomField.MULTI_ENUM: '{}__value__exact',
        }
    _CF_CSS = {
            CustomField.DATETIME:   models.DateTimeField,
            CustomField.INT:        models.PositiveIntegerField,
            CustomField.FLOAT:      models.DecimalField,
            CustomField.BOOL:       BooleanField,
            CustomField.ENUM:       models.ForeignKey,
            CustomField.MULTI_ENUM: models.ManyToManyField,
        }

    def __init__(self, customfield):
        self._customfield = customfield
        pattern = self._CF_PATTERNS.get(customfield.field_type, '{}__value__icontains')

        super(EntityCellCustomField, self).__init__(model=customfield.content_type.model_class(),
                                                    value=str(customfield.id),
                                                    title=customfield.name,
                                                    has_a_filter=True,
                                                    editable=False,  # TODO: make it editable
                                                    sortable=False,  # TODO: make it sortable ?
                                                    is_hidden=False,
                                                    filter_string=pattern.format(customfield.get_value_class()
                                                                                            .get_related_name()
                                                                                ),
                                                   )

    @staticmethod
    def build(model, customfield_id):
        ct = ContentType.objects.get_for_model(model)

        try:
            cfield = CustomField.objects.get(content_type=ct, id=customfield_id)
        except CustomField.DoesNotExist:
            logger.warning('EntityCellCustomField: custom field "%s" does not exist', customfield_id)
            return None

        return EntityCellCustomField(cfield)
 
    @property
    def custom_field(self):
        return self._customfield

    def _get_field_class(self):
        return self._CF_CSS.get(self._customfield.field_type, Field)

    @staticmethod
    def populate_entities(cells, entities, user):
        CremeEntity.populate_custom_values(entities, [cell.custom_field for cell in cells])  # NB: not itervalues()

    def render_html(self, entity, user):
        from django.utils.html import escape
        return escape(self.render_csv(entity, user))

    def render_csv(self, entity, user):
        value = entity.get_custom_value(self.custom_field)
        return value if value is not None else ''


@CELLS_MAP
class EntityCellFunctionField(EntityCell):
    type_id = 'function_field'

    _FUNFIELD_CSS = {  # TODO: ClassKeyedMap ?
        FunctionFieldDecimal: models.DecimalField,
    }

    # def __init__(self, func_field):
    def __init__(self, model, func_field):
        self._functionfield = func_field

        super(EntityCellFunctionField, self).__init__(model=model,
                                                      value=func_field.name,
                                                      title=str(func_field.verbose_name),
                                                      has_a_filter=func_field.has_filter,
                                                      is_hidden=func_field.is_hidden,
                                                     )

    @staticmethod
    def build(model, func_field_name):
        func_field = model.function_fields.get(func_field_name)

        if func_field is None:
            logger.warning('EntityCellFunctionField: function field "%s" does not exist', func_field_name)
            return None

        return EntityCellFunctionField(model=model, func_field=func_field)

    @property
    def function_field(self):
        return self._functionfield

    def _get_field_class(self):
        return self._FUNFIELD_CSS.get(self._functionfield.result_type, Field)

    @property
    def is_multiline(self):
        return issubclass(self._functionfield.result_type, FunctionFieldResultsList)

    @staticmethod
    def populate_entities(cells, entities, user):
        for cell in cells:
            cell.function_field.populate_entities(entities, user)

    def render_html(self, entity, user):
        return self.function_field(entity, user).for_html()

    def render_csv(self, entity, user):
        return self.function_field(entity, user).for_csv()


@CELLS_MAP
class EntityCellRelation(EntityCell):
    type_id = 'relation'

    # def __init__(self, rtype, is_hidden=False):
    def __init__(self, model, rtype, is_hidden=False):
        self._rtype = rtype
        super(EntityCellRelation, self).__init__(model=model,
                                                 value=str(rtype.id),
                                                 title=rtype.predicate,
                                                 has_a_filter=True,
                                                 is_hidden=is_hidden,
                                                )

    @staticmethod
    def build(model, rtype_id, is_hidden=False):  # TODO: store 'model' in instance
        try:
            rtype = RelationType.objects.get(pk=rtype_id)
        except RelationType.DoesNotExist:
            logger.warning('EntityCellRelation: relation type "%s" does not exist', rtype_id)
            return None

        return EntityCellRelation(model=model, rtype=rtype, is_hidden=is_hidden)

    @property
    def is_multiline(self):
        return True

    @property
    def relation_type(self):
        return self._rtype

    @staticmethod
    def populate_entities(cells, entities, user):
        CremeEntity.populate_relations(entities, [cell.relation_type.id for cell in cells])

    def render_html(self, entity, user):
        from ..templatetags.creme_widgets import widget_entity_hyperlink

        related_entities = entity.get_related_entities(self.value, True)

        if not related_entities:
            return u''

        if len(related_entities) == 1:
            return widget_entity_hyperlink(related_entities[0], user)

        return format_html(u'<ul>{}</ul>',
                           format_html_join(
                               '', u'<li>{}</li>',
                               ([widget_entity_hyperlink(e, user)] for e in related_entities)
                           )
                          )

    def render_csv(self, entity, user):
        has_perm = user.has_perm_to_view
        return u'/'.join(str(o)
                            for o in entity.get_related_entities(self.value, True)
                                if has_perm(o)
                        )


# @CELLS_MAP TODO ??
class EntityCellVolatile(EntityCell):
    type_id = 'volatile'

    # def __init__(self, value, title, render_func, is_hidden=False):
    def __init__(self, model, value, title, render_func, is_hidden=False):
        self._render_func = render_func
        super(EntityCellVolatile, self).__init__(model=model,
                                                 value=value,
                                                 title=title,
                                                 has_a_filter=True,  # TODO: ??
                                                 is_hidden=is_hidden,
                                                )

    def render_html(self, entity, user):
        return self._render_func(entity)
