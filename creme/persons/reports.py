################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from django.db.models import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from creme.reports.core.graph.fetcher import GraphFetcher
from creme.reports.core.chart.fetcher import ChartFetcher

# from .constants import RGF_OWNED
from . import get_contact_model

Contact = get_contact_model()


# class OwnedGraphFetcher(GraphFetcher):
class OwnedChartFetcher(ChartFetcher):
    # type_id = RGF_OWNED
    type_id = 'persons-owned'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = _('Belongs to the Contact/User')

        if self.value:
            self.error = _('No value is needed.')

    def _aux_fetch_4_entity(self, entity, order, user):
        if not isinstance(entity, Contact):
            raise self.IncompatibleContentType(gettext(
                "The volatile link «Belongs to the Contact/User» is only "
                "compatible with Contacts; you should fix your blocks' configuration."
            ))

        owner = entity.is_user
        if owner is None:
            # NB: should never happen with 'linked_models' checked correctly before...
            raise self.UselessResult(
                f'{type(self).__name__} is only useful for Contacts representing users '
                f'(see field "is_user")'
            )

        # return self.graph.fetch(
        #     extra_q=Q(user=owner), order=order, user=user,
        # )
        return self.chart.fetch(
            extra_q=Q(user=owner), order=order, user=user,
        )

    @classmethod
    def choices(cls, model):
        yield '', _('Belongs to the Contact/User')

    @property
    def linked_models(self):
        return [Contact]
