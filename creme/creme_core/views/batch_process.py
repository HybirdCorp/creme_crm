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

from logging import debug

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.forms.batch_process import BatchProcessForm
from creme_core.core.batch_process import batch_operator_manager
from creme_core.views.generic import add_entity
from creme_core.utils import get_ct_or_404, jsonify


@login_required
def batch_process(request, ct_id):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label): #TODO: factorise
        raise Http404(_(u"You are not allowed to acceed to this app"))

    try: #TODO: factorise
        callback_url = ct.model_class().get_lv_absolute_url()
    except AttributeError:
        debug('%s has no get_lv_absolute_url() method ?!' % ct.model_class())
        callback_url = '/'

    return add_entity(request, BatchProcessForm, callback_url,
                      template='creme_core/batch_process.html',
                      extra_initial={'content_type': ct},
                     )

@login_required
@jsonify
def get_ops(request, ct_id, field):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

    field = ct.model_class()._meta.get_field(field)

    return [(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(field.__class__)]
