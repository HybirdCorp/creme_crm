################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from creme.creme_core.core.entity_filter import EF_REGULAR, condition_handler
from creme.creme_core.forms.entity_filter import fields as form_fields
from creme.reports.constants import EF_REPORTS


class ReportRelationSubfiltersConditionsField(form_fields.RelationSubfiltersConditionsField):
    sub_filter_types = [EF_REGULAR, EF_REPORTS]


class ReportSubfiltersConditionsField(form_fields.SubfiltersConditionsField):
    sub_filter_types = [EF_REGULAR, EF_REPORTS]


# TODO: it would be better to pass the handler class to the form-field;
#       the field uses the class-method build_condition(), but we do not override
#       it so it works fine, but the design is not totally satisfactory.
class ReportRelationSubFilterConditionHandler(condition_handler.RelationSubFilterConditionHandler):
    # TODO: form class as class attribute?
    @classmethod
    def formfield(cls, form_class=ReportRelationSubfiltersConditionsField, **kwargs):
        return super().formfield(form_class=form_class, **kwargs)


class ReportSubFilterConditionHandler(condition_handler.SubFilterConditionHandler):
    # TODO: form class as class attribute?
    @classmethod
    def formfield(cls, form_class=ReportSubfiltersConditionsField, **kwargs):
        return super().formfield(form_class=form_class, **kwargs)
