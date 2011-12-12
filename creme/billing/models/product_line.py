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

from django.utils.translation import ugettext_lazy as _

from line import Line, PRODUCT_LINE_TYPE


class ProductLine(Line):
    def __init__(self, *args, **kwargs):
        super(ProductLine, self).__init__(*args, **kwargs)
        self.type = PRODUCT_LINE_TYPE

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Product line')
        verbose_name_plural = _(u'Product lines')

    def __unicode__(self):
        if self.related_item:
            return u"Related to product '%s'" % self.related_item
        return u"On the fly product '%s'" % self.on_the_fly_item
