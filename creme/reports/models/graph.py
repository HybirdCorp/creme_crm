
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

#TODO: Ordonate imports
from creme.creme_core.models.entity import CremeEntity
from django.db.models.fields import PositiveIntegerField
from creme.creme_core.models.base import CremeModel
from django.db.models.fields import PositiveSmallIntegerField
from creme.reports.models.report import Report
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import CharField
from creme.reports.models.report import report_prefix_url
from django.utils.translation import ugettext_lazy as _


#class ReportGraphType(CremeModel):
#    type = PositiveSmallIntegerField(_(u'Type'))
#
#    class Meta:
#        app_label = 'reports'
#        verbose_name = _(u"Report's graph type")
#        verbose_name_plural  = _(u"Reports' graphs type")


#ReportGraph types
RGT_DAY    = 1
RGT_MONTH  = 2
RGT_YEAR   = 3
RGT_RANGE  = 4
RGT_FK     = 5

verbose_report_graph_types = {
    RGT_DAY    : _(u"By days"),
    RGT_MONTH  : _(u"By months"),
    RGT_YEAR   : _(u"By years"),
    RGT_RANGE  : _(u"By X days (has to be informed in days' field)"),
    RGT_FK     : _(u"By values"),
}


class ReportGraph(CremeEntity):
    name     = CharField(_(u'Name of the graph'), max_length=100)
    report   = ForeignKey(Report)
    abscissa = CharField(_(u'Abscissa axis'), max_length=100)
    ordinate = CharField(_(u'Ordinate axis'), max_length=100)
    type     = PositiveIntegerField(_(u'Type'))
#    type     = ForeignKey(ReportGraphType)
    days     = PositiveIntegerField(_(u'Days'), blank=True, null=True)

    class Meta:
        app_label = 'reports'
        verbose_name = _(u"Report's graph")
        verbose_name_plural  = _(u"Reports' graphs")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "%s/report/%s" % (report_prefix_url, self.id)#TODO: Change url

    def get_edit_absolute_url(self):
        return "%s/report/edit/%s" % (report_prefix_url, self.id)#TODO: Change url

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "%s/reports" % report_prefix_url#TODO: Change url or don't implement ?

    def get_delete_absolute_url(self):
        return "%s/report/delete/%s" % (report_prefix_url, self.id)#TODO: Change url or don't implement ?
