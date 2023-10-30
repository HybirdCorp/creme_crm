################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from creme.creme_core.core.notification import RelatedToModelBaseContent
from creme.emails import get_emailcampaign_model


class CampaignSentContent(RelatedToModelBaseContent):
    id = RelatedToModelBaseContent.generate_id('emails', 'campaign_sent')
    subject_template_name = 'emails/notifications/campaign_sent/subject.txt'
    body_template_name = 'emails/notifications/campaign_sent/body.txt'
    html_body_template_name = 'emails/notifications/campaign_sent/body.html'

    model = get_emailcampaign_model()
