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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import TextField, PositiveIntegerField, CharField
from django.db.models.fields.related import ForeignKey
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.encoding import smart_str
from django.db.models.signals import post_save

from creme_core.models.base import CremeModel
from creme_config.models.setting import SettingValue
from creme_core.models.fields import CremeUserForeignKey

from crudity import VERBOSE_CRUD
from crudity.signals import post_save_setting_value

__all__ = ("WaitingAction",)

class WaitingAction(CremeModel):
    type    = PositiveIntegerField()
    data    = TextField(blank=True, null=True)
    ct      = ForeignKey(ContentType, verbose_name=_(u"Ressource's type"), blank=False, null=False)#Redundant, but faster bd recovery
    be_name = CharField(_(u"Backend's name"), max_length=100)#Backend's name with which he has registered
    user    = CremeUserForeignKey(verbose_name=_(u"Owner"), blank=True, null=True, default=None)#Case of sandboxes are by user

    class Meta:
        app_label = "crudity"
        verbose_name = _(u"Waiting action")
        verbose_name_plural = _(u"Waiting actions")

    def __unicode__(self):
        return u"%s - %s" % (unicode(self._meta.verbose_name), VERBOSE_CRUD.get(self.type))

    def set_data(self, data):#force data to be a dict...
        _data = []
        for k, v in data.items():
            _data.append(u"%s:%s" % (k, encodestring(smart_str(v))))
        return "#".join(_data)

    def get_data(self):
        data = self.data
        _data = {}
        if data:
            for d in data.split('#'):
                k, v = d.split(':')
                _data[k] = decodestring(v).decode('utf-8')

        return _data

    def can_validate_or_delete(self, user):
        """self.user not None means that sandbox is by user"""
        if self.user is not None and self.user != user and not user.is_superuser:
            return (False, ugettext(u"You are not allowed to validate/delete the waiting action <%s>") % self.id)
        return (True, ugettext(u"OK"))

post_save.connect(post_save_setting_value, sender=SettingValue)
