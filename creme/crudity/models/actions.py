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

from base64 import encodestring, decodestring

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import TextField, PositiveIntegerField, CharField
from django.db.models.fields.related import ForeignKey
from django.utils.translation import ugettext_lazy as _

from creme_core.models.base import CremeModel

from crudity import VERBOSE_CRUD

__all__ = ("WaitingAction",)

class WaitingAction(CremeModel):
    type      = PositiveIntegerField()
    data      = TextField(blank=True, null=True)
    ct        = ForeignKey(ContentType, verbose_name=_(u"Ressource's type"), blank=False, null=False)#Redundant, but faster bd recovery
    be_name   = CharField(_(u"Backend's name"), max_length=100)#Backend's name with which he has registered

    class Meta:
        app_label = "crudity"
        verbose_name = _(u"Waiting action")
        verbose_name_plural = _(u"Waiting actions")

    def __unicode__(self):
        return u"%s - %s" % (unicode(self._meta.verbose_name), VERBOSE_CRUD.get(self.type))

    def set_data(self, data):#force data to be a dict...
        _data = []
        for k, v in data.items():
            _data.append(u"%s:%s" % (k, encodestring(str(v))))
        return "#".join(_data)

    def get_data(self):
        data = self.data
        _data = {}
        if data:
            for d in data.split('#'):
                k, v = d.split(':')
                _data[k] = decodestring(v)
                
        return _data

