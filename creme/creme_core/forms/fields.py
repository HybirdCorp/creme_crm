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

from collections import defaultdict
from itertools import chain
from logging import debug

from django.forms import Field, CharField, MultipleChoiceField, ChoiceField, ModelChoiceField, DateField, TimeField, DateTimeField
from django.forms.util import ValidationError
from django.forms.widgets import Textarea
from django.forms.fields import EMPTY_VALUES, MultiValueField
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import loads as jsonloads
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType
from django.core.validators import validate_email

from creme_core.models import RelationType, CremeEntity, Relation
from creme_core.utils import creme_entity_content_types
from creme_core.utils.queries import get_q_from_dict
from creme_core.utils.date_range import date_range_registry
from creme_core.forms.widgets import CTEntitySelector, SelectorList, RelationSelector, ListViewWidget, ListEditionWidget, CalendarWidget, TimeWidget, DateRangeWidget
from creme_core.constants import REL_SUB_RELATED_TO, REL_SUB_HAS


__all__ = ('MultiGenericEntityField', 'GenericEntityField',
           'MultiRelationEntityField', 'RelationEntityField',
           'CremeEntityField', 'MultiCremeEntityField',
           'ListEditionField',
           'AjaxChoiceField', 'AjaxMultipleChoiceField', 'AjaxModelChoiceField',
           'CremeTimeField', 'CremeDateField', 'CremeDateTimeField',
           'DateRangeField',)


