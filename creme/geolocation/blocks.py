import warnings

from .bricks import (
    _MapBrick as _MapBlock,
    GoogleDetailMapBrick as PersonsMapsBlock,
    GoogleFilteredMapBrick as PersonsFiltersMapsBlock,
    GoogleNeighboursMapBrick as WhoisAroundMapsBlock,
)

warnings.warn('geolocation.blocks is deprecated ; use geolocation.bricks instead.', DeprecationWarning)

persons_maps_block        = PersonsMapsBlock()
persons_filter_maps_block = PersonsFiltersMapsBlock()
who_is_around_maps_block  = WhoisAroundMapsBlock()

block_list = (
    persons_maps_block,
    persons_filter_maps_block,
    who_is_around_maps_block,
)
