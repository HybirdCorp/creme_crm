# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.utils.translation import ugettext_lazy as _, pgettext_lazy


REL_SUB_MAIL_RECEIVED = 'email-subject_mail_received'
REL_OBJ_MAIL_RECEIVED = 'email-object_mail_received'

REL_SUB_MAIL_SENDED = 'email-subject_mail_sended'
REL_OBJ_MAIL_SENDED = 'email-object_mail_sended'

REL_SUB_RELATED_TO = 'email-subject_related_to'
REL_OBJ_RELATED_TO = 'email-object_related_to'

MAIL_STATUS_SENT                 = 1
MAIL_STATUS_NOTSENT              = 2
MAIL_STATUS_SENDINGERROR         = 3
MAIL_STATUS_SYNCHRONIZED         = 4
MAIL_STATUS_SYNCHRONIZED_SPAM    = 5
MAIL_STATUS_SYNCHRONIZED_WAITING = 6

MAIL_STATUS = {
                MAIL_STATUS_SENT:                 pgettext_lazy('emails', u'Sent'),
                MAIL_STATUS_NOTSENT:              pgettext_lazy('emails', u"Not sent"),
                MAIL_STATUS_SENDINGERROR:         _(u"Sending error"),
                MAIL_STATUS_SYNCHRONIZED:         pgettext_lazy('emails', u"Synchronized"),
                MAIL_STATUS_SYNCHRONIZED_SPAM:    _(u"Synchronized - Marked as SPAM"),
                MAIL_STATUS_SYNCHRONIZED_WAITING: _(u"Synchronized - Untreated"),
              }
