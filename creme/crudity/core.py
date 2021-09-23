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

from typing import Type

from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext as _

from creme.creme_core.models import CustomField, CustomFieldValue

# TODO: factorise with EntityCells?


class CRUDityExtractor:
    type_id = ''

    class InvalidExtractor(Exception):
        pass

    def __init__(self, *, model, value):
        self.model = model
        self.value = value

    # TODO: complete?
    def __eq__(self, other):
        return (
            self.model == other.model
            and self.value == other.value
        )

    def extract(self, instance, data):
        raise NotImplementedError

    def to_dict(self):
        # return {'key': self.type_id, 'value': self.value}
        return {'key': f'{self.type_id}-{self.value}'}  # TODO: only string if no more info


class CRUDityExtractorRegistry:
    def __init__(self):
        self._extractor_classes = {}

    def build_extractors(self, model, dicts):
        for data in dicts:
            # TODO: use <'extractor_type': 'basic'>

            try:
                # cell_key = data['cell_key']
                cell_key = data['key']
            except KeyError as e:
                # raise CRUDityExtractor.InvalidExtractor('the cell key is missing') from e
                raise CRUDityExtractor.InvalidExtractor('the key is missing') from e

            try:
                # cell_type_id, cell_name = cell_key.split('-', 1)
                type_id, value = cell_key.split('-', 1)
            except ValueError as e:
                raise CRUDityExtractor.InvalidExtractor(
                    # f'the cell key "{cell_key}" is malformed'
                    f'the key "{cell_key}" is malformed'
                ) from e

            # cls = self._extractor_classes.get(cell_type_id)
            cls = self._extractor_classes.get(type_id)
            if cls is None:
                raise CRUDityExtractor.InvalidExtractor(
                    # f'the type ID "{cell_type_id}" is invalid'
                    f'the type ID "{type_id}" is invalid'
                )

            # yield cls(model=model, value=cell_name)
            yield cls(model=model, value=value)

    def register(self, extractor_class: Type[CRUDityExtractor]):
        self._extractor_classes[extractor_class.type_id] = extractor_class

        return extractor_class


extractor_registry = CRUDityExtractorRegistry()


@extractor_registry.register
class RegularFieldExtractor(CRUDityExtractor):
    type_id = 'regular_field'

    def __init__(self, *, model, value):
        super().__init__(model=model, value=value)

        try:
            self.model._meta.get_field(value)
        except FieldDoesNotExist as e:
            # raise self.InvalidExtractor(str(e)) from e
            raise self.InvalidExtractor(
                _('the field with name "{}" is invalid').format(value)
            ) from e

    @property
    def field_name(self):
        return self.value

    def extract(self, instance, data):
        # TODO: what about empty values (override even in edition mode or with default value)?
        name = self.value
        try:
            value = data[name]
        except KeyError:
            pass
        else:
            setattr(instance, name, value)


@extractor_registry.register
class CustomFieldExtractor(CRUDityExtractor):
    type_id = 'custom_field'

    def __init__(self, *, model, value):
        super().__init__(model=model, value=value)
        # TODO: assert is entity subclass?

        try:
            # TODO: use cache?
            custom_field = CustomField.objects.get(id=value)
        except CustomField.DoesNotExist as e:
            raise self.InvalidExtractor(
                _('the custom-field with id="{}" does not exist').format(value)
            ) from e

        self.custom_field = custom_field

    def extract(self, instance, data):
        # TODO: assert is entity?
        # TODO: what about empty values?
        cfield = self.custom_field
        try:
            value = data[f'custom_field-{cfield.id}']
        except KeyError:
            pass
        else:
            CustomFieldValue.save_values_for_entities(cfield, [instance], value)
