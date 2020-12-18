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

from creme.creme_core.http import CremeJsonResponse


class UIFeedback:
    type = ''

    def __init__(self, **kwargs):
        self.data = kwargs


class UIRedirect(UIFeedback):
    type = 'redirect'

    def __init__(self, to):
        super().__init__(url=to)


class UIReload(UIFeedback):
    type = 'reload'


class UINotify(UIFeedback):
    type = 'notify'

    def __init__(self, message):
        super().__init__(message=message)


class UIFeedbackResponse(CremeJsonResponse):
    def __init__(self, *commands):
        data = [
            {'command': c.type, 'data': c.data} for c in commands
        ]
        super().__init__(data, safe=False)
