from django.db import models
from django.utils.translation import gettext_lazy as _

DEFAULT_HFILTER_REPORT = 'reports-hf'

DATETIME_FILTER_FORMAT = '%d|%m|%Y|%H|%M|%S'

EF_REPORTS = 'reports-report'

# models.report.Field.type values
RFT_FIELD      = 1
RFT_RELATION   = 2
RFT_FUNCTION   = 3
RFT_CUSTOM     = 4
RFT_AGG_FIELD  = 5
RFT_AGG_CUSTOM = 6
# TODO: used only in reports for the moment, integrate into HeaderFilters ?
RFT_RELATED    = 7  # Related entities (only allowed by the model)


class AbscissaGroup(models.IntegerChoices):
    DAY          = 1,  _('By days'),
    MONTH        = 2,  _('By months'),
    YEAR         = 3,  _('By years'),
    RANGE        = 4,  _('By X days'),
    FK           = 5,  _('By values (configurable)'),
    RELATION     = 6,  _('By values (of related entities)'),
    CHOICES      = 7,  _('By values (not configurable)'),
    CUSTOM_DAY   = 11, _('By days (custom field)'),
    CUSTOM_MONTH = 12, _('By months (custom field)'),
    CUSTOM_YEAR  = 13, _('By years (custom field)'),
    CUSTOM_RANGE = 14, _('By X days (custom field)'),
    CUSTOM_FK    = 15, _('By values (of custom choices)'),


class OrdinateAggregator(models.TextChoices):
    COUNT = 'count', _('Count'),
    AVG   = 'avg',   _('Average'),
    MAX   = 'max',   _('Maximum'),
    MIN   = 'min',   _('Minimum'),
    SUM   = 'sum',   _('Sum'),


# # ReportGraph fetchers
# RGF_NOLINK   = 'reports-no_link'
# RGF_FK       = 'reports-fk'
# RGF_RELATION = 'reports-relation'
