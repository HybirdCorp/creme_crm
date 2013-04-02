# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from random import randint

from django.db.models import ForeignKey, CharField, TextField, DateTimeField, PROTECT
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.formats import date_format

from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.models import CremeEntity
from creme.creme_core.templatetags.creme_date import timedelta_pprint
from creme.creme_core.utils import truncate_str

from .status import Status, OPEN_PK, CLOSED_PK
from .priority import Priority
from .criticity import Criticity


MAXINT = 100000

class _ResolvingDurationField(FunctionField):
    name         = "get_resolving_duration"
    verbose_name = _(u'Resolving duration')


class AbstractTicket(CremeEntity):
    title        = CharField(_(u'Title'), max_length=100, blank=True, null=False, unique=True)
    description  = TextField(_(u'Description'))
    status       = ForeignKey(Status, verbose_name=_(u'Status'), on_delete=PROTECT)
    priority     = ForeignKey(Priority, verbose_name=_(u'Priority'), on_delete=PROTECT)
    criticity    = ForeignKey(Criticity, verbose_name=_(u'Criticity'), on_delete=PROTECT)
    solution     = TextField(_(u'Solution'), blank=True, null=False)

    class Meta:
        app_label = 'tickets'
        abstract = True

    def __unicode__(self):
        return self.title

    def _pre_save_clone(self, source):
        max_length = self._meta.get_field('title').max_length
        self.title = truncate_str(source.title, max_length, suffix=' (%s %08x)' % (ugettext(u"Copy"), randint(0, MAXINT)))

        while self._default_manager.filter(title=self.title).exists():
            self._pre_save_clone(source)


class Ticket(AbstractTicket):
    closing_date = DateTimeField(_(u'Closing date'), blank=True, null=True, editable=False)

    function_fields = CremeEntity.function_fields.new(_ResolvingDurationField())
    creation_label = _('Add a ticket')

    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket')
        verbose_name_plural = _(u'Tickets')

    def __init__(self, *args, **kwargs):
        super(Ticket, self).__init__(*args, **kwargs)
        self.old_status_id = self.status_id

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

    def _pre_save_clone(self, source):
        super(Ticket, self)._pre_save_clone(source)
        if self.status_id == CLOSED_PK:
            self.closing_date = self.created = self.modified = datetime.now()

    def save(self, *args, **kwargs):
        if self.pk:
            if (self.status_id == CLOSED_PK) and (self.old_status_id != CLOSED_PK):
                self.closing_date = datetime.now()
        else: #creation
            self.status_id = self.status_id or OPEN_PK

        super(Ticket, self).save(*args, **kwargs)


class TicketTemplate(AbstractTicket):
    """Used by 'recurrents' app if it is installed"""
    creation_label = _('Add a ticket template')

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
            except Exception as e:
                last_exception = e
            else:
                break
        else:
            raise last_exception

        return ticket
