# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.db.models import ForeignKey, PROTECT
from django.utils.translation import ugettext_lazy as _

from base import Base
from other_models import QuoteStatus


class Quote(Base):
    status = ForeignKey(QuoteStatus, verbose_name=_(u'Status of quote'), on_delete=PROTECT, default=1)

    research_fields = Base.research_fields + ['status__name']
    excluded_fields_in_html_output = Base.excluded_fields_in_html_output + ['base_ptr']
    header_filter_exclude_fields = Base.header_filter_exclude_fields + ['base_ptr'] #TODO: use a set() ??

    def get_absolute_url(self):
        return "/billing/quote/%s" % self.id

    def get_edit_absolute_url(self):
        return "/billing/quote/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/billing/quotes"

    def build(self, template):
        # Specific recurrent generation rules
        self.status = QuoteStatus.objects.get(pk = template.status_id) #TODO: self.status_id = template.status_id ??
        return super(Quote, self).build(template)

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Quote')
        verbose_name_plural = _(u'Quotes')
