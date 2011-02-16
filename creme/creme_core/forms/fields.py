# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from re import compile as re_compile
from logging import debug

from django.core.exceptions import PermissionDenied
from django.forms import Field, CharField, MultipleChoiceField, ChoiceField, ModelChoiceField, DateField, TimeField, DateTimeField
from django.forms.util import ValidationError
from django.forms.fields import EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import loads as jsonloads
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, CremeEntity, Relation
from creme_core.utils import creme_entity_content_types
from creme_core.utils.queries import get_q_from_dict
from creme_core.forms.widgets import CTEntitySelector, SelectorList, RelationSelector, ListViewWidget, ListEditionWidget, RelationListWidget, CalendarWidget, TimeWidget
from creme_core.constants import REL_SUB_RELATED_TO, REL_SUB_HAS


__all__ = ('MultiGenericEntityField', 'GenericEntityField',
           'MultiRelationEntityField', 'RelationEntityField',
           'RelatedEntitiesField', # TODO : remove this
           'CremeEntityField', 'MultiCremeEntityField',
           'ListEditionField',
           'AjaxChoiceField', 'AjaxMultipleChoiceField', 'AjaxModelChoiceField',
           'CremeTimeField', 'CremeDateField', 'CremeDateTimeField')


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

        if not value:
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
        # TODO : wait for django 1.2 and new widget api to remove this hack
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

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        if isinstance(value, CremeEntity):
            ctype, pk = value.entity_type.id, value.id
        else:
            ctype = value['ctype']
            pk = value['entity']

        entity = {'ctype': ctype, 'entity': pk}

        return self.format_json(entity)

    def clean(self, value):
        data = self.clean_json(value)

        if data is not None and not isinstance(data, dict):
            raise ValidationError(self.error_messages['invalidformat'])

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        ctype_pk, entity_pk = self.clean_value(data, 'ctype', int), self.clean_value(data, 'entity', int)

        return self.clean_entity(ctype_pk, entity_pk)

    def clean_entity(self, ctype_pk, entity_pk):
        ctype = self.clean_ctype(ctype_pk)
        model = ctype.model_class()

        try:
            #return CremeEntity.objects.get(pk=data['entity']).get_real_entity()
            entity = model.objects.get(pk=entity_pk)

            #entity.can_view_or_die(user) TODO: user not reachable from field --> forbidden id can be forged...
        except model.DoesNotExist, PermissionDenied:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'])

        #print 'GenericEntityField.clean_entity(ctype=%s, entity=%s) > %s' % (ctype_pk, entity_pk, entity)
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
        except RelationType.DoesNotExist, PermissionDenied:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype':rtype_pk})

    def _get_ctypes_options(self, ctypes):
        return ((ctype.pk, unicode(ctype)) for ctype in ctypes)

    def get_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        return [get_ct(model) for model in self.allowed_models] if self.allowed_models else list(creme_entity_content_types())

    def set_allowed_models(self, models=None):
        self.allowed_models = models if models else list()
        self._build_widget()


#TODO: Add a q_filter, see utilization in EntityEmailForm
class MultiGenericEntityField(GenericEntityField):
    def __init__(self, models=None, *args, **kwargs):
        super(MultiGenericEntityField, self).__init__(models, *args, **kwargs)
#        self.widget = SelectorList(self.widget)
        # TODO : wait for django 1.2 and new widget api to remove this hack
