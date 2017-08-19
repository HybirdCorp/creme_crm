import warnings

from .bricks import ResutsBrick as ResutsBlock

warnings.warn('events.blocks is deprecated ; use events.bricks instead.', DeprecationWarning)

resuts_block = ResutsBlock()
