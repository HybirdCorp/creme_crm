# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _

from creme.creme_core.models import CremeEntity
from .popup import inner_popup


def edit_entity(request, object_id, model, edit_form, template='creme_core/generics/blockform/edit.html'):
    entity = get_object_or_404(model, pk=object_id)
    user = request.user

    user.has_perm_to_change_or_die(entity)

    if request.method == 'POST':
        form = edit_form(user=user, data=request.POST, files=request.FILES or None, instance=entity)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(entity.get_absolute_url())
    else:
        form = edit_form(user=user, instance=entity)

    return render(request, template, {'form': form, 'object': entity})

def edit_related_to_entity(request, pk, model, form_class, title_format):
    """Edit a model related to a CremeEntity.
    @param model A django model class that implements the method get_related_entity().
    @param form_class Form which __init__'s method MUST HAVE an argument caled 'entity' (the related CremeEntity).
    @param model title_format A format unicode with an arg (for the related entity).
    """
    auxiliary = get_object_or_404(model, pk=pk)
    entity = auxiliary.get_related_entity()
    user = request.user

    user.has_perm_to_change_or_die(entity)

    if request.method == 'POST':
        edit_form = form_class(entity=entity, user=user, data=request.POST, instance=auxiliary)

        if edit_form.is_valid():
            edit_form.save()
    else: #return page on GET request
        edit_form = form_class(entity=entity, user=user, instance=auxiliary)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  edit_form,
                        'title': title_format % entity,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

def edit_model_with_popup(request, query_dict, model, form_class,
                          title_format=None, can_change=None,
                          template='creme_core/generics/blockform/edit_popup.html'):
    """
    @param query_dict A dictionary that represents the query to retrieve the edited instance (eg: {'pk': 12})
    @param model A django model class that implements the method get_related_entity().
    @param model title_format A format unicode with an arg (for the edited instance).
    @param can_change A function with instance and user as paramaters, which return a Boolean: False causes a 403 error.
    """
    instance = get_object_or_404(model, **query_dict)
    user = request.user

    if can_change:
        if not can_change(instance, user):
            raise PermissionDenied(_(u'You can not edit this model'))
    elif isinstance(instance, CremeEntity):
        user.has_perm_to_change_or_die(instance)

    if request.method == 'POST':
        edit_form = form_class(user=user, data=request.POST, files=request.FILES or None, instance=instance)

        if edit_form.is_valid():
            edit_form.save()
    else: #return page on GET request
        edit_form = form_class(user=user, instance=instance)

    title_format = title_format or _(u'Edit <%s>')

    return inner_popup(request, template,
                       {'form':  edit_form,
                        'title': title_format % instance,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
