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

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models.authent import CremeTypeEnsembleFiche
from creme_core.models.authent_role import CremeProfile

from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
#from creme_core import creme_constantes

#TODO: should return 403 error when something wrong instead of a simple page with an error message
def get_view_or_die(app_name, access_type=None):
    def _wrap_get_view_or_die(view):
        def _get_view_or_die(request,  *args, **kwargs):
            assert request.user.is_authenticated(),'User is not logged in'
            from permissions import user_has_acces_to_application

            if user_has_acces_to_application(request, app_name, access_type):
                return view(request, *args, **kwargs)
            else:
                return render_to_response('creme_core/forbidden.html', {} ,
                                          context_instance=RequestContext(request ) )
        return _get_view_or_die
    return _wrap_get_view_or_die

def is_subordinate_of(pot_sub, pot_sup):
    """
        pot_sub : User, potentially subordonnate
        pot_sup : User, potentially superior of pot_sub
        pot_sub is considered as a subordonnate if his role is inferior than pot_sup's role
    """
#    return pot_sup.get_profile().creme_role in pot_sub.get_profile().creme_role.get_ascendants()
    try:
        return pot_sup.get_profile().creme_role > pot_sub.get_profile().creme_role
    except CremeProfile.DoesNotExist:
        return False

import logging

def add_view_or_die(content_type, type_ensemble=None, app_name=None, id_fiche_role_ou_equipe=None):
    from permissions import user_has_create_permission
    def _wrap_add_view_or_die(view):
        def _add_view_or_die(request,  *args, **kwargs):
            assert request.user.is_authenticated(),'User is not logged in'
            if user_has_create_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe):
                return view(request, *args, **kwargs)
            else:
                return render_to_response('creme_core/forbidden.html', {} ,
                                          context_instance=RequestContext(request ) )
        return _add_view_or_die
    return _wrap_add_view_or_die

def edit_view_or_die(content_type, type_ensemble=None, app_name=None, id_fiche_role_ou_equipe=None):
    from permissions import user_has_edit_permission
    def _wrap_edit_view_or_die(view):
        def _edit_view_or_die(request,  *args, **kwargs):
            assert request.user.is_authenticated(),'User is not logged in'
            if user_has_edit_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe):
                return view(request, *args, **kwargs)
            else:
                return render_to_response('creme_core/forbidden.html', {} ,
                                          context_instance=RequestContext(request ) )
        return _edit_view_or_die
    return _wrap_edit_view_or_die


###
def _object_or_die(test_func,request, object, app_name=None):
    assert request.user.is_authenticated(),'User is not logged in'
    if not test_func(request, object, app_name):
        if request.is_ajax():
            return HttpResponse(_(u"You do not have access to this page, please contact your administrator."))#Template ?

        return render_to_response('creme_core/forbidden.html', {} , context_instance=RequestContext(request))

def read_object_or_die(request, object, app_name=None):
    from creme_core.entities_access.permissions import user_has_read_permission_for_an_object
    return _object_or_die(user_has_read_permission_for_an_object,request, object, app_name=None)
    
def edit_object_or_die(request, object, app_name=None):
    from creme_core.entities_access.permissions import user_has_edit_permission_for_an_object
    return _object_or_die(user_has_edit_permission_for_an_object,request, object, app_name=None)

def delete_object_or_die(request, object, app_name=None):
    from creme_core.entities_access.permissions import user_has_delete_permission_for_an_object
    return _object_or_die(user_has_delete_permission_for_an_object,request, object, app_name=None)

def link_object_or_die(request, object, app_name=None):
    from creme_core.entities_access.permissions import user_has_link_permission_for_an_object
    return _object_or_die(user_has_link_permission_for_an_object,request, object, app_name=None)
###




#def which_type_ensemble_fiche(object, user):
#    matched_types = []
#    manager = CremeTypeEnsembleFiche.objects
#    if object.user == user:
#        if hasattr(object, 'is_user') and object.is_user==user:
#            matched_types.append(manager.get(name=creme_constantes.DROIT_TEF_SA_FICHE))
##            return CremeTypeEnsembleFiche.objects.get(name=creme_constantes.DROIT_TEF_SA_FICHE)
#        matched_types.append(manager.get(name=creme_constantes.DROIT_TEF_SES_FICHES))
##        return CremeTypeEnsembleFiche.objects.get(name=creme_constantes.DROIT_TEF_SES_FICHES)
#    elif is_subordinate_of(object.user, user):
#        matched_types.append(manager.get(name=creme_constantes.DROIT_TEF_FICHES_SUB))
##        return CremeTypeEnsembleFiche.objects.get(name=creme_constantes.DROIT_TEF_FICHES_SUB)
