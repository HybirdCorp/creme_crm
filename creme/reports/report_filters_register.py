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

from datetime import date

from django.utils.translation import ugettext as _

from reports.registry import ReportDatetimeFilter

def last_year_beg(filter, now):
    return date(year=now.year-1, month=1, day=1)

def last_year_end(filter, now):
    return date(year=now.year-1, month=12, day=31)



to_register = (
    ('customized', ReportDatetimeFilter('customized', _(u"Customized"), lambda x,y: "", lambda x,y: "")),
    ('last_year', ReportDatetimeFilter('last_year', _(u"Last year"), last_year_beg, last_year_end)),

)


