import warnings

from .bricks import (
    ReportFieldsBrick as ReportFieldsBlock,
    ReportGraphsBrick as ReportGraphsBlock,
    ReportGraphBrick as ReportGraphBlock,
)

warnings.warn('reports.blocks is deprecated ; use reports.bricks instead.', DeprecationWarning)

report_fields_block = ReportFieldsBlock()
report_graphs_block = ReportGraphsBlock()
