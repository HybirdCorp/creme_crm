# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.shortcuts import render
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
from ..core.batch_process import batch_operator_manager
from ..forms.batch_process import BatchProcessForm
from ..gui.listview import ListViewState
from ..utils import get_ct_or_404, jsonify


@login_required
def batch_process(request, ct_id):
    ct = get_ct_or_404(ct_id)
    user = request.user

    if not user.has_perm(ct.app_label):  # TODO: factorise
        raise PermissionDenied(_(u"You are not allowed to access to this app"))

    if request.method == 'POST':
        POST = request.POST
        # TODO: make 'content_type' a real arg ?
        bp_form = BatchProcessForm(user=user, data=request.POST, initial={'content_type': ct})

        if bp_form.is_valid():
            bp_form.save()

            return render(request, 'creme_core/batch_process_report.html',
                          {'form':     bp_form,
                           'back_url': request.GET.get('list_url', '/'),
                          }
                         )

        cancel_url = POST.get('cancel_url')
    else:
        efilter_id = None
        list_url = request.GET.get('list_url')

        if list_url:
            lvs = ListViewState.get_state(request, url=list_url)

            if lvs:
                efilter_id = lvs.entity_filter_id

        bp_form = BatchProcessForm(user=user,
                                   initial={'content_type': ct,
                                            'filter': efilter_id,
                                           }
                                  )
        cancel_url = request.META.get('HTTP_REFERER')

    return render(request, 'creme_core/batch_process.html',
                  {'form':          bp_form,
                   'submit_label':  _('Run'),
                   'cancel_url':    cancel_url,
                  }
                 )


@login_required
@jsonify
def get_ops(request, ct_id, field):
    ct = get_ct_or_404(ct_id)

    if not request.user.has_perm(ct.app_label):
        raise PermissionDenied(_(u"You are not allowed to access to this app"))

    field = ct.model_class()._meta.get_field(field)

    return [(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(field.__class__)]
