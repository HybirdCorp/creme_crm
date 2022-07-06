################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

from django.conf import settings

from creme.creme_core import get_concrete_model


def smscampaign_model_is_custom():
    return (
        settings.SMS_CAMPAIGN_MODEL != 'sms.SMSCampaign'
        and not settings.SMS_CAMPAIGN_FORCE_NOT_CUSTOM
    )


def messaginglist_model_is_custom():
    return (
        settings.SMS_MLIST_MODEL != 'sms.MessagingList'
        and not settings.SMS_MLIST_FORCE_NOT_CUSTOM
    )


def messagetemplate_model_is_custom():
    return (
        settings.SMS_TEMPLATE_MODEL != 'sms.MessageTemplate'
        and not settings.SMS_TEMPLATE_FORCE_NOT_CUSTOM
    )


def get_smscampaign_model():
    """Returns the SMSCampaign model that is active in this project."""
    return get_concrete_model('SMS_CAMPAIGN_MODEL')


def get_messaginglist_model():
    """Returns the MessagingList model that is active in this project."""
    return get_concrete_model('SMS_MLIST_MODEL')


def get_messagetemplate_model():
    """Returns the MessageTemplate model that is active in this project."""
    return get_concrete_model('SMS_TEMPLATE_MODEL')
