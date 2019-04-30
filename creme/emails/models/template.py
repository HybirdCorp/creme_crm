# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.conf import settings
from django.db.models import CharField, TextField, ForeignKey, ManyToManyField, SET_NULL
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import UnsafeHTMLField

from .signature import EmailSignature


class AbstractEmailTemplate(CremeEntity):
    name        = CharField(_('Name'), max_length=100)
    subject     = CharField(_('Subject'), max_length=100)
    body        = TextField(_('Body'))
    body_html   = UnsafeHTMLField(_('Body (HTML)'))
    signature   = ForeignKey(EmailSignature, verbose_name=_('Signature'),
                             blank=True, null=True, on_delete=SET_NULL,
                            )
    attachments = ManyToManyField(settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name=_('Attachments'))

    creation_label = _('Create an email template')
    save_label     = _('Save the email template')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'emails'
        verbose_name = _('Email template')
        verbose_name_plural = _('Email templates')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('emails__view_template', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('emails__create_template')

    def get_edit_absolute_url(self):
        return reverse('emails__edit_template', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('emails__list_templates')


class EmailTemplate(AbstractEmailTemplate):
    class Meta(AbstractEmailTemplate.Meta):
        swappable = 'EMAILS_TEMPLATE_MODEL'
