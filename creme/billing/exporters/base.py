# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    NewType,
    Optional,
    Type,
    Union,
)

from django.conf import settings

from creme.creme_core.utils.imports import safe_import_object

if TYPE_CHECKING:
    from django.http import HttpResponse

    from creme.creme_core.models import CremeEntity, FileRef

logger = logging.getLogger(__name__)
AGNOSTIC = 'AGNOSTIC'
FlavourId = str
EngineId = str
ExporterId = NewType('ExporterId', str)


class ExporterFlavour:
    """Variation to use for a given engine."""
    def __init__(self, country='', language='', theme=''):
        """Constructor.
        @param country: country code (eg: 'FR').
        @param language: language code (eg: 'fr_FR').
        @param theme: name of the theme
        """
        self.country = country
        self.language = language
        self.theme = theme

    def __eq__(self, other):
        return (
            self.country == other.country
            and self.language == other.language
            and self.theme == other.theme
        )

    def __repr__(self):
        return f'ExporterFlavour("{self.country}", "{self.language}", "{self.theme}")'

    @classmethod
    def agnostic(cls) -> 'ExporterFlavour':
        "A variation not related to a country or a language."
        return cls(country=AGNOSTIC)

    def as_id(self) -> FlavourId:
        "Get a string ID."
        return FlavourId(f'{self.country}/{self.language}/{self.theme}')

    @classmethod
    def from_id(cls, flavour_id: FlavourId) -> 'ExporterFlavour':
        """Get an instance from an ID."""
        return cls(*flavour_id.split('/', 2))


class BillingExporter:
    """Base class for exporters.
    Exporters can take a billing entity model and produce output files
    (generally PDF, by using third party libraries).
    """
    ID_SEPARATOR = '|'

    def __init__(self, *,
                 verbose_name: str,
                 engine: 'BillingExportEngine',
                 flavour: ExporterFlavour):
        self.verbose_name = verbose_name
        self.engine = engine
        self.flavour = flavour

    def export(self, *,
               entity: 'CremeEntity',
               user) -> Union['FileRef', 'HttpResponse']:
        raise NotImplementedError()

    @property
    def id(self) -> ExporterId:
        return ExporterId(
            f'{self.engine.id}{self.ID_SEPARATOR}{self.flavour.as_id()}'
        )

    @property
    def screenshots(self) -> Iterator[str]:
        """Get resources paths to screenshots.
        Useful to illustrate choices in configurations GUI.
        """
        raise NotImplementedError()


class BillingExportEngine:
    """Base class for exporter engines.
    An engine can create <BillingExporter> instances for a given variation (flavour).
    """
    id: EngineId = EngineId('')  # Use generate_id()

    def __init__(self, model: Type['CremeEntity']):
        self.model = model

    def exporter(self, flavour: ExporterFlavour) -> BillingExporter:
        raise NotImplementedError()

    @property
    def flavours(self) -> Iterator[ExporterFlavour]:
        """Different flavours an engine supports.
        Used by the configuration GUI.
        """
        raise NotImplementedError()

    @staticmethod
    def generate_id(app_label: str, name: str) -> EngineId:
        if BillingExporter.ID_SEPARATOR in name:
            raise ValueError(
                f'Invalid character for name: {BillingExporter.ID_SEPARATOR}'
            )

        return EngineId(f'{app_label}-{name}')


class BillingExportEngineManager:
    """Manage the list of all available types of engine."""
    class InvalidEngineClass(Exception):
        pass

    def __init__(self, engine_paths: Optional[Iterable[str]] = None):
        """Constructor.
        @param engine_paths: paths to Python classes inheriting
               <BillingExportEngine>. If <None>, the setting "BILLING_EXPORTERS"
               is used.
        """
        self.engine_paths = (
            settings.BILLING_EXPORTERS
            if engine_paths is None else
            [*engine_paths]
        )

    @property
    def engine_classes(self) -> Iterator[Type[BillingExportEngine]]:
        for path in self.engine_paths:
            cls = safe_import_object(path)

            if cls is None:
                raise self.InvalidEngineClass(
                    f'"{path}" is an invalid path of <BillingExportEngine>.'
                )

            if not issubclass(cls, BillingExportEngine):
                raise self.InvalidEngineClass(
                    f'{cls} is invalid, it is not a sub-class of <BillingExportEngine>.'
                )

            yield cls

    def engine(self, *,
               engine_id: EngineId,
               model: Type['CremeEntity']) -> Optional[BillingExportEngine]:
        for cls in self.engine_classes:
            if cls.id == engine_id:
                return cls(model)

        return None

    def exporter(self, *,
                 engine_id: EngineId,
                 flavour_id: FlavourId,
                 model: Type['CremeEntity']) -> Optional[BillingExporter]:
        engine = self.engine(engine_id=engine_id, model=model)

        return None if engine is None else engine.exporter(
            flavour=ExporterFlavour.from_id(flavour_id),
        )
