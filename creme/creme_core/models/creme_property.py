# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
import warnings
from typing import Iterable, Type, Union

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .. import signals
from ..utils.content_type import as_ctype
from .base import CremeModel
from .entity import CremeEntity

logger = logging.getLogger(__name__)


class CremePropertyTypeManager(models.Manager):
    def compatible(self, ct_or_model: Union[ContentType, Type[CremeEntity]]):
        return self.filter(
            Q(subject_ctypes=as_ctype(ct_or_model))
            | Q(subject_ctypes__isnull=True)
        )

    # TODO: split into 2 methods (smart_create & smart_update_or_create) ?
    #       avoid retrieving the instance again in CremePropertyTypeEditForm.save()
    #       (use a True model-form + improve CremePropertyType.save() ?) ?
    def smart_update_or_create(
        self, *,
        str_pk: str,
        generate_pk: bool = False,
        text: str,
        subject_ctypes: Iterable[Union[ContentType, CremeEntity]] = (),
        is_custom: bool = False,
        is_copiable: bool = True,
    ) -> 'CremePropertyType':
        """Helps the creation of new CremePropertyType instance.
        @param str_pk: Used as ID value (or it's prefix -- see generate_pk).
        @param generate_pk: If True, 'str_pk' argument is used as prefix to
               generate the Primary Key.
        @param text: Used to fill <CremePropertyType.text>.
        @param subject_ctypes: Used to fill <CremePropertyType.subject_ctypes>.
        @param is_custom: Used to fill <CremePropertyType.is_custom>.
        @param is_copiable: Used to fill <CremePropertyType.is_copiable>.
        """
        if not generate_pk:
            property_type = self.update_or_create(
                id=str_pk,
                defaults={
                    'text': text,
                    'is_custom': is_custom,
                    'is_copiable': is_copiable,
                },
            )[0]
        else:
            from creme.creme_core.utils.id_generator import (
                generate_string_id_and_save,
            )

            property_type = self.model(
                text=text, is_custom=is_custom, is_copiable=is_copiable,
            )
            generate_string_id_and_save(CremePropertyType, [property_type], str_pk)

        get_ct = ContentType.objects.get_for_model
        property_type.subject_ctypes.set([
            model if isinstance(model, ContentType) else get_ct(model)
            for model in subject_ctypes
        ])

        return property_type


# TODO: factorise with RelationManager ?
class CremePropertyManager(models.Manager):
    def safe_create(self, **kwargs) -> None:
        """Create a CremeProperty in DB by taking care of the UNIQUE constraint
        of Relation.
        Notice that, unlike 'create()' it always return None (to avoid a
        query in case of IntegrityError) ; use 'safe_get_or_create()' if
        you need the CremeProperty instance.
        @param kwargs: same as 'create()'.
        """
        try:
            with atomic():
                self.create(**kwargs)
        except IntegrityError:
            logger.exception('Avoid a CremeProperty duplicate: %s ?!', kwargs)

    def safe_get_or_create(self, **kwargs):
        """Kind of safe version of 'get_or_create'.
        Safe means the UNIQUE constraint of Relation is respected, &
        this method will never raise an IntegrityError.

        Notice that the signature of this method is the same as 'create()'
        & not the same as 'get_or_create()' : the argument "defaults" does
        not exist & no boolean is returned.

        @param kwargs: same as 'create()'.
        return: A CremeProperty instance.
        """
        for _i in range(10):
            try:
                prop = self.get(**kwargs)
            except self.model.DoesNotExist:
                try:
                    with atomic():
                        prop = self.create(**kwargs)
                except IntegrityError:
                    logger.exception('Avoid a CremeProperty duplicate: %s ?!', kwargs)
                    continue

            break
        else:
            raise RuntimeError(
                f'It seems the CremeProperty <{kwargs}> keeps being created & deleted.'
            )

        return prop

    def safe_multi_save(self,
                        properties: Iterable['CremeProperty'],
                        check_existing: bool = True) -> int:
        """Save several instances of CremeProperty by taking care of the UNIQUE
        constraint on ('type', 'creme_entity').

        Notice that you should not rely on the instances which you gave ;
        they can be saved (so get a fresh ID), or not be saved because they are
        a duplicate (& so their ID remains 'None').

        Compared to use N x 'safe_get_or_create()', this method will only
        perform 1 query to retrieve the existing CremeProperties.

        @param properties: An iterable of CremeProperties (not save yet).
        @param check_existing: Perform a query to check existing CremeProperties.
               You can pass False for newly created instances in order to avoid a query.
        @return: Number of CremeProperties inserted in base.
        """
        count = 0
        unique_props = {
            (prop.type_id, prop.creme_entity_id): prop
            for prop in properties
        }

        if unique_props:
            if check_existing:
                existing_q = Q()
                for prop in unique_props.values():
                    existing_q |= Q(
                        type_id=prop.type_id,
                        creme_entity_id=prop.creme_entity_id,
                    )

                for prop_sig in self.filter(existing_q).values_list(
                    'type', 'creme_entity',
                ):
                    unique_props.pop(prop_sig, None)

            for prop in unique_props.values():
                try:
                    with atomic():
                        prop.save()
                except IntegrityError:
                    logger.exception('Avoid a CremeProperty duplicate: %s ?!', prop)
                else:
                    count += 1

        return count