class JSONField(CharField):
    default_error_messages = {
        'invalidformat': _(u'Invalid format'),
    }

    def __init(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    def clean_value(self, data, name, type):
        if not data:
            raise ValidationError(self.error_messages['invalidformat'])

        if not isinstance(data, dict):
            raise ValidationError(self.error_messages['invalidformat'])

        value = data.get(name)

        # value can be "False" if a boolean value is expected.
        if value is None:
            raise ValidationError(self.error_messages['invalidformat'])

        if isinstance(value, type):
            return value

        try:
            return type(value)
        except:
            raise ValidationError(self.error_messages['invalidformat'])

    def clean_json(self, value):
        if not value:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        try:
            data = jsonloads(value)
        except:
            raise ValidationError(self.error_messages['invalidformat'])

        return data

    def format_json(self, value):
        return JSONEncoder().encode(value)

    def from_python(self, value):
        return self.format_json(value)

    def clean(self, value):
        return self.clean_json(value)

    def _create_widget(self):
        pass

    def _build_widget(self):
        self.widget = self._create_widget()
        #TODO : wait for django 1.2 and new widget api to remove this hack
        self.widget.from_python = lambda v: self.from_python(v)


class GenericEntityField(JSONField):
    default_error_messages = {
        'ctypenotallowed' : _(u"This content type is not allowed."),
        'doesnotexist' : _(u"This entity doesn't exist."),
    }

    def __init__(self, models=None, *args, **kwargs):
        super(GenericEntityField, self).__init__(models, *args, **kwargs)
        self.allowed_models = models if models else list()
        self._build_widget()

    def _create_widget(self):
        return CTEntitySelector(self._get_ctypes_options(self.get_ctypes()))

    #TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        if isinstance(value, CremeEntity):
            ctype = value.entity_type_id
            pk = value.id
        else:
            ctype = value['ctype']
            pk = value['entity']

        return self.format_json({'ctype': ctype, 'entity': pk})

    def clean(self, value):
        data = self.clean_json(value)

        if data is not None and not isinstance(data, dict):
            raise ValidationError(self.error_messages['invalidformat'])

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        return self.clean_entity(self.clean_value(data, 'ctype', int), self.clean_value(data, 'entity', int))

    def clean_entity(self, ctype_pk, entity_pk):
        ctype = self.clean_ctype(ctype_pk)
        model = ctype.model_class()

        try:
            entity = model.objects.get(pk=entity_pk)
        except model.DoesNotExist:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'])

        return entity

    def clean_ctype(self, ctype_pk):
        # check ctype in allowed ones
        for ct in (ct for ct in self.get_ctypes() if ct.pk == ctype_pk):
            return ct

        raise ValidationError(self.error_messages['ctypenotallowed'])

    def clean_rtype(self, rtype_pk):
        # is relation type allowed
        if rtype_pk not in self.allowed_rtypes:
            raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype':rtype_pk})

        try:
            return RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype':rtype_pk})

    def _get_ctypes_options(self, ctypes):
        return ((ctype.pk, unicode(ctype)) for ctype in ctypes)

    def get_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        return [get_ct(model) for model in self.allowed_models] if self.allowed_models else list(creme_entity_content_types())

    def set_allowed_models(self, models=None):
        self.allowed_models = models or []
        self._build_widget()


#TODO: Add a q_filter, see utilization in EntityEmailForm
class MultiGenericEntityField(GenericEntityField):
    def __init__(self, models=None, *args, **kwargs):
        super(MultiGenericEntityField, self).__init__(models, *args, **kwargs)
        # TODO : wait for django 1.2 and new widget api to remove this hack

    def _create_widget(self):
        return SelectorList(CTEntitySelector(self._get_ctypes_options(self.get_ctypes()), multiple=True))

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        return self.format_json([entry if not isinstance(entry, CremeEntity) else {'ctype': entry.entity_type_id, 'entity': entry.id}
                                    for entry in value
                                ]
                               )

    def clean(self, value):
        data = self.clean_json(value)

        if data is not None and not isinstance(data, list):
            raise ValidationError(self.error_messages['invalidformat'])

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return []

        entities_map = defaultdict(list)
        clean_value = self.clean_value

        # TODO : the entities order can be lost, see for refactor.
        # build a dictionnary of entity pks by content type (ignore invalid entries)
        for entry in data:
            try:
                entities_map[clean_value(entry, 'ctype', int)].append(clean_value(entry, 'entity', int))
            except Exception, e:
                raise ValidationError(self.error_messages['invalidformat'])

        entities = []

        # build the list of entities (ignore invalid entries)
        for ct_id, entity_pks in entities_map.iteritems():
            ctype = self.clean_ctype(ct_id)
            ctype_entities = dict((entity.pk, entity) for entity in ctype.model_class().objects.filter(pk__in=entity_pks))

            if not all(entity_pk in ctype_entities for entity_pk in entity_pks):
                raise ValidationError(self.error_messages['doesnotexist'])

            entities.extend(ctype_entities.itervalues())

        return entities

        #return CremeEntity.objects.filter(pk__in=[entry['entity'] for entry in data if entry['entity'] != 'null'])


class RelationEntityField(JSONField):
    default_error_messages = {
        'rtypedoesnotexist' : _(u"This relation type doesn't exist."),
        'rtypenotallowed' : _(u"This relation type cause constraint error."),
        'ctypenotallowed' : _(u"This content type cause constraint error with relation type."),
        'doesnotexist' : _(u"This entity doesn't exist."),
        'nopropertymatch' : _(u"This entity has no property that matches relation type constraints")
    }

    def __init__(self, allowed_rtypes=(REL_SUB_RELATED_TO, REL_SUB_HAS), *args, **kwargs):
        super(RelationEntityField, self).__init__(*args, **kwargs)
        self._allowed_rtypes = frozenset(allowed_rtypes)
        self._build_widget()

    def _create_widget(self):
        return RelationSelector(self._get_options(self._get_allowed_rtypes_objects()),
                                '/creme_core/relation/predicate/${rtype}/content_types/json')

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        rtype, entity = value
        relation = {'rtype': rtype.pk, 'ctype': entity.entity_type, 'entity': entity.pk}

        return self.format_json(relation)

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        clean_value = self.clean_value
        rtype_pk  = clean_value(data, 'rtype', str)
        ctype_pk  = clean_value(data, 'ctype', int)
        entity_pk = clean_value(data, 'entity', int)

        rtype = self.clean_rtype(rtype_pk)
        self.validate_ctype_constraints(rtype, ctype_pk)

        entity = self.clean_entity(ctype_pk, entity_pk)
        self.validate_properties_constraints(rtype, entity)

        return (rtype, entity)

    def validate_ctype_constraints(self, rtype, ctype_pk):
        rtype_ctypes = rtype.object_ctypes.values_list('pk', flat=True)

        # is relation type accepts content type
        if rtype_ctypes and ctype_pk not in rtype_ctypes:
            raise ValidationError(self.error_messages['ctypenotallowed'], params={'ctype': ctype_pk})

    def validate_properties_constraints(self, rtype, entity):
        rtype_properties = frozenset(rtype.object_properties.values_list('id', flat=True))

        if rtype_properties and not any(p.type_id in rtype_properties for p in entity.get_properties()):
            raise ValidationError(self.error_messages['nopropertymatch'])

    def clean_rtype(self, rtype_pk):
        # is relation type allowed
        if rtype_pk not in self._allowed_rtypes:
            raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype': rtype_pk})

        try:
            return RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype': rtype_pk})

    def clean_entity(self, ctype_pk, entity_pk):
        ctype = ContentType.objects.get_for_id(ctype_pk)
        model = ctype.model_class()

        try:
            entity = model.objects.get(pk=entity_pk)
        except model.DoesNotExist:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'], params={'ctype': ctype_pk, 'entity': entity_pk})

        return entity

    def _get_options(self, models):
        return ((model.pk, unicode(model)) for model in models)

    def _get_allowed_rtypes_objects(self):
        return RelationType.objects.filter(id__in=self._allowed_rtypes) if self._allowed_rtypes else RelationType.objects.all()

    def _set_allowed_rtypes(self, allowed=(REL_SUB_RELATED_TO, REL_SUB_HAS)):
        self._allowed_rtypes = frozenset(allowed)
        self._build_widget()

    allowed_rtypes = property(lambda self: self._allowed_rtypes, _set_allowed_rtypes); del _set_allowed_rtypes


class MultiRelationEntityField(RelationEntityField):
#    def __init__(self, allowed_rtypes=(REL_SUB_RELATED_TO, REL_SUB_HAS), *args, **kwargs):
#        super(MultiRelationEntityField, self).__init__(allowed_rtypes, *args, **kwargs)
#        self.widget = SelectorList(self.widget)

    def _create_widget(self):
        return SelectorList(RelationSelector(self._get_options(self._get_allowed_rtypes_objects()),
                                             '/creme_core/relation/predicate/${rtype}/content_types/json',
                                             multiple=True))

    #TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        #TODO: use list comprehension
        entities = []

        for rtype, entity in value:
            entities.append({'rtype': rtype.pk, 'ctype': entity.entity_type, 'entity': entity.pk})

        return self.format_json(entities)

    def _build_rtype_cache(self, rtype_pk):
        try:
            rtype = RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype': rtype_pk})

        rtype_allowed_ctypes     = frozenset(ct.pk for ct in rtype.object_ctypes.all())
        rtype_allowed_properties = frozenset(rtype.object_properties.values_list('id', flat=True))

        return (rtype, rtype_allowed_ctypes, rtype_allowed_properties)

    def _build_ctype_cache(self, ctype_pk):
        try:
            ctype = ContentType.objects.get_for_id(ctype_pk)
        except ContentType.DoesNotExist:
            raise ValidationError(self.error_messages['ctypedoesnotexist'], params={'ctype': ctype_pk})

        return (ctype, [])

    def _get_cache(self, entries, key, build_func):
        cache = entries.get(key)

        if not cache:
            cache = build_func(key)
            entries[key] = cache

        return cache

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return []

        if not isinstance(data, list):
            raise ValidationError(self.error_messages['invalidformat'])

        clean_value = self.clean_value

        cleaned_entries = [(clean_value(entry, 'rtype', str),
                            clean_value(entry, 'ctype', int),
                            clean_value(entry, 'entity', int)) for entry in data]

        rtypes_cache = {}
        ctypes_cache = {}

        need_property_validation = False

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            # check if relation type is allowed
            if rtype_pk not in self.allowed_rtypes:
                raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype': rtype_pk, 'ctype': ctype_pk})

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

            if rtype_allowed_properties:
                need_property_validation = True

            # check if content type is allowed by relation type
            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'], params={'ctype':ctype_pk})

            ctype, ctype_entity_pks = self._get_cache(ctypes_cache, ctype_pk, self._build_ctype_cache)
            ctype_entity_pks.append(entity_pk)

        entities_cache = {}

        # build real entity cache and check both entity id exists and in correct content type
        for ctype, entity_pks in ctypes_cache.values():
            ctype_entities = dict((entity.pk, entity) for entity in ctype.model_class().objects.filter(pk__in=entity_pks))

            if not all(entity_pk in ctype_entities for entity_pk in entity_pks):
                raise ValidationError(self.error_messages['doesnotexist'])

            entities_cache.update(ctype_entities)

        relations = []

        # build cache for validation of properties constraint between relationtypes and entities
        if need_property_validation:
            CremeEntity.populate_properties(entities_cache.values())

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            rtype, rtype_allowed_ctypes, rtype_allowed_properties = rtypes_cache.get(rtype_pk)
            entity = entities_cache.get(entity_pk)

            if rtype_allowed_properties and not any(p.type_id in rtype_allowed_properties for p in entity.get_properties()):
                raise ValidationError(self.error_messages['nopropertymatch'])

            relations.append((rtype, entity))

        if not relations:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        return relations


class _CommaMultiValueField(CharField): #TODO: Charfield and not Field ??!! #TODO2: Remove ?
    """
        An input with comma (or anything) separated values
    """
    default_error_messages = {
    }

    def __init__(self, separator=',', *args, **kwargs):
        self.separator = separator
        super(_CommaMultiValueField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        if value:
            return [val for val in value.split(self.separator) if val]

        return []


class _EntityField(Field):
    """
        Base class for CremeEntityField and MultiCremeEntityField,
        not really usable elsewhere avoid using it
    """
    widget = ListViewWidget
    default_error_messages = {
        'invalid_choice': _(u"Select a valid choice. %(value)s is not an available choice."),
    }

    def __init__(self, model=None, q_filter=None, separator=',', *args, **kwargs):
        super(_EntityField, self).__init__(*args, **kwargs)
        self.model     = model
        self.q_filter  = q_filter
        self.o2m       = None
        self.separator = separator

    def _set_model(self, model):
        self._model = self.widget.model = model

    model = property(lambda self: self._model, _set_model); del _set_model

    def _set_q_filter(self, q_filter):
        self._q_filter = self.widget.q_filter = q_filter

    q_filter = property(lambda self: self._q_filter, _set_q_filter); del _set_q_filter

    def _set_o2m(self, o2m):
        self._o2m = self.widget.o2m = o2m

    o2m = property(lambda self: self._o2m, _set_o2m); del _set_o2m

    def _set_separator(self, separator):
        self._separator = self.widget.separator = separator

    separator = property(lambda self: self._separator, _set_separator); del _set_separator

    def clean(self, value):
        value = super(_EntityField, self).clean(value)

        if not value:
            return None

        if isinstance(value, basestring) and self.separator in value:#In case of the widget doesn't make a 'good clean'
            value = [v for v in value.split(self.separator) if v]

        try:
            clean_ids = map(int, value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

        return clean_ids


class CremeEntityField(_EntityField):
    """
         An input with comma (or anything) separated primary keys
         clean method return a model instance
    """
    default_error_messages = {
        'doesnotexist' : _(u"This entity doesn't exist."),
    }

    def __init__(self, model=CremeEntity, q_filter=None, *args, **kwargs):
        super(CremeEntityField, self).__init__(model=model, q_filter=q_filter, *args, **kwargs)
        self.o2m = 1

    def clean(self, value):
        clean_id = super(CremeEntityField, self).clean(value)
        if not clean_id:
            return None

        if len(clean_id) > 1:
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

        try:
            if self.q_filter is not None:
                return self.model.objects.filter(get_q_from_dict(self.q_filter)).get(pk=clean_id[0])
            else:
                return self.model.objects.get(pk=clean_id[0])
        except self.model.DoesNotExist:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'])


class MultiCremeEntityField(_EntityField):
    """
         An input with comma (or anything) separated primary keys
         clean method return a list of real model instances
    """
    def __init__(self, model=CremeEntity, q_filter=None, *args, **kwargs):
        super(MultiCremeEntityField, self).__init__(model=model, q_filter=q_filter, *args, **kwargs)
        self.o2m = 0

    def clean(self, value):
        cleaned_ids = super(MultiCremeEntityField, self).clean(value)

        if not cleaned_ids:
            return []

        if self.q_filter is not None:
            #entities = self.model.objects.filter(**self.q_filter).filter(pk__in=cleaned_ids) #COMMENTED on 12 oct 2010 ; to be tested
            entities = self.model.objects.filter(get_q_from_dict(self.q_filter)).filter(pk__in=cleaned_ids)
        else:
            entities = self.model.objects.filter(pk__in=cleaned_ids)

        if len(entities) != len(cleaned_ids):#entities.count() better ?
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': ', '.join(str(val) for val in value)})

        return entities


class ListEditionField(Field):
    """A field to allow the user to edit/delete a list of strings.
    It returns a list with the same order:
    * deleted elements are replaced by None.
    * modified elements are replaced by the new value.
    """
    widget = ListEditionWidget
    default_error_messages = {}

    def __init__(self, content=(), only_delete=False, *args, **kwargs):
        """
        @param content Sequence of strings
        @param only_delete Can only delete elements, not edit them.
        """
        super(ListEditionField, self).__init__(*args, **kwargs)
        self.content = content
        self.only_delete = only_delete

    def _set_content(self, content):
        self._content = content
        self.widget.content = content

    content = property(lambda self: self._content, _set_content); del _set_content

    def _set_only_delete(self, only_delete):
        self._only_delete = only_delete
        self.widget.only_delete = only_delete

    only_delete = property(lambda self: self._only_delete, _set_only_delete); del _set_only_delete


class AjaxChoiceField(ChoiceField):
    """
        Same as ChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
#        value = super(ChoiceField, self).clean(value)

        is_value_empty = value in EMPTY_VALUES

        if self.required and is_value_empty:
            raise ValidationError(self.error_messages['required'])

        if is_value_empty:
            value = u''

        return smart_unicode(value)


class AjaxMultipleChoiceField(MultipleChoiceField):
    """
        Same as MultipleChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
        """
        Validates that the input is a list or tuple.
        """
        not_value = not value
        if self.required and not_value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not_value:
            return []

        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['invalid_list'])

        return [smart_unicode(val) for val in value]


class AjaxModelChoiceField(ModelChoiceField):
    """
        Same as ModelChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
#        Field.clean(self, value)

        if value in EMPTY_VALUES:
            return None

        try:
            key   = self.to_field_name or 'pk'
            value = self.queryset.model._default_manager.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])

        return value


class CremeTimeField(TimeField):
    widget = TimeWidget


class CremeDateField(DateField):
    widget = CalendarWidget


class CremeDateTimeField(DateTimeField):
    widget = CalendarWidget


class MultiEmailField(Field):
    #Original code at http://docs.djangoproject.com/en/1.3/ref/forms/validation/#form-field-default-cleaning
    widget = Textarea

    def __init__(self, sep="\n", *args, **kwargs):
        super(MultiEmailField, self).__init__(*args, **kwargs)
        self.sep = sep

    def to_python(self, value):
        "Normalize data to a list of strings."

        # Return an empty list if no input was given.
        if not value:
            return []
        return [v for v in value.split(self.sep) if v]#Remove empty values but the validation is more flexible

    def validate(self, value):
        "Check if value consists only of valid emails."

        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)

        for email in value:
            validate_email(email)

class DateRangeField(MultiValueField):
    """
    A field which returns a creme_core.utils.DateRange
    Commonly used with a DateRangeWidget
    ex:
        DateRangeField(label=_(u'Date range'))#Use DateRangeWidget with defaults params
        DateRangeField(label=_(u'Date range'), widget=DateRangeWidget(attrs={'render_as': 'ul'}))#Render DateRangeWidget as ul/li
        DateRangeField(label=_(u'Date range'), widget=DateRangeWidget(attrs={'render_as': 'table'}))#Render DateRangeWidget as a table
    """
    widget = DateRangeWidget

    default_error_messages = {
        'customized_empty': _(u'If you select customized you have to specify a start date and/or an end date.'),
        'customized_invalid': _(u'Start date has to be before end date.'),
    }

    def __init__(self, render_as="table", required=False, *args, **kwargs):
        self.ranges     = ChoiceField(choices=chain([(u'', _(u'Customized'))], date_range_registry.choices()))
        self.start_date = DateField()
        self.end_date   = DateField()
        self.render_as  = render_as

        fields = self.ranges, self.start_date, self.end_date

        super(DateRangeField, self).__init__(fields, required=required, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return data_list[0], data_list[1], data_list[2]
        return u'', u'', u''

    def clean(self, value):
        field_name, start, end = super(DateRangeField, self).clean(value)

        if field_name == "":
            if not (start or end):
                raise ValidationError(self.error_messages['customized_empty'])

            if start is not None and end is not None and start > end:
                raise ValidationError(self.error_messages['customized_invalid'])

        return date_range_registry.get_range(field_name, start, end)

    def widget_attrs(self, widget):
        return {'render_as': self.render_as}