# -*- coding: utf-8 -*-

# from django.utils.translation import gettext_lazy as _
# from django.utils.translation import pgettext_lazy

REL_SUB_MAIL_RECEIVED = 'email-subject_mail_received'
REL_OBJ_MAIL_RECEIVED = 'email-object_mail_received'

REL_SUB_MAIL_SENDED = 'email-subject_mail_sended'
REL_OBJ_MAIL_SENDED = 'email-object_mail_sended'

REL_SUB_RELATED_TO = 'email-subject_related_to'
REL_OBJ_RELATED_TO = 'email-object_related_to'

DEFAULT_HFILTER_MAILINGLIST = 'emails-hf_mailinglist'
DEFAULT_HFILTER_CAMPAIGN    = 'emails-hf_campaign'
DEFAULT_HFILTER_TEMPLATE    = 'emails-hf_template'
DEFAULT_HFILTER_EMAIL       = 'emails-hf_email'

# MAIL_STATUS_SENT                 = 1
# MAIL_STATUS_NOTSENT              = 2
# MAIL_STATUS_SENDINGERROR         = 3
# MAIL_STATUS_SYNCHRONIZED         = 4
# MAIL_STATUS_SYNCHRONIZED_SPAM    = 5
# MAIL_STATUS_SYNCHRONIZED_WAITING = 6
#
# MAIL_STATUS = {
#     MAIL_STATUS_SENT:                 pgettext_lazy('emails', 'Sent'),
#     MAIL_STATUS_NOTSENT:              pgettext_lazy('emails', 'Not sent'),
#     MAIL_STATUS_SENDINGERROR:         _('Sending error'),
#     MAIL_STATUS_SYNCHRONIZED:         pgettext_lazy('emails', 'Synchronized'),
#     MAIL_STATUS_SYNCHRONIZED_SPAM:    _('Synchronized - Marked as SPAM'),
#     MAIL_STATUS_SYNCHRONIZED_WAITING: _('Synchronized - Untreated'),
# }
#
# MAIL_SYNC_STATUSES = {
#     MAIL_STATUS_SYNCHRONIZED,
#     MAIL_STATUS_SYNCHRONIZED_SPAM,
#     MAIL_STATUS_SYNCHRONIZED_WAITING,
# }

SETTING_EMAILCAMPAIGN_SENDER = 'emails-emailcampaign_sender'
