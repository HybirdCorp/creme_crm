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

#from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import TextField, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import CreationDateTimeField

from creme_core.models.base import CremeModel
from creme_core.models.entity import CremeEntity

__all__ = ("History", )

class History(CremeModel):
#    entity_id   = PositiveIntegerField()
    entity      = ForeignKey(CremeEntity, verbose_name=_(u"Entity"), blank=False, null=False)
    created     = CreationDateTimeField(_(u'Creation date'))
    type        = PositiveIntegerField()
#    ct          = ForeignKey(ContentType, verbose_name=_(u"Ressource's type"), blank=False, null=False)#Redundant, but faster bd recovery
    description = TextField(_(u'Description'), blank=True, null=True)

    class Meta:
        app_label = "crudity"
        verbose_name = _(u"History")
        verbose_name_plural = _(u"History")

    def get_entity(self):
        entity = self.entity
        if entity:
            entity = entity.get_real_entity()
        return entity

#    def get_entity(self):
#        entity = None
#        entity_id = self.entity_id
#        if entity_id:
#            try:
#                entity = CremeEntity.objects.get(pk=entity_id).get_real_entity()
#            except CremeEntity.DoesNotExist:
#                pass
#        return entity

    def __unicode__(self):
        return u"History of %s" % self.get_entity() or u""