class CremePropertyType(CremeModel):
    id = models.CharField(primary_key=True, max_length=100)
    text = models.CharField(_('Text'), max_length=200, unique=True)

    subject_ctypes = models.ManyToManyField(
        ContentType, blank=True,
        verbose_name=_('Applies on entities with following types'),
        related_name='subject_ctypes_creme_property_set',  # TODO: '+'
    )
    is_custom = models.BooleanField(default=False, editable=False)

    # If True, the properties with this type can be copied
    # (ie: when cloning or converting an entity).
    is_copiable = models.BooleanField(_('Is copiable'), default=True)

    # A disabled type should not be proposed for adding (and a property with
    # this type should be visually marked as disabled in the UI).
    enabled = models.BooleanField(_('Enabled?'), default=True, editable=False)

    objects = CremePropertyTypeManager()

    creation_label = _('Create a type of property')
    save_label     = _('Save the type of property')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Type of property')
        verbose_name_plural = _('Types of property')
        ordering = ('text',)

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse('creme_core__ptype', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('creme_core__create_ptype')

    def get_delete_absolute_url(self):
        return reverse('creme_core__delete_ptype', args=(self.id,))

    def get_edit_absolute_url(self):
        return reverse('creme_core__edit_ptype', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('creme_config__ptypes')

    @classmethod
    def create(cls,
               str_pk,
               text,
               subject_ctypes=(),
               is_custom=False,
               generate_pk=False,
               is_copiable=True,
               ):
        warnings.warn(
            'CremePropertyType.create() is deprecated; '
            'use CremePropertyType.objects.smart_update_or_create() instead.',
            DeprecationWarning,
        )
        return cls.objects.smart_update_or_create(
            str_pk=str_pk,
            text=text,
            subject_ctypes=subject_ctypes,
            is_custom=is_custom,
            generate_pk=generate_pk,
            is_copiable=is_copiable,
        )


class CremeProperty(CremeModel):
    type = models.ForeignKey(
        CremePropertyType,
        verbose_name=_('Type of property'),
        on_delete=models.CASCADE,
    )
    creme_entity = models.ForeignKey(
        CremeEntity,
        verbose_name=_('Entity'),
        related_name='properties', on_delete=models.CASCADE,
    )

    objects = CremePropertyManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Property')
        verbose_name_plural = _('Properties')
        unique_together = ('type', 'creme_entity')

    def __str__(self):
        return str(self.type)

    def get_related_entity(self):  # For generic views
        return self.creme_entity


@receiver(signals.pre_merge_related)
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


@receiver(signals.pre_replace_related, sender=CremePropertyType)
def _handle_replacement(sender, old_instance, new_instance, **kwargs):
    """Delete 'Duplicated' CremeProperties (ie: one entity has 2 properties
    with the old & the new types).
    """
    from django.db.models import Count

    from .history import HistoryLine

    # IDs of entities with duplicates
    e_ids = CremeEntity.objects.filter(
        properties__type__in=[old_instance, new_instance],
    ).annotate(
        prop_count=Count('properties'),
    ).filter(
        prop_count__gte=2,
    ).values_list('id', flat=True)

    for prop in CremeProperty.objects.filter(creme_entity__in=e_ids, type=old_instance):
        HistoryLine.disable(prop)  # See _handle_merge()
        prop.delete()
