################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import logging
from functools import partial
from time import time
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..core.search import Searcher
from ..gui.bricks import QuerysetBrick
from ..http import CremeJsonResponse
from ..models import CremeEntity, EntityCredentials
from ..models.utils import model_verbose_name
from ..registry import creme_registry
from ..utils.unicode_collation import collator
from .bricks import BricksReloading
from .generic import base

MIN_SEARCH_LENGTH = 3
logger = logging.getLogger(__name__)


class FoundEntitiesBrick(QuerysetBrick):
    template_name = 'creme_core/bricks/found-entities.html'

    id_prefix = 'found'

    def __init__(self, searcher, model, searched, user, id=None):
        super().__init__()
        # dependencies  = (...,)  # TODO: ??
        self.searcher = searcher
        self.model = model
        self.searched = searched
        self.user = user
        ctype = ContentType.objects.get_for_model(model)
        # We generate a unique ID for each search, in order
        # to avoid sharing state (e.g. page number) between researches.
        self.id = id or f'{self.id_prefix}-{ctype.app_label}-{ctype.model}-{int(time())}'

    @classmethod
    def parse_brick_id(cls, brick_id) -> ContentType | None:
        """Extract info from brick ID.

        @param brick_id: e.g. "found-my_app-my_model-122154".
        @return A ContentType instance if valid, else None.
        """
        parts = brick_id.split('-')

        if len(parts) != 4:
            logger.warning('parse_brick_id(): the brick ID "%s" has a bad length', brick_id)
            return None

        if parts[0] != cls.id_prefix:
            logger.warning('parse_brick_id(): the brick ID "%s" has a bad prefix', brick_id)
            return None

        try:
            ctype = ContentType.objects.get_by_natural_key(parts[1], parts[2])
        except ContentType.DoesNotExist:
            logger.warning(
                'parse_brick_id(): the brick ID "%s" has an invalid ContentType key',
                brick_id,
            )
            return None

        if not issubclass(ctype.model_class(), CremeEntity):
            logger.warning(
                'parse_brick_id(): the brick ID "%s" is not related to CremeEntity',
                brick_id,
            )
            return None

        return ctype

    def detailview_display(self, context):
        model = self.model
        searched = self.searched
        searcher = self.searcher
        results = searcher.search(model, searched)

        if results is None:
            # HACK: ensures that the brick is displayed (with a strange title anyway...)
            qs = model.objects.all()[:1]
        else:
            qs = EntityCredentials.filter(self.user, results)

        return self._render(self.get_template_context(
            context, qs, cells=searcher.get_cells(model),
        ))


class SearcherMixin:
    searcher_class = Searcher
    searchable_models_registry = creme_registry

    def get_raw_models(self):
        role = self.request.user.role
        models = [*creme_registry.iter_entity_models(
            app_labels=role.allowed_apps if role else None
        )]
        sort_key = collator.sort_key
        models.sort(key=lambda m: sort_key(model_verbose_name(m)))

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
        # bricks = super().get_bricks()
        bricks = []

        if not self.get_search_error():
            searcher = self.get_searcher()
            ResultBrick = partial(
                self.brick_class,
                searcher=searcher,
                searched=self.get_search_terms(),
                user=searcher.user,
            )

            bricks.extend(ResultBrick(model=model) for model in searcher.models)

        # return bricks
        return {'main': bricks}

    def get_bricks_reload_url(self):
        return '{}?{}'.format(
            super().get_bricks_reload_url(),
            urlencode({'search': self.get_search_terms()}),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['searched'] = self.get_search_terms()
        context['error_message'] = self.get_search_error()
        context['models'] = models = [*self.get_searcher().models]
        context['verbose_names'] = [*map(model_verbose_name, models)]

        ctype = self.get_ctype()
        context['selected_ct_id'] = ctype.id if ctype else None

        return context

    def get_ctype_id(self):
        return self.request.GET.get('ct_id') or 0

    def get_raw_models(self):
        ctype = self.get_ctype()

        if ctype is None:
            models = super().get_raw_models()
        else:
            models = [ctype.model_class()]

        return models

    def get_search_error(self):
        error = self.search_error

        if error is None:
            self.search_error = error = (
                gettext(
                    'Please enter at least {count} characters'
                ).format(count=MIN_SEARCH_LENGTH)
                if len(self.get_search_terms()) < MIN_SEARCH_LENGTH else
                ''
            )

        return error

    def get_search_terms(self):
        terms = self.search_terms

        if terms is None:
            self.search_terms = terms = self.request.GET.get('search', '')  # TODO: attribute

        return terms


class SearchBricksReloading(BricksReloading):
    def get_bricks(self):
        bricks = []
        request = self.request
        user = request.user
        GET = request.GET

        for brick_id in self.get_brick_ids():
            ctype = FoundEntitiesBrick.parse_brick_id(brick_id)

            if ctype is None:
                raise Http404('Invalid block ID')

            user.has_perm_to_access_or_die(ctype.app_label)

            searched = GET.get('search', '')

            if len(searched) < MIN_SEARCH_LENGTH:
                raise Http404(f'Please enter at least {MIN_SEARCH_LENGTH} characters')

            model = ctype.model_class()
            bricks.append(
                FoundEntitiesBrick(
                    searcher=Searcher([model], user), model=model,
                    searched=searched, user=user, id=brick_id,
                )
            )

        return bricks


class LightSearch(SearcherMixin, base.CheckedView):
    response_class = CremeJsonResponse
    search_terms_arg = 'value'
    error_msg_empty = _('Empty search…')
    error_msg_length = _('Please enter at least {count} characters')
    limit = 5

    def build_entry(self, entity):
        entry = {'label': str(entity), 'url': entity.get_absolute_url()}

        if entity.is_deleted:
            entry['deleted'] = True

        return entry

    def build_model_label(self, model):
        # return str(model._meta.verbose_name)
        return model_verbose_name(model)

    def get(self, request, *args, **kwargs):
        terms = self.get_search_terms()
        limit = self.get_limit()

        data = {
            # 'query': {
            #     'content': sought,
            #     'ctype':   ct_id if ct_id else None,
            #     'limit':   int(limit),
            # },
        }

        if not terms:
            data['error'] = self.error_msg_empty
        elif len(terms) < MIN_SEARCH_LENGTH:
            data['error'] = self.error_msg_length.format(count=MIN_SEARCH_LENGTH)
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
                        # TODO: add the columns 'is_deleted' to the order of the query
                        #       to get not-deleted entities first (& so avoid as much
                        #       as possible to get them in our limited query).
                        score = 0 if e.is_deleted else e.search_score
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
