# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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

from itertools import chain
import warnings

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views import View

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.enumerable import enumerable_registry
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CustomFieldEnumValue, CustomField
from creme.creme_core.utils import get_ct_or_404

from .decorators import jsonify


@login_required
@jsonify
def json_list_enumerable(request, ct_id):
    warnings.warn('creme_core.views.enumerable.json_list_enumerable() is deprecated ; '
                  'use ChoicesView instead.',
                  DeprecationWarning
                 )

    from creme.creme_core.enumerators import EntityFilterEnumerator
    from creme.creme_core.models import EntityFilter
    from creme.creme_core.utils import build_ct_choices, creme_entity_content_types
    from creme.creme_core.utils.unicode_collation import collator

    from creme.creme_config.registry import config_registry, NotRegisteredInConfig

    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    if issubclass(model, EntityFilter):
        sort_key = collator.sort_key
        # key = lambda e: sort_key(e['group'] + e['label'])
        #
        # return sorted([{'value': filter.pk,
        #                 'label': filter.name,
        #                 'help':  _(u'Private ({})').format(filter.user)
        #                          if filter.is_private else '',
        #                 'group': str(filter.entity_type),
        #                } for filter in EntityFilter.objects.all()
        #               ],
        #               key=key,
        #              )
        choices = list(map(EntityFilterEnumerator.efilter_as_dict, EntityFilter.objects.all()))
        choices.sort(key=lambda d: sort_key(d['group'] + d['label']))

        return choices

    if model is ContentType:
        # NB: we are sure that entities' ContentTypes are user-friendly.
        #     Currently, only the form for EntityFilters on reports.Report
        #     uses it, & it needs only entities ctypes (EDIT: not true since
        #     choices() is used instead of this deprecated view).
        return build_ct_choices(creme_entity_content_types())

    if not issubclass(model, get_user_model()):
        app_name = ct.app_label

        if not request.user.has_perm(app_name):
            raise Http404("You are not allowed to access to the app '{}'".format(app_name))

        try:
            config_registry.get_app(app_name).get_model_conf(model=model)
        except (KeyError, NotRegisteredInConfig) as e:
            raise Http404('Content type is not registered in config') from e

    return [(e.id, str(e)) for e in model.objects.all()]


# TODO: JSONView ?
@method_decorator(login_required, name='dispatch')
class ChoicesView(View):
    ctype_id_url_kwarg = 'ct_id'
    field_url_kwarg = 'field'
    registry = enumerable_registry

    def get_model(self):
        model = get_ct_or_404(self.kwargs[self.ctype_id_url_kwarg]).model_class()

        self.request.user.has_perm_to_access_or_die(model._meta.app_label)

        return model

    def get_field_name(self):
        return self.kwargs[self.field_url_kwarg]

    def get_enumerator(self):
        try:
            return self.registry.enumerator_by_fieldname(model=self.get_model(),
                                                         field_name=self.get_field_name(),
                                                        )
        except FieldDoesNotExist as e:
            raise Http404('This field does not exist.') from e
        except ValueError as e:
            raise ConflictError(e) from e

    @method_decorator(jsonify)
    def get(self, request, *args, **kwargs):
        return self.get_enumerator().choices(user=request.user)


# TODO: move to entity_filter.py ?
@login_required
@jsonify
def json_list_userfilter(request):
    return list(chain((('__currentuser__', _('Current user')),),
                      ((e.id, str(e)) for e in get_user_model().objects.all()),
                     )
               )


@login_required
@jsonify
def json_list_enumerable_custom(request, cf_id):
    cf = get_object_or_404(CustomField, pk=cf_id)
    return list(CustomFieldEnumValue.objects.filter(custom_field=cf).values_list('id', 'value'))
