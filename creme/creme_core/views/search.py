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

#from functools import partial
from time import time

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, Http404
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _, ungettext

from ..auth.decorators import login_required
from ..core.search import Searcher
from ..gui.block import QuerysetBlock
from ..models import CremeEntity, EntityCredentials
from ..registry import creme_registry
from ..utils import get_ct_or_404, jsonify


MIN_RESEARCH_LENGTH = 3


class FoundEntitiesBlock(QuerysetBlock):
    #dependencies  = (CremeProperty,) #TODO: ??
    template_name = 'creme_core/templatetags/block_found_entities.html'

    def __init__(self, searcher, model, research, user, id=None):
        self.searcher = searcher
        self.model = model
        self.research = research
        self.user = user
        self.ctype = ctype = ContentType.objects.get_for_model(model)
        self.id_ = id or self.generate_id('creme_core',
                                          'found-%s-%s-%s' % (
                                                ctype.app_label,
                                                ctype.model,
                                                int(time()), #we generate an unique ID for each research, in order
                                                             # to avoid sharing state (eg: page number) between researches.
                                            )
                                         )

    @staticmethod
    def parse_block_id(block_id):
        "@return A ContentType instance if valid, else None"
        parts = block_id.split('-')
        ctype = None

        if len(parts) == 5 and parts[4]:
            try:
                tmp_ctype = ContentType.objects.get_by_natural_key(parts[2], parts[3])
            except ContentType.DoesNotExist:
                pass
            else:
                if issubclass(tmp_ctype.model_class(), CremeEntity):
                    ctype = tmp_ctype

        return ctype

    def detailview_display(self, context):
        model = self.model
        meta = model._meta
        verbose_name = meta.verbose_name
        research = self.research
        searcher = self.searcher
        btc = self.get_block_template_context(
                    context,
                    EntityCredentials.filter(self.user, searcher.search(model, research)),
                    update_url='/creme_core/search/reload_block/%s/%s' % (self.id_, research),
                    sfields=searcher.get_fields(model),
                    ctype=self.ctype, #if the model is inserted in the context, the template call it and create an instance...
                    short_title=verbose_name,
                )

        count = btc['page'].paginator.count
        btc['title'] = _('%(count)s %(model)s') % {
                            'count': count,
                            'model': ungettext(verbose_name, meta.verbose_name_plural, count),
                        }

        return self._render(btc)


#TODO: GET method ??
@login_required
def search(request):
    post_get = request.POST.get
    research = post_get('research')
    ct_id    = post_get('ct_id')

    t_ctx   = {}
    models  = []
    #results = []
    #total   = 0
    blocks  = []

    if not research:
        t_ctx['error_message'] = _(u"Empty search…")
    elif len(research) < MIN_RESEARCH_LENGTH:
        t_ctx['error_message'] = _(u"Please enter at least %s characters") % MIN_RESEARCH_LENGTH
    else:
        if not ct_id:
            models.extend(creme_registry.iter_entity_models())
            models.sort(key=lambda m: m._meta.verbose_name)
        else:
            models.append(get_ct_or_404(ct_id).model_class())

        user = request.user
        #filter_viewable = partial(EntityCredentials.filter, user=user)
        searcher = Searcher(models, user)

        #for model in models:
            #entities = filter_viewable(queryset=searcher.search(model, research))
            #total += len(entities)
            #results.append({'model':    model,
                            #'sfields':  searcher.get_fields(model),
                            #'entities': entities,
                           #}
                          #)
        blocks.extend(FoundEntitiesBlock(searcher, model, research, user) for model in models)

    #t_ctx['total'] = total
    #t_ctx['results'] = results
    t_ctx['research'] = research
    t_ctx['models'] = [model._meta.verbose_name for model in models]
    t_ctx['blocks'] = blocks

    return HttpResponse(render_to_string('creme_core/search_results.html', t_ctx,
                                         context_instance=RequestContext(request),
                                        )
                       )
#Not ajax version :
#    return render_to_response("creme_core/generics/search_results.html", t_ctx, context_instance=RequestContext(request))


@login_required
@jsonify
def reload_block(request, block_id, research):
    ctype = FoundEntitiesBlock.parse_block_id(block_id)

    if ctype is None:
        raise Http404('Invalid block ID')

    if len(research) < MIN_RESEARCH_LENGTH:
        raise Http404(u"Please enter at least %s characters" % MIN_RESEARCH_LENGTH)

    user = request.user
    model = ctype.model_class()
    block = FoundEntitiesBlock(Searcher([model], user), model, research, user, id=block_id)

    return [(block.id_, block.detailview_display(RequestContext(request)))]
