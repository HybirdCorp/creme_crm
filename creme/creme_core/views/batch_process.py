# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
#from .generic import add_entity
from ..utils import get_ct_or_404, jsonify


@login_required
def batch_process(request, ct_id):
    ct = get_ct_or_404(ct_id)
    user = request.user

    #if not request.user.has_perm(ct.app_label):
    if not user.has_perm(ct.app_label): #TODO: factorise
        raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

    #try: #todo: factorise
        #callback_url = ct.model_class().get_lv_absolute_url()
    #except AttributeError:
        #debug('%s has no get_lv_absolute_url() method ?!' % ct.model_class())
        #callback_url = '/'

    #return add_entity(request, BatchProcessForm, callback_url,
                      #template='creme_core/batch_process.html',
                      #extra_initial={'content_type': ct},
                     #)

    if request.method == 'POST':
        POST = request.POST
        bp_form = BatchProcessForm(user=user, data=request.POST, initial={'content_type': ct}) #TODO: make 'content_type' a real arg ?

        if bp_form.is_valid():
            bp_form.save()

            return render(request, 'creme_core/batch_process_report.html',
                          {'form':     bp_form,
                           'back_url': request.GET.get('list_url', '/'),
                          }
                         )

        cancel_url = POST.get('cancel_url')
    else:
        bp_form = BatchProcessForm(user=user, initial={'content_type': ct})
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
        raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

    field = ct.model_class()._meta.get_field(field)

    return [(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(field.__class__)]
