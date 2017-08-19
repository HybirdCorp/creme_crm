import warnings

from .bricks import (
    RootNodesBrick as RootNodesBlock,
    OrbitalRelationTypesBrick as OrbitalRelationTypesBlock,
)

warnings.warn('graphs.blocks is deprecated ; use graphs.bricks instead.', DeprecationWarning)

root_nodes_block     = RootNodesBlock()
orbital_rtypes_block = OrbitalRelationTypesBlock()
