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

from django.db.models import CharField, TextField, ForeignKey, ManyToManyField, SET_NULL
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from documents.models import Document

from signature import EmailSignature


class EmailTemplate(CremeEntity):
    name        = CharField(_(u'Name'), max_length=100)
    subject     = CharField(_(u'Subject'), max_length=100)
    body        = TextField(_(u"Body"))
    body_html   = TextField(_(u"Body (HTML)"))
    signature   = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True, on_delete=SET_NULL)
    attachments = ManyToManyField(Document, verbose_name=_(u'Attachments'))

    #excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['use_rte'] #body too ???

    class Meta:
        app_label = "emails"
        verbose_name = _(u"Email template")
        verbose_name_plural = _(u"Email templates")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/emails/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/emails/template/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/emails/templates"


