# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core.gui.bricks import SimpleBrick

from . import get_event_model


class EventBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'events/bricks/event-hat-bar.html'


# class ResutsBrick(SimpleBrick):
class ResultsBrick(SimpleBrick):
    id_ = SimpleBrick.generate_id('events', 'results')
    # dependencies  = (Relation,) ??
    verbose_name = _('Results of an event')
    template_name = 'events/bricks/results.html'
    target_ctypes = (get_event_model(),)
