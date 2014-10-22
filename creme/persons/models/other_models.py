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

from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import BasicAutoField


__all__ = ('Civility', 'Position', 'StaffSize', 'LegalForm', 'Sector')


class Civility(CremeModel):
    title    = CharField(pgettext_lazy('persons-civility', u'Title'), max_length=100)
    shortcut = CharField(_(u'Shortcut'), max_length=100)

    def __unicode__(self):
        return self.title

    class Meta:
        app_label = "persons"
        verbose_name = _(u'Civility')
        verbose_name_plural = _(u'Civilities')
        ordering = ('title',)


class Position(CremeModel):
    title = CharField(pgettext_lazy('persons-position', u'Title'), max_length=100)

    def __unicode__(self):
        return self.title

    class Meta:
        app_label = "persons"
        verbose_name = _(u'People position')
        verbose_name_plural = _(u'People positions')
        ordering = ('title',)


class Sector(CremeModel):
    title = CharField(pgettext_lazy('persons-sector', u'Title'), max_length=100)

    def __unicode__(self):
        return self.title

    class Meta:
        app_label = "persons"
        verbose_name = _(u"Line of business")
        verbose_name_plural = _(u"Lines of business")
        ordering = ('title',)


class LegalForm(CremeModel):
    title = CharField(pgettext_lazy('persons-legalform', u'Title'), max_length=100)

    def __unicode__(self):
        return self.title

    class Meta:
        app_label = "persons"
        verbose_name = _(u'Legal form')
        verbose_name_plural = _(u'Legal forms')
        ordering = ('title',)


class StaffSize(CremeModel):
    size  = CharField(_(u'Size'), max_length=100)
    order = BasicAutoField(_('Order')) #used by creme_config

    def __unicode__(self):
        return self.size

    class Meta:
        app_label = "persons"
        verbose_name = _(u"Organisation staff size")
        verbose_name_plural = _(u"Organisation staff sizes")
        ordering = ('order',)
