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

import logging
# import warnings

from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404  # render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from .. import utils
from ..auth.decorators import login_required
# from ..core.exceptions import ConflictError
# from ..forms.entity_filter import EntityFilterCreateForm, EntityFilterEditForm
from ..forms import entity_filter as efilter_forms
from ..gui.listview import ListViewState
from ..models import EntityFilter, RelationType  # CremeEntity
from . import generic
# from .generic import add_entity
# from .utils import build_cancel_path

logger = logging.getLogger(__name__)


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

    def get_success_url(self):
        return self.build_lv_url() or reverse('creme_core__home')


class FilterCreationMixin(FilterMixin):
    ctype_form_kwarg = 'ctype'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()

        return kwargs

    def save_in_session(self, lvs_attr):
        request = self.request
        lv_url = self.build_lv_url()
        lvs = ListViewState.get_state(request, lv_url) or \
              ListViewState(url=lv_url)

        setattr(lvs, lvs_attr, self.object.id)
        lvs.register_in_session(request)


class FilterEditionMixin(FilterMixin):
    def get_object(self, *args, **kwargs):
        filter_ = super().get_object(*args, **kwargs)

        allowed, msg = filter_.can_edit(self.request.user)
        if not allowed:
            raise PermissionDenied(msg)

        return filter_


# def _set_current_efilter(request, path, filter_instance):
#     warnings.warn('creme_core.views.entity_filter._set_current_efilter() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     lvs = ListViewState.get_state(request, path)
#     if lvs:
#         lvs.entity_filter_id = filter_instance.id
#         lvs.register_in_session(request)


# @login_required
# def add(request, ct_id):
#     ct = utils.get_ct_or_404(ct_id)
#
#     if not request.user.has_perm(ct.app_label):
#         raise PermissionDenied(ugettext(u"You are not allowed to access to this app"))
#
#     model = ct.model_class()
#
#     if not issubclass(model, CremeEntity):
#         raise ConflictError(u'This model is not a entity model: {}'.format(model))
#
#     post_save = None
#     callback_url = request.POST.get('cancel_url')
#
#     if not callback_url:
#         try:
#             # callback_url = '{}?filter=%s'.format(model.get_lv_absolute_url())
#             callback_url = model.get_lv_absolute_url()
#         except AttributeError:
#             logger.debug('%s has no get_lv_absolute_url() method ?!', model)
#             # callback_url = '/'
#     # else:
#     #     callback_url = '{}?filter=%s'.format(callback_url)
#
#     if callback_url:
#         # Set current EntityFilter
#         def post_save(request_, instance):
#             lvs = ListViewState.get_state(request_, callback_url) or \
#                   ListViewState(url=callback_url)
#
#             lvs.entity_filter_id = instance.id
#             lvs.register_in_session(request_)
#     else:
#         callback_url = '/'
#
#     return generic.add_entity(request, efilter_forms.EntityFilterCreateForm,
#                       url_redirect=callback_url,
#                       template='creme_core/forms/entity-filter.html',
#                       extra_initial={'content_type': ct},
#                       # function_post_save=lambda req, instance: _set_current_efilter(req, callback_url, instance),
#                       function_post_save=post_save,
#                      )
class EntityFilterCreation(FilterCreationMixin,
                           generic.base.EntityCTypeRelatedMixin,
                           generic.add.CremeModelCreation,
                          ):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterCreateForm
    template_name = 'creme_core/forms/entity-filter.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('entity_filter_id')

        return response


# @login_required
# def edit(request, efilter_id):
#     efilter = get_object_or_404(EntityFilter, pk=efilter_id)
#     user = request.user
#     allowed, msg = efilter.can_edit(user)
#
#     if not allowed:
#         raise PermissionDenied(msg)
#
#     if request.method == 'POST':
#         POST = request.POST
#         cancel_url = POST.get('cancel_url')
#         efilter_form = efilter_forms.EntityFilterEditForm(user=user, data=POST, instance=efilter)
#
#         if efilter_form.is_valid():
#             efilter_form.save()
#
#             return HttpResponseRedirect(cancel_url or
#                                         efilter.entity_type.model_class().get_lv_absolute_url()
#                                        )
#     else:
#         efilter_form = efilter_forms.EntityFilterEditForm(user=user, instance=efilter)
#         cancel_url = build_cancel_path(request)
#
#     return render(request,
#                   'creme_core/forms/entity-filter.html',
#                   {'form': efilter_form,
#                    'cancel_url': cancel_url,
#                    'submit_label': _('Save the modified filter'),
#                   }
#                  )
class EntityFilterEdition(FilterEditionMixin, generic.edit.CremeModelEdition):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterEditForm
    template_name = 'creme_core/forms/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    submit_label = _('Save the modified filter')


@login_required
def delete(request):
    efilter      = get_object_or_404(EntityFilter, pk=utils.get_from_POST_or_404(request.POST, 'id'))
    callback_url = efilter.entity_type.model_class().get_lv_absolute_url()
    allowed, msg = efilter.can_delete(request.user)
    status = 400  # TODO: 409 ??

    if allowed:
        try:
            efilter.delete()
        except EntityFilter.DependenciesError as e:
            return_msg = str(e)
        except ProtectedError as e:
            return_msg = ugettext('«{}» can not be deleted because of its dependencies.').format(efilter)
            return_msg += render_to_string('creme_core/templatetags/widgets/list_instances.html',
                                           {'objects': e.args[1][:25], 'user': request.user},
                                           request=request,
                                          )
        else:
            return_msg = ugettext('Filter successfully deleted')
            status = 200
    else:
        return_msg = msg

    if request.is_ajax():
        # return HttpResponse(return_msg, content_type='text/javascript', status=status)
        return HttpResponse(return_msg, status=status)

    return HttpResponseRedirect(callback_url)


# TODO: factorise with views.relations.json_rtype_ctypes  ???
@login_required
@utils.jsonify
def get_content_types(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all() or \
                    utils.creme_entity_content_types()

    choices = [(0, ugettext('All'))]
    choices.extend((ct.id, str(ct)) for ct in content_types)

    return choices


@login_required
@utils.jsonify
def get_for_ctype(request):
    GET = request.GET
    ct_id = utils.get_from_GET_or_404(GET, 'ct_id', int)
    include_all = utils.get_from_GET_or_404(GET, 'all', cast=utils.bool_from_str_extended, default='0')
    ct = utils.get_ct_or_404(ct_id)
    user = request.user

    # if not user.has_perm(ct.app_label):
    #     raise PermissionDenied(ugettext('You are not allowed to access to this app'))
    user.has_perm_to_access_or_die(ct.app_label)

    choices = [('', ugettext('All'))] if include_all else []
    choices.extend(EntityFilter.get_for_user(user, ct).values_list('id', 'name'))

    return choices
