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

from functools import partial

from django.http import HttpResponse
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
from ..models import EntityCredentials
from ..core.search import Searcher
from ..registry import creme_registry
from ..utils import get_ct_or_404


@login_required
def search(request):
    post_get = request.POST.get
    research = post_get('research')
    ct_id    = post_get('ct_id')

    t_ctx   = {}
    models  = []
    results = []
    total   = 0

    if not research:
        t_ctx['error_message'] = _(u"Empty search...")
    elif len(research) < 3:
        t_ctx['error_message'] = _(u"Please enter at least 3 characters")
    else:
        if not ct_id:
            models.extend(creme_registry.iter_entity_models())
            models.sort(key=lambda m: m._meta.verbose_name)
        else:
            models.append(get_ct_or_404(ct_id).model_class())

        user = request.user
        filter_viewable = partial(EntityCredentials.filter, user=user)
        searcher = Searcher(models, user)

        for model in models:
            entities = filter_viewable(queryset=searcher.search(model, research))
            total += len(entities)
            results.append({'model':    model,
                            'sfields':  searcher.get_fields(model),
                            'entities': entities,
                           }
                          )

    t_ctx['total'] = total
    t_ctx['results'] = results
    t_ctx['research'] = research
    t_ctx['models'] = [model._meta.verbose_name for model in models]

    return HttpResponse(render_to_string("creme_core/search_results.html", t_ctx, context_instance=RequestContext(request)))
#Not ajax version :
#    return render_to_response("creme_core/generics/search_results.html", t_ctx, context_instance=RequestContext(request))
