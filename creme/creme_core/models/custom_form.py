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

from json import loads as json_load
from typing import List

from django.db import models

from ..utils.serializers import json_encode


class CustomFormConfigItemManager(models.Manager):
    def create_if_needed(self, *, descriptor, groups_desc):
        """Creation helper (for "populate" scripts mainly).
        Create an instance of CustomFormConfigItem, related to a
        CustomFormDescriptor, if there is no one.
        """
        from ..gui.custom_form import FieldGroupList

        cform_id = descriptor.id
        item = self.filter(cform_id=cform_id).first()

        if item is None:
            item = self.model(cform_id=cform_id)
            item.store_groups(FieldGroupList.from_cells(
                model=descriptor.model,
                data=groups_desc,
                cell_registry=descriptor.build_cell_registry(),
                allowed_extra_group_classes=(*descriptor.extra_group_classes,)
            ))
            item.save()

        return item


class CustomFormConfigItem(models.Model):
    """Store the fields/groups of fields in the custom-form system.
    See also: <creme_core.gui.custom_form>.
    """
    cform_id = models.CharField(primary_key=True, max_length=100, editable=False)
    json_groups = models.TextField(editable=False, null=True)  # TODO: JSONField ?

    objects = CustomFormConfigItemManager()

    def groups_as_dicts(self) -> List[dict]:
        return json_load(self.json_groups)

    def store_groups(self, groups):
        self.json_groups = json_encode([group.as_dict() for group in groups])
