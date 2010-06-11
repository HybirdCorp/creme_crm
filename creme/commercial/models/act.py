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

from logging import debug
from datetime import datetime

from django.db.models import Model, CharField, TextField, ForeignKey, PositiveIntegerField, DateField, BooleanField
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode

from creme_core.models import CremeEntity 


class Act(CremeEntity):
    name          = CharField(_(u"Nom de l'action commerciale"), max_length=100, blank=False, null=False)
    ca_expected   = PositiveIntegerField(_(u'CA espéré'), blank=True, null=True)
    cost          = PositiveIntegerField(_(u"Cout de l'action commerciale"), blank=True, null=True)
    target        = TextField(_(u'Cible'), blank=True, null=True)
    goal          = TextField(_(u"But de l'action"), blank=True, null=True)
    aim           = TextField(_(u'Objectifs à réaliser'), blank=True, null=True)
    due_date      = DateField(_(u'Échéance'), blank=False, null=False)


    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/commercial/act/%s" % self.id

    def get_edit_absolute_url(self):
        return "/commercial/act/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/commercial/acts"

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Action Commerciale')
        verbose_name_plural = _(u'Actions Commerciales')
