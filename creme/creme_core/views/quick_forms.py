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

from django.http import Http404
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import inner_popup
from creme_core.gui.quick_forms import quickforms_registry
from creme_core.utils import get_ct_or_404

#TODO: credentials ??

@login_required
def add(request, ct_id, count):
    model = get_ct_or_404(ct_id).model_class()

    try:
        form_class = quickforms_registry.get_form(model)
    except KeyError, e:
        raise Http404('No form registered for model: %s' % model)

    if request.POST:
        qform = form_class(request.POST)

        if qform.is_valid():
            qform.save()
    else:
        qform = form_class()

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   qform,
                        'title':  _('Quick creation of <%s>') % model._meta.verbose_name,
                       },
                       is_valid=qform.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))
