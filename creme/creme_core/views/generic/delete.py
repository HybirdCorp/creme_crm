################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2024  Hybird
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

from itertools import islice
from typing import Sequence

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.http import is_ajax
from creme.creme_core.models import (
    CremeEntity,
    CremeModel,
    CremeUser,
    Relation,
)
from creme.creme_core.utils import get_from_POST_or_404

from .base import CheckedView


class CremeDeletionMixin:
    dependencies_limit = 3

    def dependencies_to_str(self, *,
                            dependencies: Sequence[CremeModel],
                            user: CremeUser,
                            ) -> str:
        def deps_generator():
            not_viewable_count = 0
            can_view = user.has_perm_to_view

            def is_printable_relation(dep):
                return isinstance(dep, Relation) and '-object_' not in dep.type_id

            for dep in dependencies:
                if isinstance(dep, CremeEntity):
                    if can_view(dep):
                        yield _('«{object}» ({model})').format(
                            object=dep, model=dep.entity_type,
                        )
                    else:
                        not_viewable_count += 1

            for dep in dependencies:
                if is_printable_relation(dep) and can_view(dep.object_entity):
                    yield f'{dep.type.predicate} «{dep.object_entity}»'

            if not_viewable_count:
                yield ngettext(
                    '{count} not viewable entity',
                    '{count} not viewable entities',
                    not_viewable_count
                ).format(count=not_viewable_count)

            for dep in dependencies:
                if is_printable_relation(dep) and not can_view(dep.object_entity):
                    yield f'{dep.type.predicate} «{settings.HIDDEN_VALUE}»'

            for dep in dependencies:
                if not isinstance(dep, (CremeEntity, Relation)):
                    yield str(dep)

        limit = self.dependencies_limit
        str_deps = [*islice(deps_generator(), limit + 1)]

        do_ellipsis = False
        if len(str_deps) > limit:
            str_deps.pop()
            do_ellipsis = True

        result = ', '.join(str_deps[:limit])

        return escape(result + '…' if do_ellipsis else result)


# class CremeDeletion(CheckedView):
class CremeDeletion(CremeDeletionMixin, CheckedView):
    def get_ajax_success_url(self):
        return ''

    def get_success_url(self):
        return reverse('creme_core__home')

    def post(self, request, *args, **kwargs):
        # TODO: <return self.delete(request, *args, **kwargs)> ?
        self.perform_deletion(self.request)

        return (
            HttpResponse(self.get_ajax_success_url(), content_type='text/plain')
            if is_ajax(request) else
            HttpResponseRedirect(self.get_success_url())
        )

    def perform_deletion(self, request):
        raise NotImplementedError


class CremeModelDeletion(CremeDeletion):
    model = CremeModel
    pk_arg = 'id'

    def check_instance_permissions(self, instance, user):
        pass

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        instance = get_object_or_404(queryset, **self.get_query_kwargs())

        self.check_instance_permissions(instance=instance, user=self.request.user)

        return instance

    def get_query_kwargs(self):
        return {'pk': get_from_POST_or_404(self.request.POST, self.pk_arg)}

    def get_queryset(self):
        return self.model._default_manager.all()

    def perform_deletion(self, request):
        self.object = self.get_object()
        self.object.delete()
