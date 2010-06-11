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

from django.db.models import CharField, TextField, ForeignKey, DateTimeField, BooleanField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity

from recurrents.models import Periodicity


class RecurrentGenerator(CremeEntity):
    name             = CharField(_(u'Nom du générateur'), max_length=100, blank=True, null=True)
    description      = TextField(_(u'Description du générateur'), blank=True, null=True)
    first_generation = DateTimeField(_(u'Date de première génération récurrente'), blank=True, null=True)
    last_generation  = DateTimeField(_(u'Date de la dernière génération récurrente'), blank=True, null=True)
    periodicity      = ForeignKey(Periodicity, verbose_name=_(u'Périodicité de la génération'))
    ct               = ForeignKey(ContentType, verbose_name=_(u'Type de ressource recurrente'))
    template         = ForeignKey(CremeEntity, verbose_name=_(u'Modèle utilisé'), related_name='template_set')
    is_working       = BooleanField(_(u'Actif ?'), default=True)

    class Meta:
        app_label = 'recurrents'
        verbose_name = _(u'Générateur récurrent')
        verbose_name_plural = _(u'Générateurs récurrents')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/recurrents/generator/%s" % self.id

    def get_edit_absolute_url(self):
        return "/recurrents/generator/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/recurrents/generators"

    def get_delete_absolute_url(self):
        return "/recurrents/generator/delete/%s" % self.id
