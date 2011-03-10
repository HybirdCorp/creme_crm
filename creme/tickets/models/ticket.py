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

from datetime import datetime

from django.db.models import ForeignKey, CharField, TextField, DateTimeField
from django.utils.translation import ugettext_lazy as _
from django.utils.formats import date_format

from creme_core.models import CremeEntity, FunctionField
from creme_core.templatetags.creme_date import timedelta_pprint

from status import Status, CLOSED_PK
from priority import Priority
from criticity import Criticity


class _ResolvingDurationField(FunctionField):
    name         = "get_resolving_duration"
    verbose_name = _(u'Resolving duration')


class AbstractTicket(CremeEntity):
    title        = CharField(_(u'Title'), max_length=100, blank=True, null=False, unique=True)
    description  = TextField(_(u'Description'), blank=False, null=False)
    status       = ForeignKey(Status, verbose_name=_(u'Status'), blank=False, null=False)
    priority     = ForeignKey(Priority, verbose_name=_(u'Priority'), blank=False, null=False)
    criticity    = ForeignKey(Criticity, verbose_name=_(u'Criticity'), blank=False, null=False)
    solution     = TextField(_(u'Solution'), blank=True, null=False)

    class Meta:
        app_label = 'tickets'
        abstract = True

    def __unicode__(self):
        return self.title


class Ticket(AbstractTicket):
    closing_date = DateTimeField(_(u'Closing date'), blank=True, null=True)

    function_fields = CremeEntity.function_fields.new(_ResolvingDurationField)

    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket')
        verbose_name_plural = _(u'Tickets')

    def get_absolute_url(self):
        return "/tickets/ticket/%s" % self.id

    def get_edit_absolute_url(self):
        return "/tickets/ticket/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/tickets/tickets"

    def get_resolving_duration(self):
        if self.status_id == CLOSED_PK:
            return  timedelta_pprint(self.closing_date - self.created)

        return ''


class TicketTemplate(AbstractTicket):
    """Used by 'recurrents' app if it is installed"""
    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket template')
        verbose_name_plural = _(u'Ticket templates')

    def get_absolute_url(self):
        return "/tickets/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/tickets/template/edit/%s" % self.id

    def get_delete_absolute_url(self):
        return '' #means that TicketTemplate can not be deleted directly (because it is closely linked to its RecurrentGenerator)

    @staticmethod
    def get_lv_absolute_url():
        return "/tickets/templates"

    def create_entity(self):
        """This method is used by the generation job of the 'recurrents' app"""
        #Beware: the 'title' column must be unique
        now = datetime.now()
        title = u'%s %s' % (self.title, date_format(now.date(), 'DATE_FORMAT'))

        ticket = Ticket(user=self.user,
                        description=self.description,
                        status_id=self.status_id,
                        priority_id=self.priority_id,
                        criticity_id=self.criticity_id,
                        solution=self.solution,
                        closing_date = now if self.status_id == CLOSED_PK else None
                       )

        min_index = Ticket.objects.filter(title__startswith=title).count() + 1
        last_exception = None

        for i in xrange(min_index, min_index + 10): #10 trials should be enough for 99,9999% of cases :)
            ticket.title = u'%s #%s' % (title, i)

            try:
                ticket.save()
            except Exception, e:
                last_exception = e
            else:
                break
        else:
            raise last_exception

        return ticket