#        self.widget.from_python = lambda v: self.from_python(v)

    def _create_widget(self):
        return SelectorList(CTEntitySelector(self._get_ctypes_options(self.get_ctypes()), multiple=True));

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        entities = []

        for entry in value:
            if isinstance(entry, CremeEntity):
                ctype, pk = entry.entity_type.id, entry.id
                entry = {'ctype': ctype, 'entity': pk}

            entities.append(entry)

        #entities = [{'ctype':ctype, 'entity':pk} for ctype, pk in CremeEntity.objects.filter(pk__in=value).values_list('entity_type', 'pk')]
        return self.format_json(entities)

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

            entities.extend(ctype_entities.values())

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

    def __init__(self, relations=(REL_SUB_RELATED_TO, REL_SUB_HAS), *args, **kwargs):
        super(RelationEntityField, self).__init__(*args, **kwargs)
        self.allowed_rtypes = frozenset(relations)
        self._build_widget()

    def _create_widget(self):
        return RelationSelector(self._get_options(self.get_rtypes()),
                                '/creme_core/relation/predicate/${rtype}/content_types/json')

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        rtype, entity = value
        relation = {'rtype':rtype.pk, 'ctype':entity.entity_type, 'entity':entity.pk}

        return self.format_json(relation)

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        clean_value = self.clean_value

        rtype_pk, ctype_pk, entity_pk = clean_value(data, 'rtype', str), \
                                        clean_value(data, 'ctype', int), \
                                        clean_value(data, 'entity', int)

        rtype = self.clean_rtype(rtype_pk)

        self.validate_ctype_constraints(rtype, ctype_pk)

        entity = self.clean_entity(ctype_pk, entity_pk)
        self.validate_properties_constraints(rtype, entity)

        return (rtype, entity)

    def validate_ctype_constraints(self, rtype, ctype_pk):
        rtype_ctypes = rtype.object_ctypes.values_list('pk', flat=True)

        # is relation type accepts content type
        if rtype_ctypes and ctype_pk not in rtype_ctypes:
            raise ValidationError(self.error_messages['ctypenotallowed'], params={'ctype':ctype_pk})

    def validate_properties_constraints(self, rtype, entity):
        rtype_properties = frozenset(rtype.object_properties.values_list('id', flat=True))

        if rtype_properties and not any(p.type_id in rtype_properties for p in entity.get_properties()):
            raise ValidationError(self.error_messages['nopropertymatch'])

    def clean_rtype(self, rtype_pk):
        # is relation type allowed
        if rtype_pk not in self.allowed_rtypes:
            raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype':rtype_pk})

        try:
            return RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist, PermissionDenied:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype':rtype_pk})

    def clean_entity(self, ctype_pk, entity_pk):
        ctype = ContentType.objects.get_for_id(ctype_pk)
        model = ctype.model_class()

        try:
            #return CremeEntity.objects.get(pk=data['entity']).get_real_entity()
            entity = model.objects.get(pk=entity_pk)

            #entity.can_view_or_die(user) TODO: user not reachable from field --> forbidden id can be forged...
        except model.DoesNotExist, PermissionDenied:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'], params={'ctype':ctype_pk, 'entity':entity_pk})

        #print 'GenericEntityField.clean_entity(ctype=%s, entity=%s) > %s' % (ctype_pk, entity_pk, entity)
        return entity

    def _get_options(self, entity):
        return ((entity.pk, unicode(entity)) for entity in entity)

    def get_rtypes(self):
        return RelationType.objects.filter(id__in=self.allowed_rtypes) if self.allowed_rtypes else RelationType.objects.all()

    def set_allowed_rtypes(self, allowed=(REL_SUB_RELATED_TO, REL_SUB_HAS)):
        self.allowed_rtypes = frozenset(allowed)
        self._build_widget()


class MultiRelationEntityField(RelationEntityField):
    def __init__(self, relations=(REL_SUB_RELATED_TO, REL_SUB_HAS), *args, **kwargs):
        super(MultiRelationEntityField, self).__init__(relations, *args, **kwargs)
#        self.widget = SelectorList(self.widget)

        # TODO : wait for django 1.2 and new widget api to remove this hack
#        self.widget.from_python = lambda v: self.from_python(v)

    def _create_widget(self):
        return SelectorList(RelationSelector(self._get_options(self.get_rtypes()),
                                             '/creme_core/relation/predicate/${rtype}/content_types/json',
                                             multiple=True))

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        entities = []

        for rtype, entity in value:
            entities.append({'rtype':rtype.pk, 'ctype':entity.entity_type, 'entity':entity.pk})

        return self.format_json(entities)

    def _build_rtype_cache(self, rtype_pk):
        try:
            rtype = RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist, PermissionDenied:
            raise ValidationError(self.error_messages['rtypedoesnotexist'], params={'rtype':rtype_pk})

        rtype_allowed_ctypes     = frozenset(ct.pk for ct in rtype.object_ctypes.all())
        rtype_allowed_properties = frozenset(rtype.object_properties.values_list('id', flat=True))

        return (rtype, rtype_allowed_ctypes, rtype_allowed_properties)

    def _build_ctype_cache(self, ctype_pk):
        ctype = ContentType.objects.get_for_id(ctype_pk)

        if not ctype:
            raise ValidationError(self.error_messages['ctypedoesnotexist'], params={'ctype':ctype_pk})

        return (ctype, list())

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

        cleaned_entries = [(clean_value(entry, 'rtype', str), \
                            clean_value(entry, 'ctype', int), \
                            clean_value(entry, 'entity', int)) for entry in data]

        rtypes_cache = dict()
        ctypes_cache = dict()

        need_property_validation = False

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            # check if relation type is allowed
            if rtype_pk not in self.allowed_rtypes:
                raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype':rtype_pk, 'ctype':ctype_pk})

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

            if rtype_allowed_properties:
                need_property_validation = True

            # check if content type is allowed by relation type
            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'], params={'ctype':ctype_pk})

            ctype, ctype_entity_pks = self._get_cache(ctypes_cache, ctype_pk, self._build_ctype_cache)
            ctype_entity_pks.append(entity_pk)

        entities_cache = dict()

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


