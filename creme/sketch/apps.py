################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2023  Hybird
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

from django.conf import settings

from creme.creme_core.apps import CremeAppConfig


class SketchConfig(CremeAppConfig):
    default = True
    name = "creme.sketch"
    verbose_name = "Sketch"
    credentials = CremeAppConfig.CRED_NONE
    dependencies = ["creme.creme_core"]

    def register_bricks(self, brick_registry):
        from . import bricks

        if settings.SKETCH_ENABLE_DEMO_BRICKS:
            brick_registry.register(
                bricks.DemoGroupBarChartBrick,
                bricks.DemoBarChartBrick,
                bricks.DemoStackBarChartBrick,
                bricks.DemoDonutChartBrick,
                bricks.DemoLineChartBrick,
            )
