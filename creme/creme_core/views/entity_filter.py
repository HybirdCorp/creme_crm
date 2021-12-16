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

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

from .. import utils
from ..auth.decorators import login_required
from ..core.entity_filter import EF_USER, entity_filter_registries
from ..core.exceptions import ConflictError
from ..forms.entity_filter import forms as efilter_forms
from ..gui.listview import ListViewState
from ..http import CremeJsonResponse
from ..models import EntityFilter, RelationType
from ..utils import db as db_utils
from ..utils import get_from_GET_or_404
from ..utils.content_type import entity_ctypes
from ..utils.unicode_collation import collator
from . import generic
from .decorators import jsonify
from .entity import EntityDeletionMixin
from .generic import base

logger = logging.getLogger(__name__)
User = get_user_model()


class FilterMixin:
    """Code factorisation with HeaderFilter views."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lv_url = None

    def build_lv_url(self):
        url = self.lv_url

        if url is None:
            url = self.request.POST.get('cancel_url')

            if not url:
                model = self.object.entity_type.model_class()

                try:
                    url = model.get_lv_absolute_url()
                except AttributeError:
                    logger.debug('"%s" has no get_lv_absolute_url() method ?!', model)
                    url = ''

            self.lv_url = url

        return url

    def check_filter_permissions(self, filter_obj, user):
        allowed, msg = filter_obj.can_edit(user)

        if not allowed:
            raise PermissionDenied(msg)

    @staticmethod
    def get_case_sensitivity_message():
        if not db_utils.is_db_equal_case_sensitive():
            if not db_utils.is_db_like_case_sensitive():
                return _(
                    'Notice: your database is not case sensitive, so the string '
                    'operators which are case sensitive and the ones which are '
                    'not will accept the same entities.'
                )

            return _(
                'Notice: your database is not case sensitive for the "equals" '
                'operator, so the string equality operators which are case '
                'sensitive and the ones which are not will accept the same entities.'
            )
        elif not db_utils.is_db_like_case_sensitive():
            return _(
                'Notice: your database is not case sensitive, so the string operators '
                'which are case sensitive and the ones which are not will accept '
                'the same entities (excepted equality ones, which are case sensitive).'
            )

        return None

    # TODO: rename (shadows view method)
    def get_success_url(self):
        # TODO: callback_url?
        return self.build_lv_url() or reverse('creme_core__home')

    def save_in_session(self, lvs_attr):
        request = self.request
        lv_url = self.build_lv_url()
        lvs = ListViewState.get_state(request, lv_url) or ListViewState(url=lv_url)

        setattr(lvs, lvs_attr, self.object.id)
        lvs.register_in_session(request)


class EntityFilterMixin(FilterMixin):
    efilter_registry = entity_filter_registries[EF_USER]

    def get_efilter_registry(self):
        return self.efilter_registry


class EntityFilterCreation(base.EntityCTypeRelatedMixin,
                           EntityFilterMixin,
                           generic.CremeModelCreation):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterCreateForm
    template_name = 'creme_core/forms/entity-filter.html'
    ctype_form_kwarg = 'ctype'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('entity_filter_id')

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.get_case_sensitivity_message()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()
        kwargs['efilter_registry'] = self.get_efilter_registry()

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE

        return initial


class EntityFilterEdition(EntityFilterMixin, generic.CremeModelEdition):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterEditForm
    template_name = 'creme_core/forms/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    submit_label = _('Save the modified filter')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.get_case_sensitivity_message()

        return context

    def get_object(self, *args, **kwargs):
        efilter = super().get_object(*args, **kwargs)
        self.check_filter_permissions(filter_obj=efilter, user=self.request.user)

        return efilter

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['efilter_registry'] = self.get_efilter_registry()

        return kwargs


class EntityFilterDeletion(EntityDeletionMixin, generic.CremeModelDeletion):
    model = EntityFilter

    def check_instance_permissions(self, instance, user):
        allowed, msg = instance.can_delete(user)
        if not allowed:
            raise PermissionDenied(msg)

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.entity_type.model_class().get_lv_absolute_url()

    def perform_deletion(self, request):
        try:
            super().perform_deletion(request)
        except EntityFilter.DependenciesError as e:
            raise ConflictError(e) from e
        # TODO: move in a middleware ??
        except ProtectedError as e:
            raise ConflictError(
                gettext(
                    'The filter can not be deleted because of its dependencies '
                    '({dependencies}).'
                ).format(
                    dependencies=self.dependencies_to_str(
                        dependencies=e.args[1],
                        user=request.user,
                    ),
                )
            ) from e


# TODO: factorise with views.relations.json_rtype_ctypes  ???
@login_required
@jsonify
def get_content_types(request, rtype_id):
    content_types = get_object_or_404(
        RelationType, pk=rtype_id,
    ).object_ctypes.all() or entity_ctypes()

    return [
        (0, pgettext('creme_core-filter', 'All')),
        *((ct.id, str(ct)) for ct in content_types),
    ]


class EntityFilterChoices(base.ContentTypeRelatedMixin, base.CheckedView):
    response_class = CremeJsonResponse
    ctype_id_arg = 'ct_id'
    include_all_arg = 'all'
    all_label = pgettext_lazy('creme_core-filter', 'All')

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

    def get_ctype_id(self):
        return utils.get_from_GET_or_404(self.request.GET, self.ctype_id_arg, int)

    def get_include_all(self):
        return utils.get_from_GET_or_404(
            self.request.GET,
            key=self.include_all_arg,
            cast=utils.bool_from_str_extended,
            default='0',
        )

    def get_choices(self):
        choices = [('', self.all_label)] if self.get_include_all() else []
        choices.extend(
            EntityFilter.objects
                        .filter_by_user(self.request.user)
                        .filter(entity_type=self.get_ctype())
                        .values_list('id', 'name')
        )

        return choices

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )


# TODO: generalize this view to all enumerable models (inherit enumerable view ?)
#       anyway, we need other examples of operand...
class UserChoicesView(base.CheckedView):
    response_class = CremeJsonResponse
    filter_type_arg = 'filter_type'

    def get_registry(self):
        ftype = get_from_GET_or_404(
            self.request.GET, key=self.filter_type_arg, cast=int,
            default=EF_USER,  # TODO: make mandatory ?
        )

        try:
            return entity_filter_registries[ftype]
        except KeyError as e:
            raise Http404('Invalid filter type') from e

    def get_operands(self):
        user = self.request.user

        for operand in self.get_registry().operands(user):
            if issubclass(operand.model, User):
                yield operand

    def get(self, request, *args, **kwargs):
        sort_key = collator.sort_key

        def choice_key(c):
            return sort_key(c[1])

        # TODO: return group for teams & inactive users (see UserEnumerator)
        #       => fix the JavaScript side (it concatenates the group label at the end)
        return self.response_class(
            [
                *sorted(
                    ((op.type_id, op.verbose_name) for op in self.get_operands()),
                    key=choice_key,
                ),
                *sorted(
                    ((e.id, str(e)) for e in User.objects.all()),
                    key=choice_key,
                ),
            ],
            safe=False,  # Result is not a dictionary
        )
