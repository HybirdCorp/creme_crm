# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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


def activity_model_is_custom():
    return (
        settings.ACTIVITIES_ACTIVITY_MODEL != 'activities.Activity'
        and not settings.ACTIVITIES_ACTIVITY_FORCE_NOT_CUSTOM
    )


def get_activity_model():
    """Returns the Activity model that is active in this project."""
    return get_concrete_model('ACTIVITIES_ACTIVITY_MODEL')


# default_app_config = 'creme.activities.apps.ActivitiesConfig'
