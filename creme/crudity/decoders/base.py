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

from typing import Iterable, Iterator, Optional, Type

from django.conf import settings

from creme.creme_core.utils.imports import safe_import_object

DecoderId = str


class CrudityDecoder:
    id: DecoderId = DecoderId('')  # Use generate_id()
    # verbose_name: str = 'DECODER'  # TODO: in child

    # def __init__(self, ...):

    @staticmethod
    def generate_id(app_label: str, name: str) -> DecoderId:
        # TODO
        # if BillingExporter.ID_SEPARATOR in name:
        #     raise ValueError(
        #         f'Invalid character for name: {BillingExporter.ID_SEPARATOR}'
        #     )

        return DecoderId(f'{app_label}-{name}')


class CrudityDecoderManager:
    class InvalidDecoderClass(Exception):
        pass

    def __init__(self, decoders_config: Optional[Iterable[str]] = None):
        self._decoders_config = (
            settings.CRUDITY_DECODERS
            if decoders_config is None else
            decoders_config
        )

    @property
    def decoder_classes(self) -> Iterator[Type[CrudityDecoder]]:
        for cls_path in self._decoders_config:
            cls = safe_import_object(cls_path)

            if cls is None:
                raise self.InvalidDecoderClass(
                    f'"{cls_path}" is an invalid path of <CrudityDecoder>.'
                )

            if not issubclass(cls, CrudityDecoder):
                raise self.InvalidDecoderClass(
                    f'{cls} is invalid, it is not a sub-class of <CrudityDecoder>.'
                )

            yield cls

    def decoder(self, decoder_id) -> Optional[CrudityDecoder]:
        for cls in self.decoder_classes:
            if cls.id == decoder_id:
                return cls()

        return None
