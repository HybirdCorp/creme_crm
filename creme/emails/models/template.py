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

from django.db.models import CharField, TextField, ForeignKey, ManyToManyField, BooleanField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from persons.models import MailSignature

from documents.models import Document


class EmailTemplate(CremeEntity):
    name        = CharField(_(u'Nom'), max_length=100)
    subject     = CharField(_(u'Sujet'), max_length=100)
    body        = TextField(_(u"Corps"))
    use_rte     = BooleanField(_(u"Utilise l'éditeur de texte riche"))
    signature   = ForeignKey(MailSignature, verbose_name=_(u'Signature'), blank=True, null=True)
    attachments = ManyToManyField(Document, verbose_name=_(u'Fichiers attachés'))

    excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['use_rte'] #body too ???

    class Meta:
        app_label = "emails"
        verbose_name = _(u"Patron de courriel")
        verbose_name_plural = _(u"Patrons de courriel")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/emails/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/emails/template/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/emails/templates"

    def get_delete_absolute_url(self):
        return "/emails/template/delete/%s" % self.id
