# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _


DEFAULT_HFILTER_REPORT = 'reports-hf'

DATETIME_FILTER_FORMAT = '%d|%m|%Y|%H|%M|%S'

# ReportField types
RFT_FIELD      = 1
RFT_RELATION   = 2
RFT_FUNCTION   = 3
RFT_CUSTOM     = 4
RFT_AGG_FIELD  = 5
RFT_AGG_CUSTOM = 6
RFT_RELATED    = 7  # Related entities (only allowed by the model)
                    # TODO: used only in reports for the moment, integrate into HeaderFilters ?


# ReportGraph types
RGT_DAY             = 1
RGT_MONTH           = 2
RGT_YEAR            = 3
RGT_RANGE           = 4
RGT_FK              = 5
RGT_RELATION        = 6
RGT_CUSTOM_DAY      = 11
RGT_CUSTOM_MONTH    = 12
RGT_CUSTOM_YEAR     = 13
RGT_CUSTOM_RANGE    = 14
RGT_CUSTOM_FK       = 15

GROUP_TYPES = {
    RGT_DAY:            _(u'By days'),
    RGT_MONTH:          _(u'By months'),
    RGT_YEAR:           _(u'By years'),
    RGT_RANGE:          _(u'By X days'),
    RGT_FK:             _(u'By values'),
    RGT_RELATION:       _(u'By values (of related entities)'),
    RGT_CUSTOM_DAY:     _(u'By days (custom field)'),
    RGT_CUSTOM_MONTH:   _(u'By months (custom field)'),
    RGT_CUSTOM_YEAR:    _(u'By years (custom field)'),
    RGT_CUSTOM_RANGE:   _(u'By X days (custom field)'),
    RGT_CUSTOM_FK:      _(u'By values (of custom choices)'),
}
