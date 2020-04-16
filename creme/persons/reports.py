# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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
from django.utils.translation import gettext_lazy as _, gettext

from creme.reports.core.graph.fetcher import GraphFetcher

from .constants import RGF_OWNED


class OwnedGraphFetcher(GraphFetcher):
    type_id = RGF_OWNED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = _('Belows to the Contact/User')

        if self.value:
            self.error = _('No value is needed.')

    def _aux_fetch_4_entity(self, entity, order, user):
        try:
            owner = entity.is_user
        except AttributeError:
            raise self.IncompatibleContentType(gettext(
                "The volatile link «Belows to the Contact/User» is only compatible with Contacts ; "
                "you should fix your blocks' configuration."
            ))

        if owner is None:
            raise self.UselessResult(
                'OwnedGraphFetcher is only useful for Contacts representing users (see field "is_user")'
            )

        return self.graph.fetch(
            extra_q=Q(user=owner), order=order, user=user,
        )

    @classmethod
    def choices(cls, model):
        yield '', _('Belows to the Contact/User')
