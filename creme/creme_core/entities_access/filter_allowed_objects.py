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

from logging import debug

#from ctypes import ArgumentError
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from creme_core import constants

#TODO: rename 'type_droit'.....
def filter_allowed_objects(request, queryset, type_droit, app_name=None):
    """
        Filter only allowed entities for an user
        Return a queryset
    """
    debug('###filter_allowed_objects###')
    from permissions import user_has_permission_for_an_object

    if request.user.is_superuser:
        debug("filter_allowed_objects() -> super user: ok")
        return queryset

    debug("filter_allowed_objects() -> NOT super user: processing")

    for obj in queryset:
        if hasattr(obj, 'user') and not user_has_permission_for_an_object(request, obj, type_droit, app_name):
            queryset = queryset.exclude(id=obj.id)

    debug('$$$filter_allowed_objects###')
    debug('objects:%s, type_droit:%s', queryset, type_droit)
    return queryset

#from django.db.models.query import QuerySet
#def filter_allowed_objects(request, objects, type_droit, app_name=None):
#    """
#        Filter only allowed entities for an user
#        Return a queryset
#    """
#    debug('###filter_allowed_objects###')
#    if request.user.is_superuser:
#        return objects
#    debug('$$#$$####objects:%s' % objects.__class__)
#
#    if isinstance(objects, QuerySet):
#        return _filter_allowed_objects_from_queryset(request, objects, type_droit, app_name)
#    elif isinstance(objects, list):
#        return _filter_allowed_objects_from_list(request, objects, type_droit, app_name)
#    else:
#        raise ArgumentError('objects have to be an instance of QuerySet or list not %s' % objects.__class__)
#
#def _filter_allowed_objects_from_list(request, list, type_droit, app_name=None):
#    from permissions import user_has_permission_for_an_object
#    for obj in list:
#        if not hasattr(obj, 'user'):
#            continue
#        if not user_has_permission_for_an_object(request, obj, type_droit, app_name):
#            list = list.remove(obj)
#    return list
#
#def _filter_allowed_objects_from_queryset(request, queryset, type_droit, app_name=None):
#    from permissions import user_has_permission_for_an_object
#    for obj in queryset:
#        if not hasattr(obj, 'user'):
#            continue
#        if not user_has_permission_for_an_object(request, obj, type_droit, app_name):
#            queryset = queryset.exclude(id=obj.id)
#    return queryset

######################## Filter allowed helpers ################################
### Read ###
def filter_can_read_objects(request, queryset, app_name=None):
    if not app_name:
        app_name = queryset.model._meta.app_label
    return filter_allowed_objects(request, queryset, constants.DROIT_TYPE_DROIT_LIRE, app_name)

### Edit ###
def filter_can_edit_objects(request, queryset, app_name=None):
    if not app_name:
        app_name = queryset.model._meta.app_label
    return filter_allowed_objects(request, queryset, constants.DROIT_TYPE_DROIT_MODIFIER, app_name)

### Delete ###
def filter_can_delete_objects(request, queryset, app_name=None):
    if not app_name:
        app_name = queryset.model._meta.app_label
    return filter_allowed_objects(request, queryset, constants.DROIT_TYPE_DROIT_SUPPRIMER, app_name)

### Link ###
def filter_can_link_objects(request, queryset, app_name=None):
    if not app_name:
        app_name = queryset.model._meta.app_label
    return filter_allowed_objects(request, queryset, constants.DROIT_TYPE_DROIT_METTRE_RELATION, app_name)


def filter_Read_objects (request, queryset, app_name=None):
    """
        Get only read/edit/delete allowed objects
    """
    return  filter_can_read_objects(request, queryset, app_name) 



def filter_RUD_objects(request, queryset, app_name=None):
    """
        Get only read/edit/delete allowed objects
    """
    return  filter_can_read_objects(request, queryset, app_name) | \
            filter_can_edit_objects(request, queryset, app_name) | \
            filter_can_delete_objects(request, queryset, app_name)

################################################################################
################################################################################
    

def filter_allowed_only_your_entities(obj, request, entity_type):
    #TODO : Deprecated ?
    if request.user.is_superuser:
        debug('on a un super user')
        return obj

    debug ('on a un  user qui n est pas un super user %s ', request.user)
    Q_total = Q(user=request.user)
    return obj.filter(Q_total)

def filter_allowed_objects_old ( obj , request, module_name  , form_name ):
    #TODO : Deprecated ?
    # a garder pour s'en inspirer peut etre pour la reecriture des requetes de filtrage
    if request.user.is_superuser:
        return obj.objects

    Role = request.user.get_profile().creme_role
    debug("filter_allowed_objects.module_name: %s", module_name )
    debug("filter_allowed_objects.form_name : %s", form_name )

    Nom_App = module_name.split('.')[0]
    debug("filter_allowed_objects.Nom_App: %s", Nom_App )
    content_type = ContentType.objects.get_for_model (obj)
    debug("filter_allowed_objects.ContentType: %s", content_type)
    pas_Acces = (Role.droits_app.none() == Role.droits_app.filter(name_app=Nom_App, type_droit__name=constants.DROIT_MODULE_A_ACCES))

    pas_Admin = (Role.droits_app.none() == Role.droits_app.filter(name_app=Nom_App, type_droit__name=constants.DROIT_MODULE_EST_ADMIN ) )

    if  pas_Acces and pas_Admin:
        return obj.objects.none()

    debug("filter_allowed_objects : il a acces ou est admin, on continue ")
    Q_total = None

#    Droit_ses_Fiches = Role.droits_entity_type.filter (content_type=content_type ,
#                        type_droit__name="Lire" ,
#                        type_ensemble_fiche__name="ses_fiches" )

#                        type_droit__name=constants.DROIT_TYPE_DROIT_LIRE ,
#                        type_ensemble_fiche__name=constants.DROIT_TEF_SES_FICHES )
 
#    if Droit_ses_Fiches :
#        if Q_total :
#            Q_total |= Q ( user=request.user )
#        else:
#            Q_total = Q ( user=request.user )



    Droit_ses_Fiches = Role.droits_entity_type.filter(content_type=content_type,
            type_droit__name=constants.DROIT_TYPE_DROIT_LIRE,
            type_ensemble_fiche__name=constants.DROIT_TEF_SES_FICHES)
    debug("filter_allowed_objects : Droit_ses_Fiches %s", Droit_ses_Fiches)
    if Droit_ses_Fiches:
        if Q_total :
            Q_total |= Q ( user=request.user )
        else:
            Q_total = Q ( user=request.user )

    Droit_ses_Fiches2 = Role.droits_entity_type.filter(content_type=content_type, type_droit__name="Lire", type_ensemble_fiche__name="ses_fiches")
    debug("filter_allowed_objects : Droit_ses_Fiches %s", Droit_ses_Fiches2)
    if Droit_ses_Fiches2:
        if Q_total:
            Q_total |= Q ( user=request.user )
        else:
            Q_total = Q ( user=request.user )

    return obj.objects.filter(Q_total)
