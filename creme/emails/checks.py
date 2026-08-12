################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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
from django.core.checks import Error, register

from creme.creme_core.checks import Tags


@register(Tags.settings)
def check_sending_settings(**kwargs):
    errors = []

    # Old settings ---
    if hasattr(settings, 'EMAILCAMPAIGN_SIZE'):
        errors.append(Error(
            'You still use the settings EMAILCAMPAIGN_SIZE',
            hint='Set EMAILS_CAMPAIGN_SIZE instead then remove EMAILCAMPAIGN_SIZE.',
            obj='emails',
            id='creme.emails.E001',
        ))

    if hasattr(settings, 'EMAILCAMPAIGN_SLEEP_TIME'):
        errors.append(Error(
            'You still use the settings EMAILCAMPAIGN_SIZE',
            hint='Set EMAILS_CAMPAIGN_SLEEP_TIME instead then remove EMAILCAMPAIGN_SLEEP_TIME.',
            obj='emails',
            id='creme.emails.E001',
        ))

    # EMAILS_CAMPAIGN_SIZE ---
    size = settings.EMAILS_CAMPAIGN_SIZE
    if not isinstance(size, int) or size < 1:
        errors.append(Error(
            'The settings EMAILS_CAMPAIGN_SIZE must be a strictly positive integer',
            hint='Set a correct value, like <EMAILS_CAMPAIGN_SIZE = 40>',
            obj='emails',
            id='creme.emails.E001',
        ))

    # EMAILS_CAMPAIGN_SLEEP_TIME ---
    sleep_time = settings.EMAILS_CAMPAIGN_SLEEP_TIME
    if not isinstance(sleep_time, (int, float)) or float(sleep_time) < 1.0:
        errors.append(Error(
            'The settings EMAILS_CAMPAIGN_SLEEP_TIME must be a number >= 1',
            hint='Set a correct value, like <EMAILS_CAMPAIGN_SLEEP_TIME = 2>',
            obj='emails',
            id='creme.emails.E001',
        ))

    return errors
