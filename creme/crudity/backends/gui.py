################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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

from django.template.loader import get_template

from .models import CrudityBackend


class BrickHeaderAction:
    def render(self, backend: CrudityBackend) -> str:
        raise NotImplementedError


class TemplateBrickHeaderAction(BrickHeaderAction):
    template_name = 'OVERRIDE ME'

    def __init__(self, template_name: str | None = None):
        super().__init__()
        if template_name is not None:
            self.template_name = template_name

    def render(self, backend):
        return get_template(self.template_name).render({'backend': backend})
