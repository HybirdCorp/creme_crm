################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

from creme.creme_core import get_concrete_model


def rgenerator_model_is_custom():
    return (
        settings.RECURRENTS_RGENERATOR_MODEL != 'recurrents.RecurrentGenerator'
        and not settings.RECURRENTS_RGENERATOR_FORCE_NOT_CUSTOM
    )


def get_rgenerator_model():
    """Returns the RecurrentGenerator model that is active in this project."""
    return get_concrete_model('RECURRENTS_RGENERATOR_MODEL')
