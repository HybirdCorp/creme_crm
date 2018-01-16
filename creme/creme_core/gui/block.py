import warnings

from .bricks import (
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


def list4url(list_):
    "Special url list-to-string function"
    warnings.warn('creme_core.gui.block.list4url() is deprecated.', DeprecationWarning)
    return ','.join(str(i) for i in list_)


def str2list(string):
    "'1,2,3'  -> [1, 2, 3]"
    warnings.warn('creme_core.gui.block.str2list() is deprecated.', DeprecationWarning)
    return [int(i) for i in string.split(',') if i.isdigit()]


warnings.warn('creme_core.gui.block is deprecated ; use creme_core.gui.bricks instead.', DeprecationWarning)
