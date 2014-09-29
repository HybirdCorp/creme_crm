# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from itertools import chain

from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.models import CustomFieldEnumValue, CustomField
from creme.creme_core.utils import get_ct_or_404, jsonify

from creme.creme_config.registry import config_registry, NotRegisteredInConfig


@login_required
@jsonify
def json_list_enumerable(request, ct_id):
    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    if model is not User:
        app_name = ct.app_label

        if not request.user.has_perm(app_name):
            #raise Http404(_(u"You are not allowed to access to this app %s") % app_name)
            raise Http404(u"You are not allowed to access to the app '%s'" % app_name)

        try:
            config_registry.get_app(app_name).get_model_conf(ct.id)
        except (KeyError, NotRegisteredInConfig):
            #raise Http404(_(u"Content type is not registered in config"))
            raise Http404(u"Content type is not registered in config")

    return [(e.id, unicode(e)) for e in model.objects.all()]

@login_required
@jsonify
def json_list_userfilter(request):
    return list(chain((('__currentuser__', _('Current user')),),
                      ((e.id, unicode(e)) for e in User.objects.all()),
                     )
               )

@login_required
@jsonify
def json_list_enumerable_custom(request, cf_id):
    cf = get_object_or_404(CustomField, pk=cf_id)
    return list(CustomFieldEnumValue.objects.filter(custom_field=cf).values_list('id', 'value'))
