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

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CTypeForeignKey


# TODO: encrypt data with secret key
class FetcherConfigItem(CremeModel):
    class_id = models.TextField()
    options = models.JSONField(default=dict)

    class Meta:
        app_label = 'crudity'
        ordering = ('id',)

    # TODO: unit test
    def __str__(self):
        fetcher = self.fetcher
        option = next(fetcher.verbose_options(), None)
        return (
            str(fetcher.verbose_name)
            if option is None else
            f'{fetcher.verbose_name} ({option})'
        )

    def __repr__(self):
        # Not "options" to avoid information leaks
        return f'FetcherConfigItem(class_id="{self.class_id}")'

    @property
    def fetcher(self):
        from ..fetchers import CrudityFetcherManager

        class_id = self.class_id

        return CrudityFetcherManager().fetcher(
            fetcher_id=class_id,
            fetcher_data=self.options,
        ) if class_id else None

    # TODO?
    # @fetcher.setter
    # def fetcher(self, fetcher):


class MachineConfigItem(CremeModel):
    class CRUDAction(models.IntegerChoices):
        CREATE = 1, _('Create'),
        UPDATE = 2, _('Update'),
        DELETE = 3, _('Delete'),

    content_type = CTypeForeignKey(verbose_name=_('Resource type'))
    action_type = models.PositiveSmallIntegerField(
        verbose_name=_('Action type'),
        choices=CRUDAction.choices,
        default=CRUDAction.CREATE,
    )
    fetcher_item = models.ForeignKey(FetcherConfigItem, on_delete=models.PROTECT)
    json_extractors = models.JSONField(default=list)

    creation_label = pgettext_lazy('crudity', 'Create a machine')
    save_label     = pgettext_lazy('crudity', 'Save the machine')

    class Meta:
        app_label = 'crudity'
        # TODO: unique_together?

    def __str__(self):
        return (
            f'{type(self).__name__}('
            f'content_type=<{self.content_type}>, '
            f'action_type={self.action_type}, '
            f'fetcher_item={self.fetcher_item_id}, '
            f'json_extractors={self.json_extractors}'
            f')'
        )

    @property
    def extractors(self):
        from ..core import extractor_registry

        return [*extractor_registry.build_extractors(
            model=self.content_type.model_class(),
            dicts=self.json_extractors,
        )]

    @extractors.setter
    def extractors(self, extractors):
        # TODO: assert model are equal to self.content_type.model_class()?

        self.json_extractors = [
            extractor.to_dict() for extractor in extractors
        ]
