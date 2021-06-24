# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2021  Hybird
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
#############################################################################

import warnings
from datetime import timedelta

from django import template

from ..models.history import TYPE_CREATION, TYPE_EDITION, HistoryLine

register = template.Library()


@register.simple_tag
def history_summary(*, entity, user):
    lines = HistoryLine.objects.filter(entity=entity.id)
    stored_hlines = []

    creation = lines.filter(type=TYPE_CREATION).first()
    if creation is not None:
        stored_hlines.append(creation)
    else:
        creation = HistoryLine(
            entity=entity, entity_ctype=entity.entity_type, type=TYPE_CREATION,
            date=entity.created,
            username='',
        )

    last_edition = lines.filter(type=TYPE_EDITION).order_by('-date').first()
    # NB: even at creation, entity.created & entity.modified are never exactly
    #     equal (is it a problem ?).
    if last_edition is not None:
        stored_hlines.append(last_edition)
    elif (entity.modified - entity.created) > timedelta(seconds=3):
        last_edition = HistoryLine(
            entity=entity, entity_ctype=entity.entity_type, type=TYPE_EDITION,
            date=entity.modified,
            username='',
        )

    HistoryLine.populate_users(stored_hlines, user)

    return {
        'creation': creation,
        'last_edition': last_edition,
    }


@register.filter
def history_modifications(history_line, user):
    warnings.warn(
        'The template filter "|history_modifications" is deprecated. '
        'Hint: see creme_core.bricks.HistoryBrick.',
        DeprecationWarning
    )

    return history_line.get_verbose_modifications(user)
