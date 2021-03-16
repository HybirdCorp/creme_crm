# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme import commercial
from creme.creme_core.gui import menu

from .models import MarketSegment

Act = commercial.get_act_model()
Strategy = commercial.get_strategy_model()
Pattern = commercial.get_pattern_model()


class ActsEntry(menu.ListviewEntry):
    id = 'commercial-acts'
    model = Act


class StrategiesEntry(menu.ListviewEntry):
    id = 'commercial-strategies'
    model = Strategy


class PatternsEntry(menu.ListviewEntry):
    id = 'commercial-patterns'
    model = Pattern


class SegmentsEntry(menu.ListviewEntry):
    id = 'commercial-segments'
    model = MarketSegment


class SalesmenEntry(menu.FixedURLEntry):
    id = 'persons-salesmen'
    label = _('Salesmen')
    url_name = 'commercial__list_salesmen'
    permissions = 'persons'


class ActCreationEntry(menu.CreationEntry):
    id = 'commercial-create_act'
    model = Act


class StrategyCreationEntry(menu.CreationEntry):
    id = 'commercial-create_strategy'
    model = Strategy


class PatternCreationEntry(menu.CreationEntry):
    id = 'commercial-create_pattern'
    model = Pattern
