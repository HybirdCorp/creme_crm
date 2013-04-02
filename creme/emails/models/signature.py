# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.db.models import CharField, TextField, ManyToManyField, ForeignKey
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme.creme_core.models import CremeModel

from creme.media_managers.models import Image


class EmailSignature(CremeModel):
    name   = CharField(_(u'Name'), max_length=100)
    user   = ForeignKey(User, verbose_name=_(u'User'))
    body   = TextField(_(u'Body'))
    images = ManyToManyField(Image, verbose_name=_(u'Images'), blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "emails"
        verbose_name = _(u"Email signature")
        verbose_name_plural = _(u"Email signatures")
        ordering = ('name',)

    def can_change_or_delete(self, user):
        return self.user_id == user.id or user.is_superuser
