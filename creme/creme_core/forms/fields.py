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

from django.forms import Field, CharField, MultipleChoiceField, ChoiceField, ModelChoiceField, DateField, TimeField, DateTimeField
from django.forms.util import ValidationError
from django.forms.fields import EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import loads as jsonloads
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, CremeEntity
from creme_core.utils import creme_entity_content_types
from creme_core.forms.widgets import CTEntitySelector, SelectorList, ListViewWidget, ListEditionWidget, RelationListWidget, CalendarWidget, TimeWidget
from creme_core.constants import REL_SUB_RELATED_TO, REL_SUB_HAS


__all__ = ('GenericEntitiesField', 'RelatedEntitiesField', 'CremeEntityField', 'MultiCremeEntityField',
           'ListEditionField',
           'AjaxChoiceField', 'AjaxMultipleChoiceField', 'AjaxModelChoiceField',
           'CremeTimeField', 'CremeDateField', 'CremeDateTimeField')

def get_entity_ctypes_options(): #TODO: staticmethod ??
    return ((ctype.pk, ctype.__unicode__()) for ctype in creme_entity_content_types())


class GenericEntitiesField(CharField):
    default_error_messages = {
        'invalidformat': _(u'Invalid format'),
    }

    def __init__(self, ctypes=None, *args, **kwargs):
        super(GenericEntitiesField, self).__init__(*args, **kwargs)
        self.ctypes = ctypes
        self.widget = SelectorList(CTEntitySelector(get_entity_ctypes_options() if not ctypes else ctypes))
         # TODO : wait for django 1.2 and new widget api to remove this hack
        self.widget.from_python = lambda v: self.from_python(v)

    # TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        entities = [{'ctype':ctype, 'entity':pk} for ctype, pk in CremeEntity.objects.filter(pk__in=value).values_list('entity_type', 'pk')]
        return JSONEncoder().encode(entities)

    def clean(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        try:
            data = jsonloads(value)
        except:
            raise ValidationError(self.error_messages['invalidformat'])

        return CremeEntity.objects.filter(pk__in=[entry['entity'] for entry in data if entry['entity'] != 'null'])


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

    model = property(_get_model, _set_model) #TODO: lambda isntead of '_get_model' ??

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
                return self.model.objects.filter(**self.q_filter).get(pk=clean_id[0])
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
            entities = self.model.objects.filter(**self.q_filter).filter(pk__in=cleaned_ids)
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

    def __init__(self, content=(), *args, **kwargs):
        """
        @param content Sequence of strings
        """
        super(ListEditionField, self).__init__(*args, **kwargs)
        self.content = content

    def _set_content(self, content):
        self._content = content
        self.widget.content = content

    content = property(lambda self: self._content, _set_content)


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
