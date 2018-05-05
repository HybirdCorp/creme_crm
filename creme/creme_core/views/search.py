# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from time import time
from urllib import urlencode
# import warnings

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _

from .. import utils
from ..auth.decorators import login_required
from ..core.search import Searcher
from ..core.entity_cell import EntityCellRegularField
from ..gui.bricks import QuerysetBrick
from ..models import CremeEntity, EntityCredentials
from ..registry import creme_registry
from ..utils.unicode_collation import collator

from .bricks import bricks_render_info


MIN_RESEARCH_LENGTH = 3


class FoundEntitiesBrick(QuerysetBrick):
    template_name = 'creme_core/bricks/found-entities.html'

    def __init__(self, searcher, model, research, user, id=None):
        super(FoundEntitiesBrick, self).__init__()
        # dependencies  = (...,)  # TODO: ??
        self.searcher = searcher
        self.model = model
        self.research = research
        self.user = user
        self.ctype = ctype = ContentType.objects.get_for_model(model)
        self.id_ = id or self.generate_id('creme_core',
                                          'found-{}-{}-{}'.format(
                                                ctype.app_label,
                                                ctype.model,
                                                # We generate an unique ID for each research, in order
                                                # to avoid sharing state (eg: page number) between researches.
                                                int(time()),
                                            )
                                         )

    @staticmethod
    # def parse_block_id(block_id):
    def parse_brick_id(brick_id):
        "@return A ContentType instance if valid, else None"
        parts = brick_id.split('-')
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
        research = self.research
        searcher = self.searcher
        results = searcher.search(model, research)

        if results is None:
            # HACK: ensures that the block is displayed (with a strange title anyway...)
            qs = model.objects.all()[:1]
        else:
            qs = EntityCredentials.filter(self.user, results)

        return self._render(self.get_template_context(
                    context, qs,
                    cells=[EntityCellRegularField.build(model, field.name) for field in searcher.get_fields(model)],
                    # If the model is inserted in the context, the template call it and create an instance...
                    ctype=self.ctype,
        ))


@login_required
def search(request):
    GET_get = request.GET.get
    research = GET_get('research', '')
    ct_id    = GET_get('ct_id', '')

    t_ctx  = {'bricks_reload_url': reverse('creme_core__reload_search_brick') + '?' + urlencode({'search': research})}
    models = []
    bricks = []

    if not research:
        if settings.OLD_MENU:
            t_ctx['error_message'] = _(u'Empty search…')
    elif len(research) < MIN_RESEARCH_LENGTH:
        t_ctx['error_message'] = _(u'Please enter at least %s characters') % MIN_RESEARCH_LENGTH
    else:
        if not ct_id:
            models.extend(creme_registry.iter_entity_models())
            models.sort(key=lambda m: m._meta.verbose_name)
        else:
            model = utils.get_ct_or_404(ct_id).model_class()

            if not issubclass(model, CremeEntity):
                raise Http404('The model must be a CremeEntity')

            models.append(model)

        user = request.user
        searcher = Searcher(models, user)

        models = list(searcher.models)  # Remove disabled models
        bricks.extend(FoundEntitiesBrick(searcher, model, research, user) for model in models)

    t_ctx['research'] = research
    t_ctx['models'] = [m._meta.verbose_name for m in models]
    # t_ctx['blocks'] = bricks
    t_ctx['bricks'] = bricks
    t_ctx['selected_ct_id'] = int(ct_id) if ct_id.isdigit() else None

    return render(request, 'creme_core/search_results.html', t_ctx)


# @login_required
# @utils.jsonify
# def reload_block(request, block_id, research):
#     warnings.warn("/creme_core/search/reload_block/{{block_id}}/{{search}} is now deprecated. "
#                   "Use /creme_core/search/reload_brick/ view instead "
#                   "[ie: reverse('creme_core__reload_search_brick') + '?block_id=' + block_id + '&search=' + research ].",
#                   DeprecationWarning
#                  )
#
#     from . import blocks
#
#     ctype = FoundEntitiesBrick.parse_block_id(block_id)
#
#     if ctype is None:
#         raise Http404('Invalid block ID')
#
#     if len(research) < MIN_RESEARCH_LENGTH:
#         raise Http404(u"Please enter at least %s characters" % MIN_RESEARCH_LENGTH)
#
#     user = request.user
#     model = ctype.model_class()
#     block = FoundEntitiesBrick(Searcher([model], user), model, research, user, id=block_id)
#
#     return [(block.id_, block.detailview_display(blocks.build_context(request)))]


@login_required
@utils.jsonify
def reload_brick(request):
    GET = request.GET
    brick_id = utils.get_from_GET_or_404(GET, 'brick_id')
    # ctype = FoundEntitiesBrick.parse_block_id(brick_id)
    ctype = FoundEntitiesBrick.parse_brick_id(brick_id)

    if ctype is None:
        raise Http404('Invalid block ID')

    search = GET.get('search', '')

    if len(search) < MIN_RESEARCH_LENGTH:
        raise Http404(u'Please enter at least %s characters' % MIN_RESEARCH_LENGTH)

    user = request.user
    model = ctype.model_class()
    brick = FoundEntitiesBrick(Searcher([model], user), model, search, user, id=brick_id)

    return bricks_render_info(request, bricks=[brick])


@login_required
@utils.jsonify
def light_search(request):
    GET_get = request.GET.get
    sought = GET_get('value', '')
    # ct_id = GET_get('ct_id')  # TODO: ??
    # limit = int(GET_get('limit', 5))  # TODO: ?? (+ error if not int + min/max)
    limit = 5

    data = {
            # 'query': {'content': sought,
            #               'ctype':   ct_id if ct_id else None,
            #               'limit':   int(limit),
            #              }
           }

    if not sought:
        data['error'] = _(u'Empty search…')
    elif len(sought) < MIN_RESEARCH_LENGTH:
        data['error'] = _(u'Please enter at least %s characters') % MIN_RESEARCH_LENGTH
    else:
        models = []
        results = []

        # if not ct_id:
        models.extend(creme_registry.iter_entity_models())
        models.sort(key=lambda m: m._meta.verbose_name)
        # else:
        #     model = get_ct_or_404(ct_id).model_class()
        #
        #     if not issubclass(model, CremeEntity):
        #         data['error'] = _(u'The model must be a CremeEntity')
        #     else:
        #         models.append(model)

        user = request.user
        searcher = Searcher(models, user)

        models = list(searcher.models)  # Remove disabled models

        best_score = -1
        best_entry = None

        for model in models:
            query = searcher.search(model, sought)

            if query is None:
                count = 0
                query = []
            else:
                query = EntityCredentials.filter(user, query)
                count = query.count()

                if limit > 0:
                    query = query[:limit]

            ctype = ContentType.objects.get_for_model(model)

            if query:
                entities = []

                for e in query:
                    score = e.search_score
                    entry = {'label': unicode(e), 'url': e.get_absolute_url()}  # 'score': score

                    if score > best_score:
                        best_score = score
                        best_entry = entry

                    entities.append(entry)

                results.append({'id':      ctype.id,
                                'label':   unicode(model._meta.verbose_name),
                                'count':   count,
                                'results': entities,
                               })

        sort_key = collator.sort_key
        data['results'] = sorted(results, key=lambda r: sort_key(r['label']))
        data['best'] = best_entry

    return data
