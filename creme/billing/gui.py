################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2020  Hybird
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

from creme import recurrents
from creme.creme_core.gui.listview import CreationButton


# TODO: limit generator to billing models ?
class GeneratorCreationButton(CreationButton):
    def get_model(self, lv_context):
        return recurrents.get_rgenerator_model()
