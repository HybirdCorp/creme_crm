# -*- coding: utf-8 -*-

#################################################################################
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
#################################################################################

from django.db import models

from creme_core.models import CremeModel, CremeEntity

class EntityASData(CremeModel):
    """
        Additional values for an entity, present in Active sync but not in Creme
        For example: a Meeting hasn't an UID but on server side it has.
    """
    entity      = models.ForeignKey(CremeEntity,    verbose_name=u'Target entity')
    field_name  = models.CharField(u'Field name',   max_length=100)#Exchange field name
    field_value = models.CharField(u'Field value',  max_length=300)#Exchange field value

    def __unicode__(self):
        return u"<EntityASData entity<%s>, field_name<%s>, field_value<%s> >" % (self.entity, self.field_name, self.field_value)

    class Meta:
        app_label = 'activesync'
        verbose_name = u""
        verbose_name_plural = u""
        unique_together = ("entity", "field_name")