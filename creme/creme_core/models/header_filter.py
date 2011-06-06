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
from logging import debug

from django.db.models import (Model, CharField, ForeignKey, BooleanField, PositiveIntegerField,
                              PositiveSmallIntegerField, DateField, DateTimeField)
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import RelationType, CremeEntity, CustomField
from creme_core.utils.meta import get_model_field_infos #get_flds_with_fk_flds_str
from creme_core.utils.id_generator import generate_string_id_and_save


HFI_ACTIONS    = 0
HFI_FIELD      = 1
HFI_RELATION   = 2
HFI_FUNCTION   = 3
HFI_CUSTOM     = 4
HFI_CALCULATED = 5 #TODO: Used only in reports for the moment, integrate into HF?
HFI_VOLATILE   = 6 #not saved in DB : added at runtime to implements tricky columnns ; see HeaderFilterItem.volatile_render


class HeaderFilterList(list):
    """Contains all the HeaderFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's as a cache.
    """
    def __init__(self, content_type):
        super(HeaderFilterList, self).__init__(HeaderFilter.objects.filter(entity_type=content_type).order_by('name'))
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select_by_id(self, *ids):
        """Try several HeaderFilter ids"""
        #linear search but with few items after all....
        for hf_id in ids:
            for hf in self:
                if hf.id == hf_id:
                    self._selected = hf
                    return hf

        if self:
            self._selected = self[0]
        else:
            self._selected = None

        return self._selected


class HeaderFilter(Model): #CremeModel ???
    id          = CharField(primary_key=True, max_length=100)
    name        = CharField(max_length=100, verbose_name=_('Name of the view'))
    user        = ForeignKey(User, verbose_name=_(u'Owner'), blank=True, null=True)
    entity_type = ForeignKey(ContentType, editable=False)
    is_custom   = BooleanField(blank=False, default=True)

    _items = None

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'<HeaderFilter: name="%s">' % self.name

    def build_items(self, show_actions=False):
        items = list(self.header_filter_items.order_by('order'))

        if show_actions:
            items.insert(0, _hfi_action)

        self._items = items

    #TODO: factorise with Filter.can_edit_or_delete ???
    def can_edit_or_delete(self, user):
        if not self.is_custom:
            return (False, ugettext(u"This view can't be edited/deleted"))

        if not self.user_id: #all users allowed
            return (True, 'OK')

        if user.is_superuser:
            return (True, 'OK')

        if not user.has_perm(self.entity_type.app_label):
            return (False, ugettext(u"You are not allowed to acceed to this app"))

        if not self.user.is_team:
            if self.user_id == user.id:
                return (True, 'OK')
        elif user.team_m2m.filter(teammate=user).exists():
            return (True, 'OK')

        return (False, ugettext(u"You are not allowed to edit/delete this view"))

    @staticmethod
    def create(pk, name, model, is_custom=False, user=None):
        """Creation helper ; useful for populate.py scripts.
        It clean old HeaderFilterItems.
        """
        from creme_core.utils import create_or_update
        hf = create_or_update(HeaderFilter, pk=pk,
                              name=name, is_custom=is_custom, user=user,
                              entity_type=ContentType.objects.get_for_model(model)
                             )
        HeaderFilterItem.objects.filter(header_filter=pk).delete()
        return hf

    @property
    def items(self):
        if self._items is None:
            self.build_items()
        return self._items

    def populate_entities(self, entities, user):
        """Fill caches of CremeEntity objects, related to the columns that will
        be displayed with this HeaderFilter.
        @param entities QuerySet on CremeEntity (or subclass).
        """
        hfi_groups = defaultdict(list)

        for hfi in self.items:
            hfi_groups[hfi.type].append(hfi)

        group = hfi_groups[HFI_ACTIONS]
        if group:
            CremeEntity.populate_credentials(entities, user)

        group = hfi_groups[HFI_FIELD]
        if group:
            CremeEntity.populate_fk_fields(entities, [hfi.name.partition('__')[0] for hfi in group])

        group = hfi_groups[HFI_RELATION]
        if group:
            CremeEntity.populate_relations(entities, [hfi.relation_predicat_id for hfi in group], user)

        group = hfi_groups[HFI_CUSTOM]
        if group:
            cfields = CustomField.objects.in_bulk([int(hfi.name) for hfi in group])

            for hfi in group:
                hfi._customfield = cfields[int(hfi.name)]

            CremeEntity.populate_custom_values(entities, cfields.values()) #NB: not itervalues() (iterated several times)

        for hfi in hfi_groups[HFI_FUNCTION]:
            func_field = self.entity_type.model_class().function_fields.get(hfi.name)
            func_field.populate_entities(entities)

    def set_items(self, items): #TODO: reuse old items' pk ?? fill cache ?
        for i, hfi in enumerate(items, start=1):
            hfi.order = i
            hfi.header_filter = self

        generate_string_id_and_save(HeaderFilterItem, items, self.id)


