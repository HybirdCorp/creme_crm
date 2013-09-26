# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import Http404

from creme.creme_core.utils import get_ct_or_404, jsonify

from creme.creme_config.registry import config_registry, NotRegisteredInConfig


@login_required
@jsonify
def json_list_all(request, ct_id):
    ct = get_ct_or_404(ct_id)
    app_name = ct.app_label

    if not request.user.has_perm(app_name):
        raise Http404(_(u"You are not allowed to acceed to this app %s") % app_name)

    model = ct.model_class()

    if model is not User:
        try:
            model = config_registry.get_app(app_name).get_model_conf(ct.id).model
        except (KeyError, NotRegisteredInConfig):
            raise Http404(_(u"Content type is not registered in config"))

    return [(e.id, unicode(e)) for e in model.objects.all()]
