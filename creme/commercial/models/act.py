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

from django.db.models import CharField, TextField, PositiveIntegerField, DateField, BooleanField, ForeignKey
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremeModel, Relation

from opportunities.models import Opportunity

from commercial.constants import REL_SUB_OPPORT_LINKED, REL_SUB_COMPLETE_GOAL


class ActType(CremeModel):
    title     = CharField(_(u"Title"), max_length=75)
    is_custom = BooleanField(default=True) #used by creme_config

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Type of Commercial Action')
        verbose_name_plural = _(u'Types of Commercial Actions')

    def __unicode__(self):
        return self.title


class Act(CremeEntity):
    name           = CharField(_(u"Name of the commercial action"), max_length=100)
    #ca_expected   = PositiveIntegerField(_(u'Expected sales'), blank=True, null=True)
    expected_sales = PositiveIntegerField(_(u'Expected sales'), blank=True, null=True)
    cost           = PositiveIntegerField(_(u"Cost of the commercial action"), blank=True, null=True)
    #target        = TextField(_(u'Target'), blank=True, null=True)
    goal           = TextField(_(u"Goal of the action"), blank=True, null=True)
    #aim           = TextField(_(u'Objectives to achieve'), blank=True, null=True)
    start          = DateField(_(u'Start'))
    due_date       = DateField(_(u'Due date'))
    act_type       = ForeignKey(ActType, verbose_name=_(u'Type'))

    _related_opportunities = None

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial Action')
        verbose_name_plural = _(u'Commercial Actions')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/commercial/act/%s" % self.id

    def get_edit_absolute_url(self):
        return "/commercial/act/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/commercial/acts"

    def get_made_sales(self):
        return sum(o.made_sales for o in self.get_related_opportunities() if o.made_sales)

    def get_related_opportunities(self):
        relopps = self._related_opportunities

        if relopps is None:
            relopps = list(Opportunity.objects.filter(relations__type=REL_SUB_OPPORT_LINKED,
                                                      relations__object_entity=self.id)
                          )
            self._related_opportunities = relopps

        return relopps


class ActObjective(CremeModel):
    name    = CharField(_(u"Name"), max_length=100)
    act     = ForeignKey(Act)
    counter = PositiveIntegerField(_(u'Counter'), default=0)
    reached = BooleanField(_(u'Reached'), default=False)
    ctype   = ForeignKey(ContentType, verbose_name=_(u'Counted type'), null=True)

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial Objective')
        verbose_name_plural = _(u'Commercial Objectives')

    def __unicode__(self):
        return self.name

    def get_related_entity(self): #NB: see edit_related_to_entity()
        return self.act

    #TODO: optimise by regrouping queries
    def get_relations_count(self): #TODO: get_count that works with custom objectives too ??
        return Relation.objects.filter(type=REL_SUB_COMPLETE_GOAL,
                                       object_entity=self.act_id,
                                       subject_entity__entity_type=self.ctype_id) \
                               .count()
