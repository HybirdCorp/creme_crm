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

from django.conf.urls.defaults import patterns

urlpatterns = patterns('reports2.views',
    (r'^$', 'portal.portal'),
#
    (r'^reports$',                           'report.listview'),
    (r'^report/add$',                        'report.add'),
    (r'^report/edit/(?P<report_id>\d+)$',    'report.edit'),
    (r'^report/(?P<report_id>\d+)$',         'report.detailview'),
    (r'^report/(?P<report_id>\d+)/preview$', 'report.preview'),

    #Fields block
    (r'^(?P<report_id>\d+)/fields_block/reload/$',                                               'report.reload_fields_block'),
    (r'^report/field/unlink_report$',                                                            'report.unlink_report'),
    (r'^report/field/change_order$',                                                             'report.change_field_order'),
    (r'^report/(?P<report_id>\d+)/field/(?P<field_id>\d+)/link_report$',                         'report.link_report'),
    (r'^report/(?P<report_id>\d+)/field/(?P<field_id>\d+)/link_relation_report/(?P<ct_id>\d+)$', 'report.link_relation_report'),
    (r'^report/(?P<report_id>\d+)/field/add$',                                                   'report.add_field'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^report/delete/(?P<object_id>\d+)$', 'delete_entity'),
)