class HeaderFilterItem(Model):  #CremeModel ???
    id                    = CharField(primary_key=True, max_length=100)
    order                 = PositiveIntegerField()
    name                  = CharField(max_length=100)
    title                 = CharField(max_length=100)
    type                  = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}
    header_filter         = ForeignKey(HeaderFilter, related_name='header_filter_items')
    has_a_filter          = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    editable              = BooleanField(blank=True, default=True)   #TODO: useful ?? retrievable with type ??
    sortable              = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    is_hidden             = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    filter_string         = CharField(max_length=100, blank=True, null=True)
    relation_predicat     = ForeignKey(RelationType, blank=True, null=True) #TODO: rename to 'relation_type' ???  use 'name' to store pk instead ????
    relation_content_type = ForeignKey(ContentType, blank=True, null=True) #TODO: useful ??

    _customfield = None
    _volatile_render = None

    def __unicode__(self):
        return u"<HeaderFilterItem: order: %i, name: %s, title: %s>" % (self.order, self.name, self.title)

    class Meta:
        app_label = 'creme_core'

    class ValueError(Exception):
        pass

    _CF_PATTERNS = {
            CustomField.BOOL:       '%s__value__creme-boolean',
            CustomField.DATE:       '%s__value__range',
            CustomField.ENUM:       '%s__value__exact',
            CustomField.MULTI_ENUM: '%s__value__exact',
        }

    @classmethod
    def build_4_customfield(cls, customfield):
        pattern = cls._CF_PATTERNS.get(customfield.field_type, '%s__value__icontains')

        return HeaderFilterItem(name=unicode(customfield.id),
                                title=customfield.name,
                                type=HFI_CUSTOM,
                                has_a_filter=True,
                                editable=False, #TODO: make it editable
                                sortable=False, #TODO: make it sortable
                                filter_string=pattern % customfield.get_value_class().get_related_name(),
                               )

    @staticmethod
    def build_4_field(model, name):
        field_info = get_model_field_infos(model, name)
        if not field_info:
            raise HeaderFilterItem.ValueError(u'Invalid field: %s' % name)

        field   = field_info[0]['field']
        pattern = "%s__icontains"

        if isinstance(field, ForeignKey) :
            if len(field_info) == 1:
                pattern = "%s"
            else:
                field = field_info[1]['field'] #The sub-field is considered as the main field

        if isinstance(field, (DateField, DateTimeField)):
            pattern = "%s__range"
        elif isinstance(field, BooleanField):
            pattern = "%s__creme-boolean"

        return HeaderFilterItem(name=name,
                                 title=u" - ".join(unicode(info['field'].verbose_name) for info in field_info),
                                 type=HFI_FIELD,
                                 has_a_filter=True,
                                 editable=True,
                                 sortable=True,
                                 filter_string=pattern % name
                                )

    @staticmethod
    def build_4_functionfield(func_field):
        return HeaderFilterItem(name=func_field.name,
                                title=unicode(func_field.verbose_name),
                                type=HFI_FUNCTION,
                                has_a_filter=func_field.has_filter,
                                is_hidden=func_field.is_hidden,
                                editable=False,
                                filter_string=""
                               )

    @staticmethod
    def build_4_relation(rtype):
        return HeaderFilterItem(name=unicode(rtype.id),
                                title=rtype.predicate,
                                type=HFI_RELATION,
                                has_a_filter=True,
                                editable=False ,
                                filter_string="",
                                relation_predicat=rtype #TODO: rtype.id in 'name' attr...
                               )

    def get_customfield(self):
        assert self.type == HFI_CUSTOM

        if self._customfield is None:
            debug('HeaderFilterItem.get_customfield(): cache MISS for id=%s', self.id)
            self._customfield = CustomField.objects.get(pk=self.name)
        else:
            debug('HeaderFilterItem.get_customfield(): cache HIT for id=%s', self.id)

        return self._customfield

    def _get_volatile_render(self):
        assert self.type == HFI_VOLATILE
        assert self._volatile_render is not None
        return self._volatile_render

    def _set_volatile_render(self, volatile_render):
        assert self.type == HFI_VOLATILE
        self._volatile_render = volatile_render

    #volatile_render is a 'function' that takes one parameter: the entity display on the current list line
    #this function must be set on the HeaderFilterItem with type HFI_VOLATILE
    volatile_render = property(_get_volatile_render, _set_volatile_render); del (_get_volatile_render, _set_volatile_render)

_hfi_action = HeaderFilterItem(order=0, name='entity_actions', title=_(u'Actions'), type=HFI_ACTIONS, has_a_filter=False, editable=False, is_hidden=False)


def _delete_relationtype_hfi(sender, instance, **kwargs):
    #NB: None: because with symmetric relation_type FK is cleaned
    HeaderFilterItem.objects.filter(type=HFI_RELATION, relation_predicat=None).delete()

def _delete_customfield_hfi(sender, instance, **kwargs):
    HeaderFilterItem.objects.filter(type=HFI_CUSTOM, name=instance.id).delete()

pre_delete.connect(_delete_relationtype_hfi, sender=RelationType)
pre_delete.connect(_delete_customfield_hfi,  sender=CustomField)
