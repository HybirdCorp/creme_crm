import warnings

from .bricks import add_graph_instance_brick as add_graph_instance_block

warnings.warn('reports.views.blocks is deprecated ; use reports.views.bricks instead.', DeprecationWarning)
