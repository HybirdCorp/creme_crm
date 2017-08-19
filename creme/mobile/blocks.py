import warnings

from .bricks import FavoritePersonsBrick as FavoritePersonsBlock

warnings.warn('mobile.blocks is deprecated ; use mobile.bricks instead.', DeprecationWarning)

favorite_persons_block = FavoritePersonsBlock()
