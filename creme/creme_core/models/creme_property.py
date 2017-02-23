# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import CharField, ForeignKey, ManyToManyField, BooleanField, Q
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from ..signals import pre_merge_related, pre_replace_related
from .base import CremeModel
from .entity import CremeEntity


class CremePropertyType(CremeModel):
    id             = CharField(primary_key=True, max_length=100)
    text           = CharField(max_length=200, unique=True)
    subject_ctypes = ManyToManyField(ContentType, blank=True, related_name='subject_ctypes_creme_property_set')
    is_custom      = BooleanField(default=False)  # TODO: editable=False ??
    # If True, the properties with this type can be copied (ie: when cloning or converting an entity).
    is_copiable    = BooleanField(default=True)

    creation_label = _(u'Create a type of property')
    save_label     = _(u'Save the type of property')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Type of property')
        verbose_name_plural = _(u'Types of property')
        ordering = ('text',)

    def __unicode__(self):
        return self.text

    def get_absolute_url(self):
        # return '/creme_core/property/type/%s' % self.id
        return reverse('creme_core__ptype', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        # return '/creme_core/property/type/add'
        return reverse('creme_core__create_ptype')

    def get_delete_absolute_url(self):
        # return '/creme_core/property/type/%s/delete' % self.id
        return reverse('creme_core__delete_ptype', args=(self.id,))

    def get_edit_absolute_url(self):
        # return '/creme_core/property/type/%s/edit' % self.id
        return reverse('creme_core__edit_ptype', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return '/creme_config/property_type/portal/'

    @staticmethod
    def create(str_pk, text, subject_ctypes=(), is_custom=False, generate_pk=False, is_copiable=True):
        """Helps the creation of new CremePropertyType.
        @param subject_ctypes: Sequence of CremeEntity classes/ContentType objects.
        @param generate_pk: If True, str_pk is used as prefix to generate pk.
        """
        if not generate_pk:
            property_type = CremePropertyType.objects.update_or_create(
                                    id=str_pk,
                                    defaults={'text': text,
                                              'is_custom': is_custom,
                                              'is_copiable': is_copiable,
                                             }
                                )[0]
        else:
            from creme.creme_core.utils.id_generator import generate_string_id_and_save
            property_type = CremePropertyType(text=text, is_custom=is_custom, is_copiable=is_copiable)
            generate_string_id_and_save(CremePropertyType, [property_type], str_pk)

        get_ct = ContentType.objects.get_for_model
        property_type.subject_ctypes = [model if isinstance(model, ContentType) else get_ct(model)
                                            for model in subject_ctypes
                                       ]

        return property_type

    @staticmethod
    def get_compatible_ones(ct):
        return CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))


class CremeProperty(CremeModel):
    type         = ForeignKey(CremePropertyType)
    creme_entity = ForeignKey(CremeEntity, related_name='properties')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Property')
        verbose_name_plural = _(u'Properties')
        unique_together = ('type', 'creme_entity')

    def __unicode__(self):
        return unicode(self.type)

    def get_related_entity(self):  # For generic views
        return self.creme_entity


@receiver(pre_merge_related)
def _handle_merge(sender, other_entity, **kwargs):
    """Delete 'Duplicated' CremeProperties (ie: exist in the removed entity &
    the remaining entity).
    """
    from .history import HistoryLine

    ptype_ids = sender.properties.values_list('type', flat=True)

    for prop in other_entity.properties.filter(type__in=ptype_ids):
        # Duplicates' deletion would be confusing to the user (the
        # property type is still related to the remaining entity). So we
        # disable the history for it.
        HistoryLine.disable(prop)
        prop.delete()


@receiver(pre_replace_related, sender=CremePropertyType)
def _handle_replacement(sender, old_instance, new_instance, **kwargs):
    """Delete 'Duplicated' CremeProperties (ie: one entity has 2 properties
    with the old & the new types).
    """
    from django.db.models import Count

    from .history import HistoryLine

    # IDs of entities with duplicates
    e_ids = CremeEntity.objects.filter(properties__type__in=[old_instance, new_instance]) \
                               .annotate(prop_count=Count('properties')) \
                               .filter(prop_count__gte=2) \
                               .values_list('id', flat=True)

    for prop in CremeProperty.objects.filter(creme_entity__in=e_ids, type=old_instance):
        HistoryLine.disable(prop)  # See _handle_merge()
        prop.delete()
