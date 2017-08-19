import warnings

from .bricks import (
    list4url, str2list,
    _BrickContext as _BlockContext,
    Brick as Block,
    SimpleBrick as SimpleBlock,
    _PaginatedBrickContext as _PaginatedBlockContext,
    PaginatedBrick as PaginatedBlock,
    _QuerysetBrickContext as _QuerysetBlockContext,
    QuerysetBrick as QuerysetBlock,
    SpecificRelationsBrick as SpecificRelationsBlock,
    CustomBrick as CustomBlock,
    BricksManager as BlocksManager,
    _BrickRegistry as _BlockRegistry,
    brick_registry as block_registry,
)

warnings.warn('creme_core.gui.block is deprecated ; use creme_core.gui.bricks instead.', DeprecationWarning)
