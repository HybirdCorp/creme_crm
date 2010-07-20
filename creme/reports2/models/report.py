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

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.db.models.fields import CharField, PositiveIntegerField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Filter, CremeModel

report_prefix_url   = '/reports2' #TODO : Remove me when remove reports app
report_template_dir = 'reports2' #TODO : Remove me when remove reports app

class Field(CremeModel):
    name   = CharField(_(u'Nom de la colonne'), max_length=100)
    title  = CharField(max_length=100)
    order  = PositiveIntegerField()
    type   = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}#Add in choices ?

    class Meta:
        app_label = 'reports2'
        verbose_name = _(u'Colone de rapport')
        verbose_name_plural  = _(u'Colonnes de rapport')

class Report2(CremeEntity):
    name    = CharField(_(u'Nom du rapport'), max_length=100)
    ct      = ForeignKey(ContentType, verbose_name=_(u"Type d'entité"))
    columns = ManyToManyField(Field, verbose_name=_(u"Colonnes affichées"))
    filter  = ForeignKey(Filter, verbose_name=_(u'Filtre'), blank=True, null=True)

    class Meta:
        app_label = 'reports2'
        verbose_name = _(u'Rapport')
        verbose_name_plural  = _(u'Rapports')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "%s/report/%s" % (report_prefix_url, self.id)

    def get_edit_absolute_url(self):
        return "%s/report/edit/%s" % (report_prefix_url, self.id)

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "%s/reports" % report_prefix_url

    def get_delete_absolute_url(self):
        return "%s/report/delete/%s" % (report_prefix_url, self.id)