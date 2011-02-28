# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity
from creme_core.views.generic.popup import inner_popup


#TODO: rename 'extra_initial' ??
def add_entity(request, form_class, url_redirect='', template='creme_core/generics/blockform/add.html',
               function_post_save=None, extra_initial=None, extra_template_dict=None):
    """
    @param url_redirect: string or format string with ONE argument replaced by the id of the created entity.
    @param function_post_save: allow processing on the just saved entity. Its signature: function_post_save(request, entity)
    """
    #initial_dict = {'user': request.user.id} #TODO: let the form doing it
    #if extra_initial:
        #initial_dict.update(extra_initial)

    if request.method == 'POST':
        #entity_form = form_class(user=request.user, data=request.POST, files=request.FILES or None, initial=initial_dict)
        entity_form = form_class(user=request.user, data=request.POST, files=request.FILES or None, initial=extra_initial)

        if entity_form.is_valid():
            entity_form.save()

            if function_post_save:
                function_post_save(request, entity_form.instance)

            if not url_redirect:
                url_redirect = entity_form.instance.get_absolute_url()
            elif url_redirect.find("%") > -1: #TODO: still useful ???
                url_redirect = url_redirect % entity_form.instance.id

            return HttpResponseRedirect(url_redirect)
        #else:
            #entity_form = form_class(post, initial=initial_dict) #COMMENTED on 14 february 2011
    else: #GET
        #entity_form = form_class(user=request.user, initial=initial_dict)
        entity_form = form_class(user=request.user, initial=extra_initial)

    template_dict = {'form': entity_form}
    if extra_template_dict:
        template_dict.update(extra_template_dict)

    return render_to_response(template, template_dict,
                              context_instance=RequestContext(request))

def add_to_entity(request, entity_id, form_class, title, entity_class=None, initial=None,
                  template='creme_core/generics/blockform/add_popup2.html', link_perm=False):
    """ Add models related to one CremeEntity (eg: a CremeProperty)
    @param entity_id Id of a CremeEntity.
    @param form_class Form which __init__'s method MUST HAVE an argument caled 'entity' (the related CremeEntity).
    @param title Title of the Inner Popup: Must be a format string with one arg: the related entity.
    @param entity_class If given, it's the entity's class (else it could be any class inheriting CremeEntity)
    @param initial classical 'initial' of Forms
    @param link_perm use LINK permission instead of CHANGE permission (default=False)
    """
    entity = get_object_or_404(entity_class, pk=entity_id) if entity_class else \
             get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    user = request.user

    if link_perm:
        entity.can_link_or_die(user)
    else:
        entity.can_change_or_die(user)

    if request.method == 'POST':
        form = form_class(entity=entity, user=user, data=request.POST, files=request.FILES or None, initial=initial)

        if form.is_valid():
            form.save()
    else:
        form = form_class(entity=entity, user=user, initial=initial)

    return inner_popup(request, template,
                       {
                        'form':   form,
                        'title':  title % entity,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def add_model_with_popup(request, form_class, title=None, initial=None,
                        template='creme_core/generics/blockform/add_popup2.html'):
    """
    @param title Title of the Inner Popup.
    @param initial classical 'initial' of Forms (passed when the request is a GET)
    """
    if request.method == 'POST':
        form = form_class(user=request.user, data=request.POST, files=request.FILES or None, initial=initial)

        if form.is_valid():
            form.save()
    else:
        form = form_class(user=request.user, initial=initial)

    return inner_popup(request, template,
                       {
                        'form':   form,
                        'title':  title or _(u'New'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request)
                      )