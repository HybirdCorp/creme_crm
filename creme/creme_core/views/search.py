# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from time import time
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from ..core.entity_cell import EntityCellRegularField
from ..core.search import Searcher
from ..gui.bricks import QuerysetBrick
from ..http import CremeJsonResponse
from ..models import CremeEntity, EntityCredentials
from ..registry import creme_registry
from ..utils.unicode_collation import collator
from .bricks import BricksReloading
from .generic import base

MIN_RESEARCH_LENGTH = 3


class FoundEntitiesBrick(QuerysetBrick):
    template_name = 'creme_core/bricks/found-entities.html'

    def __init__(self, searcher, model, research, user, id=None):
        super().__init__()
        # dependencies  = (...,)  # TODO: ??
        self.searcher = searcher
        self.model = model
        self.research = research
        self.user = user
        self.ctype = ctype = ContentType.objects.get_for_model(model)
        self.id_ = id or self.generate_id(
            'creme_core',
            # We generate an unique ID for each research, in order
            # to avoid sharing state (eg: page number) between researches.
            f'found-{ctype.app_label}-{ctype.model}-{int(time())}',
        )

    @staticmethod
    def parse_brick_id(brick_id):
        "@return A ContentType instance if valid, else None."
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
            # HACK: ensures that the brick is displayed (with a strange title anyway...)
            qs = model.objects.all()[:1]
        else:
            qs = EntityCredentials.filter(self.user, results)

        return self._render(self.get_template_context(
            context, qs,
            # cells=[
            #     EntityCellRegularField.build(model, field.name)
            #     for field in searcher.get_fields(model)
            # ],
            cells=searcher.get_cells(model),
            # If the model is inserted in the context, the template calls it
            # and creates an instance...
            ctype=self.ctype,
        ))


class SearcherMixin:
    searcher_class = Searcher
    searchable_models_registry = creme_registry

    def get_raw_models(self):
        models = [*self.searchable_models_registry.iter_entity_models()]
        models.sort(key=lambda m: m._meta.verbose_name)

        return models

    def get_searcher(self):
        searcher = getattr(self, 'searcher', None)

        if searcher is None:
            self.searcher = searcher = self.searcher_class(
                models=self.get_raw_models(), user=self.request.user,
            )

        return searcher


class Search(SearcherMixin, base.EntityCTypeRelatedMixin, base.BricksView):
    template_name = 'creme_core/search_results.html'
    ct_id_0_accepted = True
    bricks_reload_url_name = 'creme_core__reload_search_brick'
    brick_class = FoundEntitiesBrick
    searcher_class = Searcher

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_error = None
        self.search_terms = None

    def get_bricks(self):
        bricks = super().get_bricks()

        if not self.get_search_error():
            searcher = self.get_searcher()
            ResultBrick = partial(
                self.brick_class,
                searcher=searcher,
                research=self.get_search_terms(),
                user=searcher.user,
            )

            bricks.extend(ResultBrick(model=model) for model in searcher.models)

        return bricks

    def get_bricks_reload_url(self):
        return '{}?{}'.format(
            super().get_bricks_reload_url(),
            urlencode({'search': self.get_search_terms()}),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['research'] = self.get_search_terms()
        context['error_message'] = self.get_search_error()
        context['models'] = [m._meta.verbose_name for m in self.get_searcher().models]

        ctype = self.get_ctype()
        context['selected_ct_id'] = ctype.id if ctype else None

        return context

    def get_ctype_id(self):
        return self.request.GET.get('ct_id') or 0

    def get_raw_models(self):
        ctype = self.get_ctype()

        if ctype is None:
            models = [*creme_registry.iter_entity_models()]
            models.sort(key=lambda m: m._meta.verbose_name)
        else:
            models = [ctype.model_class()]

        return models

    def get_search_error(self):
        error = self.search_error

        if error is None:
            self.search_error = error = (
                gettext(
                    'Please enter at least {count} characters'
                ).format(count=MIN_RESEARCH_LENGTH)
                if len(self.get_search_terms()) < MIN_RESEARCH_LENGTH else
                ''
            )

        return error

    def get_search_terms(self):
        terms = self.search_terms

        if terms is None:
            self.search_terms = terms = self.request.GET.get('research', '')

        return terms


class SearchBricksReloading(BricksReloading):
    check_bricks_permission = False

    def get_bricks(self):
        bricks = []
        request = self.request
        user = request.user
        GET = request.GET

        for brick_id in self.get_brick_ids():
            ctype = FoundEntitiesBrick.parse_brick_id(brick_id)

            if ctype is None:
                raise Http404('Invalid block ID')

            search = GET.get('search', '')

            if len(search) < MIN_RESEARCH_LENGTH:
                raise Http404(f'Please enter at least {MIN_RESEARCH_LENGTH} characters')

            model = ctype.model_class()
            bricks.append(
                FoundEntitiesBrick(Searcher([model], user), model, search, user, id=brick_id)
            )

        return bricks


class LightSearch(SearcherMixin, base.CheckedView):
    response_class = CremeJsonResponse
    search_terms_arg = 'value'
    error_msg_empty = _('Empty search…')
    error_msg_length = _('Please enter at least {count} characters')
    limit = 5

    def build_entry(self, entity):
        return {'label': str(entity), 'url': entity.get_absolute_url()}

    def build_model_label(self, model):
        return str(model._meta.verbose_name)

    def get(self, request, *args, **kwargs):
        terms = self.get_search_terms()
        limit = self.get_limit()

        data = {
            # 'query': {'content': sought,
            #               'ctype':   ct_id if ct_id else None,
            #               'limit':   int(limit),
            #              }
        }

        if not terms:
            data['error'] = self.error_msg_empty
        elif len(terms) < MIN_RESEARCH_LENGTH:
            data['error'] = self.error_msg_length.format(count=MIN_RESEARCH_LENGTH)
        else:
            results = []
            user = request.user
            searcher = self.get_searcher()

            best_score = -1
            best_entry = None

            get_ct = ContentType.objects.get_for_model

            for model in searcher.models:
                query = searcher.search(model, terms)

                if query is None:
                    count = 0
                    query = []
                else:
                    query = EntityCredentials.filter(user, query)
                    count = query.count()

                    if limit > 0:
                        query = query[:limit]

                if query:
                    entities = []

                    for e in query:
                        score = e.search_score
                        entry = self.build_entry(e)

                        if score > best_score:
                            best_score = score
                            best_entry = entry

                        entities.append(entry)

                    results.append({
                        'id': get_ct(model).id,
                        'label': self.build_model_label(model),
                        'count': count,
                        'results': entities,
                    })

            sort_key = collator.sort_key
            data['results'] = sorted(results, key=lambda r: sort_key(r['label']))
            data['best'] = best_entry

        return self.response_class(data)

    def get_limit(self):
        return self.limit

    def get_search_terms(self):
        return self.request.GET.get(self.search_terms_arg, '')
