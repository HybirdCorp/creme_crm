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

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SearchConfigItem
from creme.creme_core.utils import get_from_POST_or_404, get_ct_or_404
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup

from ..forms.search import SearchEditForm, SearchAddForm


@login_required
@permission_required('creme_core.can_admin')
def add(request, ct_id):
    ctype = get_ct_or_404(ct_id)

    return add_model_with_popup(request, SearchAddForm,
                                title=_(u'New search configuration for «%s»') % ctype,
                                submit_label=_('Save the configuration'),
                                initial={'content_type': ctype},
                               )

@login_required
#@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/search_portal.html')

@login_required
@permission_required('creme_core.can_admin')
def edit(request, search_config_id):
    return edit_model_with_popup(request, query_dict={'pk': search_config_id},
                                 model=SearchConfigItem, form_class=SearchEditForm,
                                )

@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    sci = get_object_or_404(SearchConfigItem, id=get_from_POST_or_404(request.POST, 'id'))

#    if sci.user is None:
    if sci.is_default:
        raise ConflictError("You cannot delete the default configuration")

    sci.delete()

    return HttpResponse()
