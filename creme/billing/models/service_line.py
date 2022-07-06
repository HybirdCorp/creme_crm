################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.products import get_service_model

from .line import Line


class AbstractServiceLine(Line):
    creation_label = _('Create a service line')

    class Meta(Line.Meta):
        abstract = True
        verbose_name = _('Service line')
        verbose_name_plural = _('Service lines')

    def __str__(self):
        if self.on_the_fly_item:
            return gettext('On the fly service «{}»').format(self.on_the_fly_item)

        if self.id:
            return gettext('Related to service «{}»').format(self.related_item)

        return 'Unsaved service line'

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_service_lines')

    @staticmethod
    def related_item_class():
        return get_service_model()


class ServiceLine(AbstractServiceLine):
    class Meta(AbstractServiceLine.Meta):
        swappable = 'BILLING_SERVICE_LINE_MODEL'
