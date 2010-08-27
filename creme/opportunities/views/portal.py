# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext as _

from creme_core.views.generic import app_portal

from creme_config.utils.url_generator import generate_portal_url

from opportunities.models.opportunity import Opportunity


def portal(request):
    """
        @Permissions : Acces or Admin to opportunities app
    """
    stats = (
                (_(u"Number of opportunities"),  Opportunity.objects.all().count()),
            )

    return app_portal(request, 'opportunities', 'opportunities/portal.html',
                      Opportunity, stats, config_url=generate_portal_url('opportunities'))
