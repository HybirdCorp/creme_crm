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


def emailcampaign_model_is_custom():
    return (
        settings.EMAILS_CAMPAIGN_MODEL != 'emails.EmailCampaign'
        and not settings.EMAILS_CAMPAIGN_FORCE_NOT_CUSTOM
    )


def emailtemplate_model_is_custom():
    return (
        settings.EMAILS_TEMPLATE_MODEL != 'emails.EmailTemplate'
        and not settings.EMAILS_TEMPLATE_FORCE_NOT_CUSTOM
    )


def entityemail_model_is_custom():
    return (
        settings.EMAILS_EMAIL_MODEL != 'emails.EntityEmail'
        and not settings.EMAILS_EMAIL_FORCE_NOT_CUSTOM)


def mailinglist_model_is_custom():
    return (
        settings.EMAILS_MLIST_MODEL != 'emails.MailingList'
        and not settings.EMAILS_MLIST_FORCE_NOT_CUSTOM
    )


def get_emailcampaign_model():
    """Returns the EmailCampaign model that is active in this project."""
    return get_concrete_model('EMAILS_CAMPAIGN_MODEL')


def get_emailtemplate_model():
    """Returns the EmailTemplate model that is active in this project."""
    return get_concrete_model('EMAILS_TEMPLATE_MODEL')


def get_entityemail_model():
    """Returns the EntityEmail model that is active in this project."""
    return get_concrete_model('EMAILS_EMAIL_MODEL')


def get_mailinglist_model():
    """Returns the MailingList model that is active in this project."""
    return get_concrete_model('EMAILS_MLIST_MODEL')
