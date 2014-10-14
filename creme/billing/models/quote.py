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

from django.db.models import ForeignKey, DateField, PROTECT
from django.utils.translation import ugettext_lazy as _

from .base import Base
from .other_models import QuoteStatus


class Quote(Base):
    status           = ForeignKey(QuoteStatus, verbose_name=_(u'Status of quote'), on_delete=PROTECT)
    acceptation_date = DateField(_(u"Acceptation date"), blank=True, null=True).set_tags(clonable=False)

    creation_label = _('Add a quote')

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
        tpl_status_id = template.status_id
        self.status = QuoteStatus.objects.get_or_create(pk=tpl_status_id,
                                                        defaults={'name': 'N/A',
                                                                  'order': tpl_status_id,
                                                                 },
                                                       )[0]
        return super(Quote, self).build(template)

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Quote')
        verbose_name_plural = _(u'Quotes')
