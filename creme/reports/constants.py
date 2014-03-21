# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

DATETIME_FILTER_FORMAT = '%d|%m|%Y|%H|%M|%S'

#ReportField types
RFT_FIELD      = 1
RFT_RELATION   = 2
RFT_FUNCTION   = 3
RFT_CUSTOM     = 4
#RFT_AGGREGATE  = 5
RFT_AGG_FIELD  = 5
RFT_AGG_CUSTOM = 6
RFT_RELATED    = 7 #Related entities (only allowed by the model) #TODO: Used only in reports for the moment, integrate into HF?


#ReportGraph types
RGT_DAY             = 1
RGT_MONTH           = 2
RGT_YEAR            = 3
RGT_RANGE           = 4
RGT_FK              = 5
RGT_RELATION        = 6
RGT_CUSTOM_DAY      = 11
RGT_CUSTOM_MONTH    = 12
RGT_CUSTOM_YEAR     = 13
RGT_CUSTOM_RANGE    = 14
RGT_CUSTOM_FK       = 15

