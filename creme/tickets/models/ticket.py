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

from django.db.models import ForeignKey, CharField, TextField, DateTimeField
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.template.loader import render_to_string

from creme_core.models import CremeEntity, FunctionField
from creme_core.templatetags.creme_date import timedelta_pprint

from status import Status, CLOSED_PK
from priority import Priority
from criticity import Criticity


class _ResolvingDurationField(FunctionField):
    name         = "get_resolving_duration"
    verbose_name = _(u'Resolving duration')


#relié à une ou plusieurs fiches (une relation spéciale 'en rapport à' ? ) ??

class Ticket(CremeEntity):
    title        = CharField(_(u'Title'), max_length=100, blank=True, null=False, unique=True)
    description  = TextField(_(u'Description'), blank=False, null=False)
    status       = ForeignKey(Status, verbose_name=_(u'Status'), blank=False, null=False)
    closing_date = DateTimeField(_(u'Closing date'), blank=True, null=True)
    priority     = ForeignKey(Priority, verbose_name=_(u'Priority'), blank=False, null=False)
    criticity    = ForeignKey(Criticity, verbose_name=_(u'Criticity'), blank=False, null=False)
    solution     = TextField(_(u'Solution'), blank=True, null=False)

    function_fields = CremeEntity.function_fields.new(_ResolvingDurationField)

    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket')
        verbose_name_plural = _(u'Tickets')

    def __unicode__(self):
        return force_unicode(self.title)

    def get_absolute_url(self):
        return "/tickets/ticket/%s" % self.id

    def get_edit_absolute_url(self):
        return "/tickets/ticket/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/tickets/tickets"

    def get_delete_absolute_url(self):
        return "/tickets/ticket/delete/%s" % self.id

    def get_resolving_duration(self):
        if self.status.pk == CLOSED_PK: #status_id == CLOSED_PK instead ???
            return  timedelta_pprint(self.closing_date - self.created)

        return ''
