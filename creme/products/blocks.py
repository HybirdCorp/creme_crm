import warnings

from .bricks import ImagesBrick as ImagesBlock

warnings.warn('products.blocks is deprecated ; use products.bricks instead.', DeprecationWarning)

images_block = ImagesBlock()
