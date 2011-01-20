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

from django.db.models import CharField, TextField, DateTimeField, DecimalField, ForeignKey, Count
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, CremeModel, RelationType, Relation

from events.constants import *


_STATS_TYPES = (REL_OBJ_IS_INVITED_TO, REL_OBJ_ACCEPTED_INVITATION,REL_OBJ_REFUSED_INVITATION, REL_OBJ_CAME_EVENT)


class EventType(CremeModel):
    name = CharField(_(u'Name'), max_length=50)

    class Meta:
        app_label = 'events'
        verbose_name = _(u'Type of event')
        verbose_name_plural = _(u'Types of event')

    def __unicode__(self):
        return self.name


class Event(CremeEntity):
    name        = CharField(_(u'Name'), max_length=100)
    type        = ForeignKey(EventType, verbose_name=_(u'Type'))
    description = TextField(_(u'Description'), blank=True)
    place       = CharField(_(u'Place'), max_length=100, blank=True)
    start_date  = DateTimeField(_(u'Start date'))
    end_date    = DateTimeField(_(u'End date'), blank=True, null=True)
    budget      = DecimalField(_(u'Budget (€)'), max_digits=10, decimal_places=2, blank=True, null=True)
    final_cost  = DecimalField(_(u'Final cost (€)'), max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        app_label = 'events'
        verbose_name = _(u'Event')
        verbose_name_plural = _(u'Events')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/events/event/%s" % self.id

    def get_edit_absolute_url(self):
        return "/events/event/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/events/events"

    def get_stats(self):
        types_count = dict(RelationType.objects.filter(relation__subject_entity=self.id, id__in=_STATS_TYPES) \
                                               .annotate(relations_count=Count('relation')) \
                                               .values_list('id', 'relations_count'))
        get_count = types_count.get

        return {
                'invations_count': get_count(REL_OBJ_IS_INVITED_TO, 0),
                'accepted_count':  get_count(REL_OBJ_ACCEPTED_INVITATION, 0),
                'refused_count':   get_count(REL_OBJ_REFUSED_INVITATION, 0),
                'visitors_count':  get_count(REL_OBJ_CAME_EVENT, 0),
               }

    def set_invitation_status(self, contact, status, user):
        relations = Relation.objects

        if status == INV_STATUS_NOT_INVITED:
            relations.filter(subject_entity=contact.id, object_entity=self.id,
                                    type__in=(REL_SUB_IS_INVITED_TO, REL_SUB_ACCEPTED_INVITATION, REL_SUB_REFUSED_INVITATION)) \
                            .delete()
        else:
            create_relations = Relation.objects.create
            relations.get_or_create(subject_entity=contact, type=RelationType.objects.get(pk=REL_SUB_IS_INVITED_TO), object_entity=self, user=user)

            if status == INV_STATUS_ACCEPTED:
                relations.create(subject_entity=contact, type_id=REL_SUB_ACCEPTED_INVITATION, object_entity=self, user=user)
                relations.filter(subject_entity=contact.id, object_entity=self.id, type=REL_SUB_REFUSED_INVITATION) \
                         .delete()
            elif status == INV_STATUS_REFUSED:
                relations.create(subject_entity=contact, type_id=REL_SUB_REFUSED_INVITATION, object_entity=self, user=user)
                relations.filter(subject_entity=contact.id, object_entity=self.id, type=REL_SUB_ACCEPTED_INVITATION) \
                         .delete()

    def set_presence_status(self, contact, status, user):
        relations = Relation.objects

        if status == PRES_STATUS_NOT_COME:
            relations.filter(subject_entity=contact.id, type=REL_SUB_CAME_EVENT, object_entity=self.id).delete()
            relations.create(subject_entity=contact, type_id=REL_SUB_NOT_CAME_EVENT, object_entity=self, user=user)
        elif status == PRES_STATUS_COME:
            relations.filter(subject_entity=contact.id, type=REL_SUB_NOT_CAME_EVENT, object_entity=self.id).delete()
            relations.create(subject_entity=contact, type_id=REL_SUB_CAME_EVENT, object_entity=self, user=user)
        else: #PRES_STATUS_DONT_KNOW
            relations.filter(subject_entity=contact.id, type__in=(REL_SUB_CAME_EVENT, REL_SUB_NOT_CAME_EVENT), object_entity=self.id) \
                     .delete()
