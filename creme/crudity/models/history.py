# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.db.models import TextField, PositiveIntegerField, CharField, ForeignKey
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel, CremeEntity
from creme_core.models.fields import CreationDateTimeField, CremeUserForeignKey


__all__ = ("History", )

class History(CremeModel):
    entity      = ForeignKey(CremeEntity, verbose_name=_(u"Entity"), blank=False, null=False)
    created     = CreationDateTimeField(_(u'Creation date'))
    action      = CharField(_(u"Action"), max_length=100)#Action (i.e: create, update...)
    source      = CharField(_(u"Source"), max_length=100)#Source (i.e: email raw, email from infopath, sms raw...)
    description = TextField(_(u'Description'), blank=True, null=True)
    user        = CremeUserForeignKey(verbose_name=_(u"Owner"), blank=True, null=True, default=None)#Case of sandboxes are by user

    class Meta:
        app_label = "crudity"
        verbose_name = _(u"History")
        verbose_name_plural = _(u"History")

    def get_entity(self):
        entity = self.entity
        if entity:
            entity = entity.get_real_entity()
        return entity

    def __unicode__(self):
        return u"History of %s" % self.get_entity() or u""
