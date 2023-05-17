################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import Field
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import partition
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

from creme.creme_core.enumerators import UserEnumerator

from .. import utils
from ..auth.decorators import login_required
from ..core.entity_filter import EF_USER, entity_filter_registries
from ..core.exceptions import BadRequestError, ConflictError
from ..forms.entity_filter import forms as efilter_forms
from ..gui.listview import ListViewState
from ..http import CremeJsonResponse
from ..models import EntityFilter, RelationType
from ..utils import db as db_utils
from ..utils.content_type import entity_ctypes
from ..utils.unicode_collation import collator
from . import generic
from .decorators import jsonify
from .entity import EntityDeletionMixin
from .enumerable import FieldChoicesView
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
                    'Notice: your database is not case-sensitive, so the string '
                    'operators which are case-sensitive and the ones which are '
                    'not will accept the same entities.'
                )

            return _(
                'Notice: your database is not case-sensitive for the "equals" '
                'operator, so the string equality operators which are '
                'case-sensitive and the ones which are not will accept the same entities.'
            )
        elif not db_utils.is_db_like_case_sensitive():
            return _(
                'Notice: your database is not case-sensitive, so the string operators '
                'which are case-sensitive and the ones which are not will accept '
                'the same entities (excepted equality ones, which are case-sensitive).'
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
    form_class = efilter_forms.EntityFilterCreationForm
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
    form_class = efilter_forms.EntityFilterEditionForm
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


class EntityFilterUserEnumerator(UserEnumerator):
    def __init__(
        self,
        field: Field,
        filter_type=EF_USER,
        search_fields=None,
        limit_choices_to=None
    ):
        self.efilter_registry = self.get_efilter_registry(filter_type)
        super().__init__(field, search_fields, limit_choices_to)

    def get_efilter_registry(self, filter_type):
        try:
            return entity_filter_registries[filter_type]
        except KeyError:
            raise BadRequestError(f'Unknown entity filter type {filter_type}')

    def get_user_operands(self, user):
        for operand in self.efilter_registry.operands(user):
            if issubclass(operand.model, User):
                yield operand

    def to_python(self, user, values):
        operands = {o.type_id for o in self.get_user_operands(user)}

        op_ids, pks = partition(lambda v: v in operands, values)
        return [*op_ids, *self._queryset(user).filter(pk__in=pks)]

    def choices(self, user, *, term=None, only=None, limit=None):
        sort_key = collator.sort_key
        choices = [
            {
                'value': op.type_id,
                'label': op.verbose_name,
            } for op in self.get_user_operands(user)
        ]
        choices.sort(key=lambda d: sort_key(d['label']))

        choices.extend(
            super().choices(user, term=term, only=only)
        )

        return choices[:limit] if limit else choices


# class UserChoicesView(ChoicesView):
class UserChoicesView(FieldChoicesView):
    filter_type_arg = 'filter_type'

    def get_enumerator(self):
        model = self.get_ctype().model_class()
        field_name = self.get_field_name()

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            raise Http404('This field does not exist.') from e

        return EntityFilterUserEnumerator(field, filter_type=self.filter_type)

    def get(self, request, *args, **kwargs):
        try:
            self.filter_type = int(request.GET.get('filter_type', EF_USER))
        except ValueError as e:
            raise BadRequestError(e) from e

        return super().get(request, *args, **kwargs)
