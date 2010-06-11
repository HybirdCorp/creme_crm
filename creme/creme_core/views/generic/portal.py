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

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.entities_access.permissions import user_has_acces_to_application


@login_required
def app_portal(request, app_name, template, models, stats, config_url=None, extra_template_dict=None):
    """
    @param models A class inheriting CremeEntity, or a sequence of classes inheriting CremeEntity
    """
    if not user_has_acces_to_application(request, app_name):
        return render_to_response('creme_core/forbidden.html', {},
                                  context_instance=RequestContext(request))

    try:
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(model).id for model in models]
    except TypeError: #models is a not a sequence -> CremeEntity
        ct_ids = [ContentType.objects.get_for_model(models).id]

    template_dict = {
                        'ct_ids':       ct_ids,
                        'stats':        stats,
                        'config_url':   config_url, #structure_creme.get_app_config(app_name) instead ????
                    }

    if extra_template_dict is not None:
        template_dict.update(extra_template_dict)

    return render_to_response(template,
                              template_dict,
                              context_instance=RequestContext(request))
