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

import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import JSONField
from creme.creme_core.models import CremeEntity
from creme.crudity import models
from creme.crudity.core import CRUDityExtractor, extractor_registry
from creme.crudity.fetchers import CrudityFetcherManager
from creme.crudity.registry import NEW_crudity_registry as crudity_registry

logger = logging.getLogger(__name__)


class CrudityExtractorsField(JSONField):
    value_type = list

    # widget = widgets.CrudityExtractorsWidget  TODO
    default_error_messages = {
        'invalidextractor': _('This extractor is invalid: %(error)s.'),
    }
    # _model = None

    def __init__(self, *,
                 model=CremeEntity,  # TODO: CremeModel ?
                 # extractor_registry=None,  TODO
                 **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.extractor_registry = extractor_registry

    # TODO
    # @property
    # def model(self):
    #     return self._model
    #
    # @model.setter
    # def model(self, model):
    #     self._model = model
    #     self.widget.ptypes = CallableChoiceIterator(
    #         lambda: [(pt.id, pt) for pt in self._get_ptypes()]
    #     )

    # TODO
    # def _value_to_jsonifiable(self, value):
    #     fields = self._get_fields()
    #     dicts = []
    #     field_choicetype = widgets.FieldConditionSelector.field_choicetype
    #
    #     for condition in value:
    #         search_info = condition.value
    #         operator_id = search_info['operator']
    #         operator = self.efilter_registry.get_operator(operator_id)
    #
    #         field = fields[condition.name][-1]
    #         field_entry = {'name': condition.name, 'type': field_choicetype(field)}
    #
    #         dicts.append({
    #             'field': field_entry,
    #             'operator': {
    #                 'id': operator_id,
    #                 'types': ' '.join(operator.allowed_fieldtypes),
    #             },
    #             'value': values,
    #         })
    #
    #     return dicts

    def _value_from_unjsonfied(self, data):
        # extractors = []

        try:
            # for entry in data:
            #     # TODO: use cell? rename 'cell_key'?
            #     # {'cell_key': 'regular_field-last_name', 'extractor_type': 'basic'}
            #
            #     try:
            #         cell_type_id, cell_name = entry['cell_key'].split('-', 1)
            #     except (ValueError, KeyError) as e:
            #         raise ValidationError(
            #             self.error_messages['invalidcellkey'],
            #             code='invalidcellkey',
            #         ) from e
            #
            #     # TODO: registry
            #     if cell_type_id == 'regular_field':
            #         extractors.append(RegularFieldExtractor(
            #             model=self.model,
            #             field_name=cell_name,
            #         ))
            #     elif cell_type_id == 'custom_field':
            #         extractors.append(CustomFieldExtractor(
            #             model=self.model,
            #             custom_field_id=cell_name,
            #         ))
            #     else:
            #         raise ValidationError(
            #             self.error_messages['invalidcellkey'],
            #             code='invalidcellkey',
            #         )
            extractors = [*self.extractor_registry.build_extractors(
                model=self.model,
                dicts=data,
            )]
        except CRUDityExtractor.InvalidExtractor as e:
            raise ValidationError(
                # self.error_messages['invalidcellvalue'],
                self.error_messages['invalidextractor'],
                # code='invalidcellvalue',
                params={'error': e},
                code='invalidextractor',
            ) from e

        return extractors


class FetcherItemCreationStep(CremeModelForm):
    class_id = forms.ChoiceField(label=_('Type of fetcher'))

    class Meta(CremeModelForm.Meta):
        model = models.FetcherConfigItem
        fields = ('class_id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_id'].choices = [
            (cls.id, cls.verbose_name) for cls in CrudityFetcherManager().fetcher_classes
        ]


class MachineItemCreationStep(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = models.MachineConfigItem
        fields = ('content_type', 'action_type', 'fetcher_item')
        exclude = ('json_extractors',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        fields['content_type'].ctypes = [
            *map(ContentType.objects.get_for_model, crudity_registry.models),
        ]

    def save(self):
        pass


class ExtractorsStep(CremeModelForm):
    extractors = CrudityExtractorsField(
        label=_('Extractors'),
        help_text=_('How to import external data'),
    )

    class Meta(CremeModelForm.Meta):
        model = models.MachineConfigItem
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['extractors'].model = self.instance.content_type.model_class()

    def save(self, *args, **kwargs):
        self.instance.extractors = self.cleaned_data['extractors']
