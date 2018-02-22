# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from .. import get_service_model
from .base import _BaseForm, _BaseEditForm  # _BaseCreateForm

Service = get_service_model()


# class ServiceCreateForm(_BaseCreateForm):
#     class Meta(_BaseCreateForm.Meta):
#         model = Service
class ServiceCreateForm(_BaseForm):
    class Meta(_BaseForm.Meta):
        model = Service


class ServiceEditForm(_BaseEditForm):
    class Meta(_BaseEditForm.Meta):
        model = Service
