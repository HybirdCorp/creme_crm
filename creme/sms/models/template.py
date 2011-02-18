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

from django.db.models import CharField, TextField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity


class MessageTemplate(CremeEntity):
    name    = CharField(_(u'Name'), max_length=100)
    subject = CharField(_(u'Subject'), max_length=100)
    body    = TextField(_(u"Body"))

    class Meta:
        app_label = "sms"
        verbose_name = _(u"Message template")
        verbose_name_plural = _(u"Messages templates")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/sms/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/sms/template/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/sms/templates"

    def resolve(self, date):
        return self.subject + ' : ' + self.body
