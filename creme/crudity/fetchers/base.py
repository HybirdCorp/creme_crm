################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from __future__ import annotations

# from collections import defaultdict
from typing import Iterable, Iterator  # DefaultDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from creme.creme_core.utils.imports import safe_import_object

# from ..inputs.base import CrudityInput
FetcherId = str


# class CrudityFetcher:
#     _inputs: DefaultDict[str, dict[str, CrudityInput]]
#
#     def __init__(self, *args, **kwargs):
#         self._inputs = defaultdict(dict)
#
#     def register_inputs(self, *inputs: CrudityInput) -> None:
#         for input in inputs:
#             self._inputs[input.name][input.method] = input
#
#     def fetch(self, *args, **kwargs) -> Iterable:
#         """Make the fetcher do his job.
#         @returns: iterable of fetcher managed type
#                   (i.e: emails objects for email fetcher for example).
#         """
#         raise NotImplementedError


class NEWCrudityFetcher:
    id: FetcherId = FetcherId('')  # Use generate_id()
    verbose_name: str = 'FETCHER'  # TODO: in child

    def __init__(self, options):
        self.options = options

    # TODO
    # def fetch(self, *args, **kwargs) -> Iterable:
    #     """Make the fetcher do his job.
    #     @returns: iterable of fetcher managed type
    #               (i.e: emails objects for email fetcher for example).
    #     """
    #     raise NotImplementedError

    @staticmethod
    def generate_id(app_label: str, name: str) -> FetcherId:
        # TODO
        # if BillingExporter.ID_SEPARATOR in name:
        #     raise ValueError(
        #         f'Invalid character for name: {BillingExporter.ID_SEPARATOR}'
        #     )

        return FetcherId(f'{app_label}-{name}')

    # TODO: class attribute instead
    @classmethod
    def options_form(cls, **kwargs):
        raise NotImplementedError

    # TODO: unit test children
    # TODO: property?
    def verbose_options(self):
        raise NotImplementedError


class CrudityFetcherManager:
    # TODO: if error in GUI?
    # class InvalidFetcherClass(Exception):
    #     pass

    def __init__(self, fetchers_config: Iterable[str] | None = None):
        self._fetchers_config = (
            settings.CRUDITY_FETCHERS
            if fetchers_config is None else
            fetchers_config
        )

    # TODO: factorise? cache imported classes?
    @property
    def fetcher_classes(self) -> Iterator[type[NEWCrudityFetcher]]:
        for cls_path in self._fetchers_config:
            cls = safe_import_object(cls_path)

            if cls is None:
                # raise self.InvalidFetcherClass(
                #     f'"{cls_path}" is an invalid path of <CrudityFetcher>.'
                # )
                raise ImproperlyConfigured(
                    f'"{cls_path}" is an invalid path of <CrudityFetcher> '
                    f'(see CRUDITY_FETCHERS).'
                )

            if not issubclass(cls, NEWCrudityFetcher):
                # raise self.InvalidFetcherClass(
                #     f'{cls} is invalid, it is not a sub-class of <CrudityFetcher>.'
                # )
                raise ImproperlyConfigured(
                    f'"{cls_path}" is not a <CrudityFetcher> sub-class '
                    f'(see CRUDITY_FETCHERS).'
                )

            yield cls

    def fetcher(self, *, fetcher_id: FetcherId, fetcher_data: dict) -> NEWCrudityFetcher | None:
        for cls in self.fetcher_classes:
            if cls.id == fetcher_id:
                return cls(options=fetcher_data)

                # TODO: error message if None? Exception?

        return None


# TODO: if cached classes
# crudity_fetcher_manager = CrudityFetcherManager()