# TODO: remove this field when refactor of activity and event forms will be done.
class RelatedEntitiesField(CharField):
    default_error_messages = {
        'invalidformat': _(u'Invalid format'),
    }
    widget = RelationListWidget

    regex = re_compile('^(\([\w-]+,[\d]+,[\d]+\);)*$')

    def __init__(self, relation_types=(REL_SUB_RELATED_TO, REL_SUB_HAS), *args, **kwargs):
        """
        @param relation_types Sequence of RelationTypes' id if you want to narrow to these RelationTypes.
        """
        super(RelatedEntitiesField, self).__init__(*args, **kwargs)
        self.relation_types = relation_types

    def _set_relation_types(self, relation_types):
        rtypes = RelationType.objects.filter(pk__in=relation_types)
        self._relation_types = rtypes
        self.widget.relation_types = rtypes

    relation_types = property(lambda self: self._relation_types, _set_relation_types)

    def clean(self, value):
        value = value or ''

        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        if not self.regex.match(value):
            raise ValidationError(self.error_messages['invalidformat'])

        allowed_rtypes = set(rtype.id for rtype in self.relation_types)

        rawdata = [(relationtype_pk, int(content_type_pk), int(pk))
                        for relationtype_pk, content_type_pk, pk in (entry.strip('()').split(',') for entry in value.split(';')[:-1])
                            if relationtype_pk in allowed_rtypes]

        ct_map = defaultdict(list)
        for relationtype_id, ct_id, entity_id in rawdata:
            ct_map[ct_id].append(entity_id)

        entities = {}
        get_ct   = ContentType.objects.get_for_id

        for ct_id, entity_ids in ct_map.iteritems():
            entities.update(get_ct(ct_id).model_class().objects.in_bulk(entity_ids))

        return [(relationtype_id, entities[entity_id]) for relationtype_id, ct_id, entity_id in rawdata]


class _CommaMultiValueField(CharField): #TODO: Charfield and not Field ??!!
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


class _EntityField(_CommaMultiValueField):
    """
        Base class for CremeEntityField and MultiCremeEntityField,
        not really usable elsewhere avoid using it
    """
    widget = ListViewWidget
    default_error_messages = {
        'invalid_choice': _(u"Select a valid choice. %(value)s is not an available choice."),
    }

    o2m = 1

    def _get_model(self):
        return self._model

    def _set_model(self, model):
        self._model = self.widget.model = model

    model = property(_get_model, _set_model) #TODO: lambda instead of '_get_model' ?? del _set_model ?

    def _get_q_filter(self):
        return self._q_filter

    def _set_q_filter(self, q_filter):
        self._q_filter = self.widget.q_filter = q_filter

    q_filter = property(_get_q_filter, _set_q_filter)

    def clean(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        clean_ids = super(_EntityField, self).clean(value)

        try:
            clean_ids = map(int, clean_ids)
        except ValueError:
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

        return clean_ids

    #TODO: attrs are better for html related properties ==> use setter on the widget directly (as 'choices' for ChoiceField)
    def widget_attrs(self, widget):
        if isinstance(widget, (ListViewWidget,)):
            return {'o2m': self.o2m, 'ct_id': ContentType.objects.get_for_model(self.model).id}


class CremeEntityField(_EntityField):
    """
         An input with comma (or anything) separated primary keys
         clean method return a model instance
    """
    default_error_messages = {
        'doesnotexist' : _(u"This entity doesn't exist."),
    }

    def __init__(self, model, q_filter=None, *args, **kwargs):
        self.model = model
        super(CremeEntityField, self).__init__(*args, **kwargs)
        self.q_filter = q_filter

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
    o2m = 0

    def __init__(self, model, separator=',', q_filter=None, *args, **kwargs):
        self.separator = separator
        self.model = model
        super(MultiCremeEntityField, self).__init__(*args, **kwargs)
        self.q_filter = q_filter

    def clean(self, value):
        cleaned_ids = super(MultiCremeEntityField, self).clean(value)

        if not cleaned_ids:
            return []

        if self.q_filter is not None:
            #entities = self.model.objects.filter(**self.q_filter).filter(pk__in=cleaned_ids) #COMMENTED on 12 oct 2010 ; to be tested
            entities = self.model.objects.filter(get_q_from_dict(self.q_filter)).filter(pk__in=cleaned_ids)
        else:
            entities = self.model.objects.filter(pk__in=cleaned_ids)

        if len(entities) != len(cleaned_ids):
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

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
