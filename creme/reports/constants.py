# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import gettext_lazy as _

DEFAULT_HFILTER_REPORT = 'reports-hf'

DATETIME_FILTER_FORMAT = '%d|%m|%Y|%H|%M|%S'

# ReportField types
RFT_FIELD      = 1
RFT_RELATION   = 2
RFT_FUNCTION   = 3
RFT_CUSTOM     = 4
RFT_AGG_FIELD  = 5
RFT_AGG_CUSTOM = 6
# TODO: used only in reports for the moment, integrate into HeaderFilters ?
RFT_RELATED    = 7  # Related entities (only allowed by the model)


# ReportGraph types (abscissa)
# RGT_DAY             = 1
# RGT_MONTH           = 2
# RGT_YEAR            = 3
# RGT_RANGE           = 4
# RGT_FK              = 5
# RGT_RELATION        = 6
# RGT_CUSTOM_DAY      = 11
# RGT_CUSTOM_MONTH    = 12
# RGT_CUSTOM_YEAR     = 13
# RGT_CUSTOM_RANGE    = 14
# RGT_CUSTOM_FK       = 15
#
# GROUP_TYPES = {
#     RGT_DAY:            _('By days'),
#     RGT_MONTH:          _('By months'),
#     RGT_YEAR:           _('By years'),
#     RGT_RANGE:          _('By X days'),
#     RGT_FK:             _('By values'),
#     RGT_RELATION:       _('By values (of related entities)'),
#     RGT_CUSTOM_DAY:     _('By days (custom field)'),
#     RGT_CUSTOM_MONTH:   _('By months (custom field)'),
#     RGT_CUSTOM_YEAR:    _('By years (custom field)'),
#     RGT_CUSTOM_RANGE:   _('By X days (custom field)'),
#     RGT_CUSTOM_FK:      _('By values (of custom choices)'),
# }
class AbscissaGroup(models.IntegerChoices):
    DAY          = 1,  _('By days'),
    MONTH        = 2,  _('By months'),
    YEAR         = 3,  _('By years'),
    RANGE        = 4,  _('By X days'),
    FK           = 5,  _('By values'),
    RELATION     = 6,  _('By values (of related entities)'),
    CUSTOM_DAY   = 11, _('By days (custom field)'),
    CUSTOM_MONTH = 12, _('By months (custom field)'),
    CUSTOM_YEAR  = 13, _('By years (custom field)'),
    CUSTOM_RANGE = 14, _('By X days (custom field)'),
    CUSTOM_FK    = 15, _('By values (of custom choices)'),


# ReportGraph aggregators (ordinate)
# RGA_COUNT = 'count'
# RGA_AVG   = 'avg'
# RGA_MAX   = 'max'
# RGA_MIN   = 'min'
# RGA_SUM   = 'sum'
#
# AGGREGATOR_TYPES = {
#     RGA_COUNT: _('Count'),
#     RGA_AVG:   _('Average'),
#     RGA_MAX:   _('Maximum'),
#     RGA_MIN:   _('Minimum'),
#     RGA_SUM:   _('Sum'),
# }
class OrdinateAggregator(models.TextChoices):
    COUNT = 'count', _('Count'),
    AVG   = 'avg',   _('Average'),
    MAX   = 'max',   _('Maximum'),
    MIN   = 'min',   _('Minimum'),
    SUM   = 'sum',   _('Sum'),


# ReportGraph fetchers
RGF_NOLINK   = 'reports-no_link'
RGF_FK       = 'reports-fk'
RGF_RELATION = 'reports-relation'
