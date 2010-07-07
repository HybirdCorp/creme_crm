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

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from creme_core.models.search import SearchConfigItem, SearchField, DEFAULT_PATTERN
from creme_core.registry import creme_registry
from creme_core.utils.meta import get_flds_with_fk_flds_str

from creme_config.forms.search import EXCLUDED_FIELDS_TYPES


BASE_Q = Q(is_deleted=False)


def _build_research(model, research, is_or=True):
    """Build a Q with all (non excluded in EXCLUDED_FIELDS) model's fields"""
    q = Q()
    fields = get_flds_with_fk_flds_str(model, 1, exclude_func=lambda f: f.get_internal_type() in EXCLUDED_FIELDS_TYPES or f.name in model.header_filter_exclude_fields)
    for f_name, f_verb_name in fields:
        _q = Q(**{'%s%s' % (f_name, DEFAULT_PATTERN):research})
        if is_or:
            q |= _q
        else:
            q &= _q
    return {'q' : BASE_Q & q, 'fields' : fields}

@login_required
def search(request):
    POST = request.POST

    research = POST.get('research')
    ct_id = POST.get('ct_id')

    t_ctx   = {}
    scope   = []
    results = []

    if not research:
        t_ctx['error_message'] = _(u"Recherche vide...")
    elif len(research) < 3:
        t_ctx['error_message'] = _(u"Veuillez entrer au moins 3 caractères")
    else:
        if not ct_id:
            scope = creme_registry.iter_entity_models()
        else:
            scope.append(ContentType.objects.get_for_id(ct_id).model_class())

        ct_get_for_model = ContentType.objects.get_for_model
        SCI_get = SearchConfigItem.objects.get
        user = request.user
        
        for model in scope:
            res_dict = {'model':model}
            model_filter = model.objects.filter(BASE_Q).filter
            try:
                #Trying to catch the user's research config for this model
                sci = SCI_get(content_type=ct_get_for_model(model), user=user)
                res_dict['fields']  = sci.get_fields()

                #No fields, the get_q will act as .all() so we try another search config
                if not res_dict['fields']:
                    raise SearchConfigItem.DoesNotExist

                #TODO: Needs values_list?
                res_dict['results'] = model_filter(sci.get_q(research))
            except SearchConfigItem.DoesNotExist:
                try:
                    #Trying to catch the model's research config
                    sci = SCI_get(content_type=ct_get_for_model(model))
                    res_dict['fields']  = sci.get_fields()
                    
                    #No fields, the get_q will act as .all() so we try another search config
                    if not res_dict['fields']:
                        raise SearchConfigItem.DoesNotExist


                    #TODO: Needs values_list?
                    res_dict['results'] = model_filter(sci.get_q(research))
                except SearchConfigItem.DoesNotExist:
                    #The research will be on all unexcluded fields
                    srch_infos = _build_research(model, research)
#                    res_dict['fields']  = [{'field': f_name,'field_verbose_name': f_verb_name} for f_name, f_verb_name in search_infos['fields']]
                    #Needed to match the SearchField api in template
                    res_dict['fields']  = [SearchField(field=f_name, field_verbose_name=f_verbname, order=i) for i, (f_name, f_verbname) in enumerate(srch_infos['fields'])]
                    res_dict['fields'].sort(key=lambda k: k.order)
                    #TODO: Needs values_list?
                    res_dict['results'] = model_filter(srch_infos['q'])
            results.append(res_dict)

    t_ctx['results'] = results
    t_ctx['research'] = research
    t_ctx['models'] = [mod._meta.verbose_name for mod in scope]

    return HttpResponse(render_to_string("creme_core/generics/search_results.html", t_ctx, context_instance=RequestContext(request)))
#Not ajax version :
#    return render_to_response("creme_core/generics/search_results.html", t_ctx, context_instance=RequestContext(request))
