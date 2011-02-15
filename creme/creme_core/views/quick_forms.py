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
from django.http import Http404
from django.forms.formsets import formset_factory
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import inner_popup
from creme_core.gui.quick_forms import quickforms_registry
from creme_core.utils import get_ct_or_404


#TODO: it seems there is a problem with formsets : if the 'user' field is empty
#      it does not raise a Validation exception, but it causes a SQL integrity
#      error ; we are saved by the 'empty_label=None' of user field, but it is
#      not really perfect...

@login_required
def add(request, ct_id, count):
    model = get_ct_or_404(ct_id).model_class()
    model_name = model._meta.verbose_name
    user = request.user

    if not user.has_perm_to_create(model):
        #TODO: manage/display error on js side (for now it just does nothing)
        raise PermissionDenied('You are not allowed to create entity with type "%s"' % model_name)

    try:
        base_form_class = quickforms_registry.get_form(model)
    except KeyError, e:
        raise Http404('No form registered for model: %s' % model)

    #we had the mandatory 'user' argument
    class _QuickForm(base_form_class):
        def __init__(self, *args, **kwargs):
            base_form_class.__init__(self, user=user, *args, **kwargs)

    qformset_class = formset_factory(_QuickForm, extra=int(count))

    if request.method == 'POST':
        qformset = qformset_class(request.POST)

        if qformset.is_valid():
            for form in qformset.forms: #TODO: django1.3 -> "for form in qformset:"
                form.save()
    else:
        qformset = qformset_class()

    return inner_popup(request, 'creme_core/generics/blockformset/add_popup.html',
                       {
                        'formset': qformset,
                        'title':   _('Quick creation of <%s>') % model_name,
                       },
                       is_valid=qformset.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))
