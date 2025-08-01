################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2025  Hybird
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

from collections import Counter
from collections.abc import Sequence

from django.db.models import ProtectedError
from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.http import is_ajax
from creme.creme_core.models import (
    CremeEntity,
    CremeModel,
    CremeUser,
    Relation,
)
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.translation import smart_model_verbose_name

from .base import CheckedView


class CremeDeletionMixin:
    dependencies_limit = 3

    def dependencies_to_html(self, *,
                             instance: CremeModel,
                             dependencies: Sequence[CremeModel],
                             user: CremeUser,
                             ) -> str:
        def deps_generator():
            not_viewable_count = 0
            can_view = user.has_perm_to_view

            def entity_as_link(entity):
                return format_html(
                    '<a href="{url}" target="_blank"{deleted}>{label}</a>',
                    url=entity.get_absolute_url(),
                    deleted=(
                        mark_safe(' class="is_deleted"')
                        if entity.is_deleted else
                        ''
                    ),
                    label=entity,
                )

            # TODO: sort entities alphabetically?
            # TODO: priority to entity not deleted?
            for dep in dependencies:
                if isinstance(dep, CremeEntity):
                    if can_view(dep):
                        yield entity_as_link(dep)
                    else:
                        not_viewable_count += 1

            if isinstance(instance, CremeEntity):
                not_viewable_relations_counter = Counter()

                # TODO: sort predicates alphabetically?
                for dep in dependencies:
                    if isinstance(dep, Relation):
                        if dep.subject_entity_id == instance.id:
                            obj_entity = dep.object_entity

                            if can_view(obj_entity):
                                yield format_html(
                                    '{predicate} {link}',
                                    predicate=dep.type.predicate,
                                    link=entity_as_link(obj_entity),
                                )
                            else:
                                not_viewable_relations_counter[dep.type.predicate] += 1
                        elif dep.object_entity_id != instance.id:
                            # TODO: other_relations_counter?
                            not_viewable_relations_counter[dep.type.predicate] += 1

                if not_viewable_count:
                    yield ngettext(
                        '{count} not viewable entity',
                        '{count} not viewable entities',
                        not_viewable_count
                    ).format(count=not_viewable_count)

                for predicate, count in not_viewable_relations_counter.items():
                    yield ngettext(
                        '{count} relationship «{predicate}»',
                        '{count} relationships «{predicate}»',
                        count
                    ).format(count=count, predicate=predicate)

                counter = Counter(
                    type(dep)
                    for dep in dependencies
                    if not isinstance(dep, CremeEntity | Relation)
                )
            else:
                if not_viewable_count:
                    yield ngettext(
                        '{count} not viewable entity',
                        '{count} not viewable entities',
                        not_viewable_count
                    ).format(count=not_viewable_count)

                counter = Counter(
                    type(dep) for dep in dependencies if not isinstance(dep, CremeEntity)
                )

            if counter:
                fmt = _('{count} {model}').format

                for model, count in counter.items():
                    yield fmt(
                        count=count,
                        model=smart_model_verbose_name(model=model, count=count),
                    )

        limit = self.dependencies_limit

        # NB: we produce tuples for 'format_html_join()'
        def limited_items():
            for idx, item in enumerate(deps_generator()):
                if idx >= limit:
                    yield ('…',)
                    break

                yield (item,)

        return format_html(
            '<ul>{}</ul>',  # TODO: <class="...">?
            format_html_join('', '<li>{}</li>', limited_items())
        )


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
        user = request.user

        with atomic(), run_workflow_engine(user=user):
            self.object = instance = self.get_object()

            try:
                instance.delete()
            except ProtectedError as e:
                raise ConflictError(
                    format_html(
                        '<span>{message}</span>{dependencies}',
                        message=_(
                            'This deletion cannot be performed because of the '
                            'links with some entities (& other elements):'
                        ),
                        dependencies=self.dependencies_to_html(
                            instance=instance, dependencies=e.args[1], user=user,
                        ),
                    )
                ) from e
