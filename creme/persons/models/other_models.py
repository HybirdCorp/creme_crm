################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import MinionModel
from creme.creme_core.models.fields import BasicAutoField

__all__ = ('Civility', 'Position', 'StaffSize', 'LegalForm', 'Sector')


class Civility(MinionModel):
    title    = CharField(pgettext_lazy('persons-civility', 'Title'), max_length=100)
    shortcut = CharField(_('Shortcut'), max_length=100)

    creation_label = _('Create a civility')

    def __str__(self):
        return self.title

    class Meta:
        app_label = 'persons'
        verbose_name = _('Civility')
        verbose_name_plural = _('Civilities')
        ordering = ('title',)


class Position(MinionModel):
    title = CharField(pgettext_lazy('persons-position', 'Title'), max_length=100)

    creation_label = pgettext_lazy('persons-position', 'Create a position')

    def __str__(self):
        return self.title

    class Meta:
        app_label = 'persons'
        verbose_name = _('People position')
        verbose_name_plural = _('People positions')
        ordering = ('title',)


class Sector(MinionModel):
    title = CharField(pgettext_lazy('persons-sector', 'Title'), max_length=100)

    creation_label = pgettext_lazy('persons-sector', 'Create a sector')

    def __str__(self):
        return self.title

    class Meta:
        app_label = 'persons'
        verbose_name = _('Line of business')
        verbose_name_plural = _('Lines of business')
        ordering = ('title',)


class LegalForm(MinionModel):
    title = CharField(pgettext_lazy('persons-legalform', 'Title'), max_length=100)

    creation_label = _('Create a legal form')

    def __str__(self):
        return self.title

    class Meta:
        app_label = 'persons'
        verbose_name = _('Legal form')
        verbose_name_plural = _('Legal forms')
        ordering = ('title',)


class StaffSize(MinionModel):
    size  = CharField(_('Size'), max_length=100)
    order = BasicAutoField()  # Used by creme_config

    creation_label = _('Create a staff size')

    def __str__(self):
        return self.size

    class Meta:
        app_label = 'persons'
        verbose_name = _('Organisation staff size')
        verbose_name_plural = _('Organisation staff sizes')
        ordering = ('order',)
