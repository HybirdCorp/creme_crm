# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021 Hybird
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

import logging
# from json import loads as json_load
from typing import List, Optional

from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _

from ..core.deletion import REPLACERS_MAP, Replacer, ReplacersRegistry
# from ..utils.serializers import json_encode
from .base import CremeModel
from .fields import CTypeOneToOneField
from .job import Job

logger = logging.getLogger(__name__)


def CREME_REPLACE_NULL(collector, field, sub_objs, using):
    """Can be used as value for <on_delete> attribute of ForeignKeys.
    It's equivalent to regular Django's SET_NULL, but creme_config
    will propose to replace the deleted value by another instance
    (<NULL> is proposed too).
    """
    collector.add_field_update(field, None, sub_objs)


def CREME_REPLACE(collector, field, sub_objs, using):
    """Can be used as value for <on_delete> attribute of ForeignKeys.
    It's equivalent to regular Django's PROTECT, but creme_config
    will propose to replace the deleted value by another instance.
    """
    raise models.ProtectedError(
        _('Cannot delete some instances of model «{model}» because they are '
          'referenced through a protected foreign key: «{related} - {field}»').format(
            model=field.remote_field.model.__name__,
            related=type(sub_objs[0])._meta.verbose_name,
            field=field.verbose_name,
        ),
        sub_objs
    )

# TODO ?
# def CREME_REPLACE_CHOICES/SET(collector, field, sub_objs, using):


class DeletionCommand(CremeModel):
    """Information used by the 'Deletor' job to know which instance
    to delete, & which instances use as replacements.
    """
    # NB: using <content_type> as PK assures us that we cannot delete several
    #     instances of the same model concurrently, with potential issues like
    #    dependency loops (eg: replace A with B, B with C, C with A arg).
    content_type = CTypeOneToOneField(editable=False, primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, editable=False)
    pk_to_delete = models.TextField(editable=False)

    # NB: representation of the deleted instance (for UI)
    deleted_repr = models.TextField(editable=False)

    # json_replacers = models.TextField(editable=False, default='[]')
    # TODO: encoder=CremeJSONEncoder ?
    json_replacers = models.JSONField(default=list, editable=False)
    total_count = models.PositiveIntegerField(default=0, editable=False)  # NB: for statistics
    updated_count = models.PositiveIntegerField(default=0, editable=False)  # NB: for statistics

    class Meta:
        app_label = 'creme_core'
        # verbose_name = 'Deletion command'
        # verbose_name_plural = 'Deletion commands'

    replacers_registry: ReplacersRegistry

    def __init__(self, *args, replacers_registry: Optional[ReplacersRegistry] = None, **kwargs):
        self.replacers_registry = replacers_registry or REPLACERS_MAP
        super().__init__(*args, **kwargs)

    @property
    def instance_to_delete(self) -> models.Model:
        return self.content_type.model_class()._default_manager.get(pk=self.pk_to_delete)

    @instance_to_delete.setter
    def instance_to_delete(self, instance: models.Model):
        self.content_type = type(instance)
        self.pk_to_delete = str(instance.pk)
        self.deleted_repr = str(instance)

    @property
    def replacers(self) -> List[Replacer]:
        "@return List of <creme_core.core.deletion.Replacer> instances."
        # return self.replacers_registry.deserialize(json_load(self.json_replacers))
        return self.replacers_registry.deserialize(self.json_replacers)

    @replacers.setter
    def replacers(self, values: List[Replacer]):
        "@param: List of <creme_core.core.deletion.Replacer> instances."
        # self.json_replacers = json_encode(self.replacers_registry.serialize(values))
        self.json_replacers = self.replacers_registry.serialize(values)


class TrashCleaningCommand(CremeModel):
    """Useful to warranty that one user does not try to flush the trash several
    times in the same time.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True, editable=False, on_delete=models.CASCADE,
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, editable=False)
    deleted_count = models.PositiveIntegerField(default=0, editable=False)  # NB: for statistics

    class Meta:
        app_label = 'creme_core'
        # verbose_name = 'Trash cleaning command'
        # verbose_name_plural = 'Trash cleaning commands'
