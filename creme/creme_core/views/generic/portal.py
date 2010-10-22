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

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity


@login_required
def app_portal(request, app_name, template, models, stats, config_url=None, extra_template_dict=None):
    if not request.user.has_perm(app_name):
        raise PermissionDenied(_(u'You are not allowed to access to the app: %s') % app_name)

    get_ct = ContentType.objects.get_for_model

    try:
        ct_ids = [get_ct(model).id for model in models]
    except TypeError: #models is a not a sequence -> CremeEntity
        ct_ids = [get_ct(models).id]

    template_dict = {
                        'ct_ids':       ct_ids,
                        'stats':        stats,
                        'config_url':   config_url,
                    }

    if extra_template_dict is not None:
        template_dict.update(extra_template_dict)

    return render_to_response(template,
                              template_dict,
                              context_instance=RequestContext(request))
