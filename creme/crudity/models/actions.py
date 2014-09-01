# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from pickle import loads, dumps

from django.db.models.signals import post_save
from django.db.models import TextField, CharField #ForeignKey
#from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _, ugettext
#from django.utils.simplejson import loads, dumps

from creme.creme_core.models import CremeModel, SettingValue
from creme.creme_core.models.fields import CremeUserForeignKey, CTypeForeignKey

from creme.crudity.signals import post_save_setting_value


__all__ = ("WaitingAction",)


class WaitingAction(CremeModel):
    action  = CharField(_(u"Action"), max_length=100)#Action (i.e: create, update...) #TODO: int instead ??
    source  = CharField(_(u"Source"), max_length=100)#Source (i.e: email raw, email from infopath, sms raw...)
    data    = TextField(blank=True, null=True)
    #ct      = ForeignKey(ContentType, verbose_name=_(u"Ressource's type"), blank=False, null=False)#Redundant, but faster bd recovery
    ct      = CTypeForeignKey(verbose_name=_(u"Ressource's type"))#Redundant, but faster bd recovery
    subject = CharField(_(u"Subject"), max_length=100)
    user    = CremeUserForeignKey(verbose_name=_(u"Owner"), blank=True, null=True, default=None)#Case of sandboxes are by user

    class Meta:
        app_label = "crudity"
        verbose_name = _(u"Waiting action")
        verbose_name_plural = _(u"Waiting actions")

    def get_data(self):
        data = loads(self.data.encode('utf-8'))
        if isinstance(data, dict):
            d = {}
            for k,v in data.iteritems():
                d[k] = v.decode('utf8') if isinstance(v, basestring) else v
            data = d

        return data

    def set_data(self, data):
        return dumps(data)

    def can_validate_or_delete(self, user):
        """self.user not None means that sandbox is by user"""
        if self.user is not None and self.user != user and not user.is_superuser:
            return (False, ugettext(u"You are not allowed to validate/delete the waiting action <%s>") % self.id)

        return (True, ugettext(u"OK"))

post_save.connect(post_save_setting_value, sender=SettingValue)
