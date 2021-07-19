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

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import (
    CREME_REPLACE,
    CremeEntity,
    CremeModel,
    Relation,
    RelationType,
)

from .. import constants

_STATS_TYPES = (
    constants.REL_OBJ_IS_INVITED_TO,
    constants.REL_OBJ_ACCEPTED_INVITATION,
    constants.REL_OBJ_REFUSED_INVITATION,
    constants.REL_OBJ_CAME_EVENT,
)


class EventType(CremeModel):
    name = models.CharField(_('Name'), max_length=50)

    creation_label = pgettext_lazy('events-event_type', 'Create a type')

    class Meta:
        app_label = 'events'
        verbose_name = _('Type of event')
        verbose_name_plural = _('Types of event')
        ordering = ('name',)

    def __str__(self):
        return self.name


class AbstractEvent(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    type = models.ForeignKey(EventType, verbose_name=_('Type'), on_delete=CREME_REPLACE)

    place = models.CharField(
        pgettext_lazy('events', 'Place'), max_length=100, blank=True,
    ).set_tags(optional=True)

    start_date = models.DateTimeField(_('Start date'))
    end_date = models.DateTimeField(_('End date'), blank=True, null=True).set_tags(optional=True)

    budget = models.DecimalField(
        _('Budget (€)'), max_digits=10, decimal_places=2, blank=True, null=True,
    ).set_tags(optional=True)
    final_cost = models.DecimalField(
        _('Final cost (€)'), max_digits=10, decimal_places=2, blank=True, null=True,
    ).set_tags(optional=True)

    creation_label = pgettext_lazy('events', 'Create an event')
    save_label     = pgettext_lazy('events', 'Save the event')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'events'
        verbose_name = pgettext_lazy('events', 'Event')
        verbose_name_plural = pgettext_lazy('events', 'Events')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def _pre_delete(self):
        for relation in Relation.objects.filter(
            type__in=[
                constants.REL_OBJ_IS_INVITED_TO,
                constants.REL_OBJ_ACCEPTED_INVITATION,
                constants.REL_OBJ_REFUSED_INVITATION,
                constants.REL_OBJ_CAME_EVENT,
                constants.REL_OBJ_NOT_CAME_EVENT,
                constants.REL_OBJ_GEN_BY_EVENT,
            ],
            subject_entity=self,
        ):
            relation._delete_without_transaction()

    def clean(self):
        end = self.end_date

        if end and self.start_date > end:
            raise ValidationError(
                {'end_date': gettext('The end date must be after the start date.')},
            )

    def get_absolute_url(self):
        return reverse('events__view_event', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('events__create_event')

    def get_edit_absolute_url(self):
        return reverse('events__edit_event', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('events__list_events')

    def get_stats(self):
        types_count = dict(
            RelationType.objects.filter(
                id__in=_STATS_TYPES,
                relation__subject_entity=self.id,
            ).annotate(
                relations_count=models.Count('relation'),
            ).values_list(
                'id', 'relations_count',
            )
            # .order_by()  # NB: do not use Meta.ordering (remove when use Django 3.1)
        )
        get_count = types_count.get

        return {
            'invitations_count': get_count(constants.REL_OBJ_IS_INVITED_TO, 0),
            'accepted_count':    get_count(constants.REL_OBJ_ACCEPTED_INVITATION, 0),
            'refused_count':     get_count(constants.REL_OBJ_REFUSED_INVITATION, 0),
            'visitors_count':    get_count(constants.REL_OBJ_CAME_EVENT, 0),
        }

    def set_invitation_status(self, contact, status, user):
        relations = Relation.objects

        if status == constants.INV_STATUS_NOT_INVITED:
            relations.filter(
                subject_entity=contact.id,
                object_entity=self.id,
                type__in=(
                    constants.REL_SUB_IS_INVITED_TO,
                    constants.REL_SUB_ACCEPTED_INVITATION,
                    constants.REL_SUB_REFUSED_INVITATION,
                ),
            ).delete()
        else:
            relations.safe_get_or_create(
                subject_entity=contact,
                type=RelationType.objects.get(pk=constants.REL_SUB_IS_INVITED_TO),
                object_entity=self,
                user=user,
            )

            if status == constants.INV_STATUS_ACCEPTED:
                relations.safe_get_or_create(
                    subject_entity=contact,
                    type_id=constants.REL_SUB_ACCEPTED_INVITATION,
                    object_entity=self,
                    user=user,
                )
                relations.filter(
                    subject_entity=contact.id,
                    object_entity=self.id,
                    type=constants.REL_SUB_REFUSED_INVITATION,
                ).delete()
            elif status == constants.INV_STATUS_REFUSED:
                relations.safe_get_or_create(
                    subject_entity=contact,
                    type_id=constants.REL_SUB_REFUSED_INVITATION,
                    object_entity=self,
                    user=user,
                )
                relations.filter(
                    subject_entity=contact.id,
                    type=constants.REL_SUB_ACCEPTED_INVITATION,
                    object_entity=self.id,
                ).delete()
            else:
                assert status == constants.INV_STATUS_NO_ANSWER
                relations.filter(
                    subject_entity=contact.id,
                    type__in=(
                        constants.REL_SUB_ACCEPTED_INVITATION,
                        constants.REL_SUB_REFUSED_INVITATION,
                    ),
                    object_entity=self.id,
                ).delete()

    def set_presence_status(self, contact, status, user):
        relations = Relation.objects

        if status == constants.PRES_STATUS_NOT_COME:
            relations.filter(
                subject_entity=contact.id,
                type=constants.REL_SUB_CAME_EVENT,
                object_entity=self.id,
            ).delete()
            relations.safe_get_or_create(
                subject_entity=contact,
                type_id=constants.REL_SUB_NOT_CAME_EVENT,
                object_entity=self,
                user=user,
            )
        elif status == constants.PRES_STATUS_COME:
            relations.filter(
                subject_entity=contact.id,
                type=constants.REL_SUB_NOT_CAME_EVENT,
                object_entity=self.id,
            ).delete()
            relations.safe_get_or_create(
                subject_entity=contact,
                type_id=constants.REL_SUB_CAME_EVENT,
                object_entity=self,
                user=user,
            )
        else:  # PRES_STATUS_DONT_KNOW
            relations.filter(
                subject_entity=contact.id,
                type__in=(
                    constants.REL_SUB_CAME_EVENT,
                    constants.REL_SUB_NOT_CAME_EVENT,
                ),
                object_entity=self.id,
            ).delete()


class Event(AbstractEvent):
    class Meta(AbstractEvent.Meta):
        swappable = 'EVENTS_EVENT_MODEL'
