# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from functools import partial

from django.http import HttpResponse
from django.db.models import Q
#from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import EntityCredentials
from creme_core.models.search import SearchConfigItem, SearchField, DEFAULT_PATTERN
from creme_core.registry import creme_registry
from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.utils import get_ct_or_404

from creme_config.forms.search import EXCLUDED_FIELDS_TYPES #humm...


BASE_Q = Q(is_deleted=False)

#TODO: move as SearchConfigItem method ??
def _build_q_research(model, research, fields, is_or=True):
    """Build a Q with all params fields"""
    q = Q()
#    for f_name, f_verb_name in fields:
    for f in fields:
        _q = Q(**{'%s%s' % (str(f.field), DEFAULT_PATTERN): research})
        if is_or:
            q |= _q
        else:
            q &= _q

    return BASE_Q & q

#TODO: move as SearchConfigItem method ??
def _get_research_fields(model, user):
    sc_items = SearchConfigItem.objects.filter(content_type=ContentType.objects.get_for_model(model)) \
                                       .filter(Q(user=user) | Q(user__isnull=True)) \
                                       .order_by('-user') #config of the user has higher priority than default one

    for sc_item in sc_items:
        fields  = sc_item.get_fields()
        if fields:
            return fields

    #The research will be on all unexcluded fields
    _fields = get_flds_with_fk_flds_str(model, 1, exclude_func=lambda f: f.get_internal_type() in EXCLUDED_FIELDS_TYPES or f.name in model.header_filter_exclude_fields)
    #Needed to match the SearchField api in template
    fields  = [SearchField(field=f_name, field_verbose_name=f_verbname, order=i) for i, (f_name, f_verbname) in enumerate(_fields)]
    fields.sort(key=lambda k: k.order)
    return fields

@login_required
def search(request):
    post_get = request.POST.get
    research = post_get('research')
    ct_id    = post_get('ct_id')

    t_ctx   = {}
    scope   = []
    results = []
    total   = 0

    if not research:
        t_ctx['error_message'] = _(u"Empty search...")
    elif len(research) < 3:
        t_ctx['error_message'] = _(u"Please enter at least 3 characters")
    else:
        if not ct_id:
            scope = list(creme_registry.iter_entity_models())
            scope.sort(key=lambda m: m._meta.verbose_name)
        else:
#            scope.append(ContentType.objects.get_for_id(ct_id).model_class())
            scope.append(get_ct_or_404(ct_id).model_class())

        user = request.user
        filter_viewable = partial(EntityCredentials.filter, user=user)

        for model in scope:
            fields   = _get_research_fields(model, user) #TODO: regroup queries ??
            entities = filter_viewable(queryset=model.objects.filter(BASE_Q)
                                                             .filter(_build_q_research(model, research, fields))
                                                             .distinct()
                                      )
            total += len(entities)

            results.append({
                'model':    model,
                'fields':   fields,
                'entities': entities
            })

    t_ctx['total'] = total
    t_ctx['results'] = results
    t_ctx['research'] = research
    t_ctx['models'] = [mod._meta.verbose_name for mod in scope]

    return HttpResponse(render_to_string("creme_core/search_results.html", t_ctx, context_instance=RequestContext(request)))
#Not ajax version :
#    return render_to_response("creme_core/generics/search_results.html", t_ctx, context_instance=RequestContext(request))
