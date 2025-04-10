from __future__ import annotations

import logging
from dataclasses import dataclass

from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.media import creme_media_themed_url

logger = logging.getLogger(__name__)


# TODO : Add more properties here like icon size or shadow.
@dataclass
class GeoMarkerIcon:
    path: str = ''

    @property
    def url(self):
        try:
            return creme_media_themed_url(self.path) if self.path else ''
        except KeyError:
            logger.warning('Missing marker image: %s' % self.path)
            return ''


class GeoMarkerIconRegistry:
    __slots__ = ('_icons',)

    def __init__(self) -> None:
        self._icons: dict[type[CremeEntity], GeoMarkerIcon] = {}

    def register(
        self,
        model: type[CremeEntity],
        icon: GeoMarkerIcon | str
    ) -> GeoMarkerIconRegistry:
        self._icons[model] = GeoMarkerIcon(path=icon) if isinstance(icon, str) else icon
        return self

    def icon_for_model(self, model: type[CremeEntity]) -> GeoMarkerIcon:
        return self._icons.get(model, GeoMarkerIcon())

    def icon_for_instance(self, instance: CremeEntity):
        return self._icons.get(type(instance)) or GeoMarkerIcon()


geomarker_icon_registry = GeoMarkerIconRegistry()
