# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.exceptions import ValidationError
from django.forms.fields import CharField
from django.utils.translation import ugettext_lazy as _, ugettext, ungettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.bulk import BulkDefaultEditForm #BulkForm
from creme.creme_core.forms.fields import DurationField, JSONField
from creme.creme_core.forms.widgets import ChainedInput, Label
from creme.creme_core.utils.id_generator import generate_string_id_and_save

from ..constants import ACTIVITYTYPE_INDISPO
from ..models import ActivityType, ActivitySubType


class ActivityTypeForm(CremeModelForm):
    default_hour_duration = DurationField(label=_(u'Duration'))

    class Meta(CremeModelForm.Meta):
        model = ActivityType

    def save(self):
        instance = self.instance

        if not instance.id:
            super(ActivityTypeForm, self).save(commit=False)
            generate_string_id_and_save(ActivityType, [instance],
                                        'creme_config-useractivitytype',
                                       )
        else:
            super(ActivityTypeForm, self).save()

        return instance


class ActivitySubTypeForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = ActivitySubType

    def save(self, *args, **kwargs):
        instance = self.instance

        if not instance.id:
            super(ActivitySubTypeForm, self).save(commit=False, *args, **kwargs)
            generate_string_id_and_save(ActivitySubType, [instance],
                                        'creme_config-useractivitydetailesubtype',
                                       )
        else:
            super(ActivitySubTypeForm, self).save(*args, **kwargs)

        return instance


class ActivityTypeWidget(ChainedInput):
    def __init__(self, types, attrs=None, creation_allowed=True):
        super(ActivityTypeWidget, self).__init__(attrs)
        attrs = {'auto': False}
        self.creation_allowed = creation_allowed

        self.add_dselect('type', options=types, attrs=attrs)
        self.add_dselect('sub_type', options='/activities/type/${type}/json', attrs=attrs)


class ActivityTypeField(JSONField):
    default_error_messages = {
        'typenotallowed':  _('This type causes constraint error.'),
        'subtyperequired': _('Sub-type is required.'),
    }
    value_type = dict

    def __init__(self, types=None, *args, **kwargs):
        super(ActivityTypeField, self).__init__(*args, **kwargs)
        self.types = types if types is not None else ActivityType.objects.all()

    def _create_widget(self):
        return ActivityTypeWidget(((atype.pk, unicode(atype)) for atype in self.types),
                                  attrs={'reset': not self.required},
                                 )
#        return ActivityTypeWidget(self._get_types_options(self._get_types_objects()),
#                                  attrs={'reset':False, 'direction':ChainedInput.VERTICAL})

    def _value_to_jsonifiable(self, value):
        if isinstance(value, ActivitySubType):
            type_id = value.type_id
            subtype_id = value.id
        else:
            type_id, subtype_id = value

        return {'type': type_id, 'sub_type': subtype_id}

    def _value_from_unjsonfied(self, data):
        clean = self.clean_value
        type_pk  = clean(data, 'type', str)
        subtype_pk = clean(data, 'sub_type', str, required=False)

        try:
            atype = self.types.get(pk=type_pk)
        except ActivityType.DoesNotExist:
            raise ValidationError(self.error_messages['typenotallowed'])

        related_types = ActivitySubType.objects.filter(type=atype)
        subtype = None

        if subtype_pk:
            try:
                subtype = related_types.get(pk=subtype_pk)
            except ActivitySubType.DoesNotExist:
                raise ValidationError(self.error_messages['subtyperequired'])
        elif self.required and related_types.exists():
            raise ValidationError(self.error_messages['subtyperequired'])

        return (atype, subtype)

    @property
    def types(self):
        return self._types.all()

    @types.setter
    def types(self, types):
        self._types = types
        self._build_widget()


class BulkEditTypeForm(BulkDefaultEditForm):
    def __init__(self, field, user, entities, is_bulk=False, **kwargs):
        super(BulkEditTypeForm, self).__init__(field, user, entities, is_bulk=is_bulk, **kwargs)
        self.fields['field_value'] = type_selector = \
                    ActivityTypeField(label=_(u'Type'),
                                      types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO),
                                     )
        self._mixed_indispo = False
        indispo_count = sum(a.type_id == ACTIVITYTYPE_INDISPO for a in entities)

        if indispo_count:
            if indispo_count == len(entities): # all entities are indisponibilities, so we propose to change the sub-type
                type_selector.types = ActivityType.objects.filter(pk=ACTIVITYTYPE_INDISPO)
            else:
                self._mixed_indispo = True
                self.fields['beware'] = CharField(
                        label=_('Beware !'),
                        required=False, widget=Label,
                        initial=ungettext(u'The type of %s activity cannot be changed because it is an indisponibility.',
                                          u'The type of %s activities cannot be changed because they are indisponibilities.',
                                          indispo_count
                                         ) % indispo_count,
                    )

        if not is_bulk:
            first = entities[0]
            type_selector.initial = (first.type_id, first.sub_type_id)

    def _bulk_clean_entity(self, entity, values):
        if self._mixed_indispo and entity.type_id == ACTIVITYTYPE_INDISPO:
            raise ValidationError(ugettext('The type of an indisponibility cannot be changed.'))

        entity.type, entity.sub_type = values.get(self.field_name)

        return entity
