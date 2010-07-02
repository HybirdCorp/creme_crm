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

import re
from logging import debug

from django.forms import Field, CharField
from django.forms.util import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import loads as jsonloads
from django.utils.simplejson.encoder import JSONEncoder
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, CremeEntity
from creme_core.utils import creme_entity_content_types
from creme_core.forms.widgets import CTEntitySelector, SelectorList, ListViewWidget, ListEditionWidget


def get_entity_ctypes_options(): #TODO: staticmethod ??
    return ((ctype.pk, ctype.__unicode__()) for ctype in creme_entity_content_types())


class GenericEntitiesField(CharField):
    default_error_messages = {
        'invalidformat': _(u'Format invalide'),
    }

    def __init__(self, ctypes=None, *args, **kwargs):
        super(GenericEntitiesField, self).__init__(*args, **kwargs)
        self.ctypes = ctypes
        self.widget = SelectorList(CTEntitySelector(get_entity_ctypes_options() if not ctypes else ctypes))
         # TODO : wait for django 1.2 and new widget api to remove this hack
        self.widget.from_python = lambda v:self.from_python(v)

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
        'invalidformat': _(u'Format invalide'),
    }

    def __init__(self, relations=None, use_ctype=False, *args, **kwargs):
        self.regex = re.compile('^(\([\w-]+,[\d]+,[\d]+\);)*$')
        self.relations = relations if relations is not None else []
        self.use_ctype = use_ctype
        super(RelatedEntitiesField, self).__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        predicates = RelationType.objects.filter(pk__in=self.relations).values_list('id', 'predicate')
        widget.set_predicates(predicates)
        return super(RelatedEntitiesField, self).widget_attrs(widget)

    def clean(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        if not self.regex.match(value):
            raise ValidationError(self.error_messages['invalidformat'])

        data = (entry.strip('()').split(',') for entry in value.split(';')[:-1])

        if self.use_ctype:
            return [(relationtype_pk, int(content_type_pk), int(pk)) for relationtype_pk, content_type_pk, pk in data if not self.relations or relationtype_pk in self.relations]

        return [(entry[0], int(entry[2])) for entry in data if not self.relations or entry[0] in self.relations]


class CommaMultiValueField(CharField): #TODO: Charfield and not Field ??!!
    """
        An input with comma (or anything) separated values
    """
    default_error_messages = {
    }

    def __init__(self, separator=',', *args, **kwargs):
        self.separator = separator
        super(CommaMultiValueField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and self.required:
            raise ValidationError(self.error_messages['required'])

        if value:
            return [val for val in value.split(self.separator) if val]

        return []


class _EntityField(CommaMultiValueField):
    """
        Base class for CremeEntityField and MultiCremeEntityField,
        not really usable elsewhere avoid using it
    """
    widget = ListViewWidget
    default_error_messages = {
        'invalid_choice': _(u"Selectionnez un choix valide. %(value)s n'est pas un des choix disponibles."),
    }

    o2m = 1

    def _get_model(self):
        return self._model

    def _set_model(self, model):
        self._model = self.widget.model = model

    model = property(_get_model, _set_model)

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

    def widget_attrs(self, widget):
        if isinstance(widget, (ListViewWidget,)):
            return {'o2m': self.o2m, 'ct_id': ContentType.objects.get_for_model(self.model).id}


class CremeEntityField(_EntityField):#TODO : Refactor to derivate from charField ? / Improve me ?
#class CremeEntityField(forms.CharField):
    """
         An input with comma (or anything) separated primary keys
         clean method return a model instance
    """
    default_error_messages = {
        'doesnotexist' : _(u"Cette entité n'existe pas"),
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
        #super(CommaMultiValueField, self).__init__(*args, **kwargs) #super(MultiCremeEntityField, self) ???
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
