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

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q

from persons.models.contact import Contact
from creme_core import constants
from creme_core.entities_access.functions_for_permissions import is_subordinate_of
from creme_core.models import CremeEntity, CremeProfile, CremeRole
from creme_core.utils.meta import NotDjangoModel


def allow_superuser(view):
    def _allow_superuser(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated() and user.is_superuser:
            debug("Super-user: allowing %s()", view.__name__)
            return True
        else:
            return view(request, *args, **kwargs)
    return _allow_superuser

@allow_superuser
def user_has_acces_to_application(request, app_name, access_type=None):
    """
        Checks if an user has access to an application
        /!\ Doesn't check in subroles because application's access haven't be transitives
    """
    try:
        role = request.user.get_profile().creme_role
    except CremeProfile.DoesNotExist:
        return False

    debug('###access_type:%s', access_type)
    if access_type is None:
        access_filter = Q(type_droit__name=constants.DROIT_MODULE_A_ACCES)|Q(type_droit__name=constants.DROIT_MODULE_EST_ADMIN)
    else:
        access_filter = Q(type_droit__name=access_type)

    #TODO: return role.droits_app.filter(access_filter, name_app=app_name).exists()
    if role.droits_app.filter(access_filter, name_app=app_name):
        return True
    return False


@allow_superuser
def user_has_permission(request, app_name, content_type, type_droit, type_ensemble, id_fiche_role_ou_equipe=None):
    """
        Checks if a user has a permission for the given parameters
        Checks in sub-roles too
        If one or much entity matches  the user has the permission
    """
    #return True
    debug('###user_has_permission###')
    try:
        user_role = request.user.get_profile().creme_role
    except CremeProfile.DoesNotExist:
        debug('user_has_permission renvoie faux')
        return False
    debug('user : %s', request.user)
    debug("app_name:%s, content_type:%s, type_droit:%s, type_ensemble:%s, id_fiche_role_ou_equipe:%s", app_name, content_type, type_droit, type_ensemble, id_fiche_role_ou_equipe)
#    roles = user_role.get_descendants(True)
    roles = CremeRole.objects.filter(pk=user_role.id)

    access_filters = Q(droits_entity_type__content_type=content_type)

    if app_name.lower() != "all_creme_apps":
        access_filters &= Q(droits_app__name_app=app_name)
    access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
    if type_droit!=constants.DROIT_TYPE_DROIT_CREER and type_ensemble is not None:
        access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=type_ensemble)
    if id_fiche_role_ou_equipe:
        access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe=id_fiche_role_ou_equipe)

    debug('access_filters.__dict__:%s', access_filters)
    if roles.filter(access_filters):
        debug('roles.filter(access_filters) : %s', roles.filter(access_filters))
        debug('user_has_permission renvoie vrai')
        return True
    debug('user_has_permission renvoie faux')
    return False

@allow_superuser
def user_has_permission_for_an_object(request, object, type_droit, app_name=None):
    """
        Test if an user has the permission to do something on an object

        TODO : (Re)factor

    """
    debug('###user_has_permission_for_an_object###')
#    debug('Parameters : request=%s, object=%s, type_droit=%s, app_name=%s' % (request.REQUEST, object, type_droit, app_name))
#    debug('Parameters types: request=%s, object=%s, type_droit=%s, app_name=%s' % (type(request), type(object), type(type_droit), type(app_name)))
    if isinstance(object, Model):

#        debug("hasattr(object, 'user'):%s" % hasattr(object, 'user'))

        if not hasattr(object, 'user'):
            return True

        debug('object.user=%s', object.user)

        current_user = request.user
        user_role, obj_role = None, None

        debug('current_user=%s', current_user)

        try:
            user_role = request.user.get_profile().creme_role
        except CremeProfile.DoesNotExist, e:
            debug('%s n est associe a aucun profil exception : %s', request.user, e)
            return False

        if hasattr(object, 'entity_type'):
            content_type = object.entity_type
        else:
            try:
#                content_type = ContentType.objects.get(name=object._meta.object_name)
                content_type = ContentType.objects.get_for_model(object)
            except ContentType.DoesNotExist:
                raise NotDjangoModel('%s.%s is not a django model', object.__class__, object)

        obj_id = object.id
        try:
            obj_role = object.user.get_profile().creme_role
        except CremeProfile.DoesNotExist, e:
            debug('%s n est associe a aucun profil exception : %s', object.user, e)
            return False

        if not app_name:
            app_name = content_type.model_class()._meta.app_label

        #Toutes les fiches / All entities
        # Si l'utilisateur a le droit sur toutes les fiches
#        debug('user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_TOUTES_LES_FICHES) : %s' % user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_TOUTES_LES_FICHES))
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_TOUTES_LES_FICHES):
            debug('DROIT_TEF_TOUTES_LES_FICHES Accordé')
            return True

        # Les autres fiches / Other entities
        # Si l'utilisateur a le droit sur toutes les fiches sauf n particulieres
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_LES_AUTRES_FICHES):
            roles = user_role.get_descendants(True)
            access_filters = Q(droits_app__name_app=app_name)
            access_filters &= Q(droits_entity_type__content_type=content_type)
            access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
            access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=constants.DROIT_TEF_LES_AUTRES_FICHES)
            access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe__isnull=False)
            roles = roles.filter(access_filters).distinct()
            if roles :
                all_rights = []
                right_filter = Q(id_fiche_role_ou_equipe__isnull=False) & Q(type_ensemble_fiche__name=constants.DROIT_TEF_LES_AUTRES_FICHES)
                for r in [role.droits_entity_type.filter(right_filter) for role in roles]:
                    all_rights.extend(r)
                targeted_entities = [right.id_fiche_role_ou_equipe for right in all_rights]
                if obj_id not in targeted_entities:
                    debug('DROIT_TEF_LES_AUTRES_FICHES accordé')
                    return True

        #Ses fiches / Owned entities
        # Si la fiche courante a pour utilisateur l'utilsateur courant
        if object.user == current_user and user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_SES_FICHES):
            debug('DROIT_TEF_SES_FICHES accordé')
            return True

        #Fiches d'un role particulier / entities of a particular role
        # Si le role et les sous-roles de l'utilisateur courant possedent le droit de voir les fiches d'un role particulier
        # et que dans ces droits, il y en ai un qui contient l'id du role concerne
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_FICHES_D_UN_ROLE):
            roles = user_role.get_descendants(True)
            access_filters = Q(droits_app__name_app=app_name)
            access_filters &= Q(droits_entity_type__content_type=content_type)
            access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
            access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_D_UN_ROLE)
            access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe__isnull=False)
            roles = roles.filter(access_filters).distinct()
            if roles :
#                rights = [role.droits_entity_type.filter(Q(id_fiche_role_ou_equipe__isnull=False)&Q(type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_D_UN_ROLE)) for role in roles]
                all_rights = []
#                for r in rights:
                right_filter = Q(id_fiche_role_ou_equipe__isnull=False) & Q(type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_D_UN_ROLE)
                for r in [role.droits_entity_type.filter(right_filter) for role in roles]:
                    all_rights.extend(r)
                all_rights_ids = [right.id_fiche_role_ou_equipe for right in all_rights]
                if obj_role.id in all_rights_ids:
                    debug('DROIT_TEF_FICHES_D_UN_ROLE accordé role:%s' % obj_role)
                    return True
        
        #Fiches des subordonnes / Subordonates' entities
        #Si l'utilisateur qui possede la fiche est un subordonne de l'utilisateur courant et
        #que l'utilisateur courant a le droit de voir les fiches de ses subordonnes
#        debug('is_subordinate_of(object.user, current_user) = %s' % is_subordinate_of(object.user, current_user))
#        debug('object.user : %s' % object.user)
        if is_subordinate_of(object.user, current_user) and user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_FICHES_DE_SES_SUBORDONNES):
            debug('DROIT_TEF_FICHES_DE_SES_SUBORDONNES accordé')
            return True

        #Fiches d'un role particulier + les subordonnes de ce role / Entities of a particular role and it subordonates
        # On recupere tout les roles que possede l'utilisateur courant
        # On les filtre pour ne garder que ceux qui concernent le droit fiche d'un role et subordonnes
        # On recupere les droits concernant le droit fiche d'un role et subordonnes & un role
        # On prend ce role + ses subordonnes + le/les roles d'origine et on regarde si la fiche en cours est contenu dans ceux-ci
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_FICHES_D_UN_ROLE_ET_SUBORDONNES):
            roles = user_role.get_descendants(True)
            access_filters = Q(droits_app__name_app=app_name)
            access_filters &= Q(droits_entity_type__content_type=content_type)
            access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
            access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_D_UN_ROLE_ET_SUBORDONNES)
            access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe__isnull=False)
            roles = roles.filter(access_filters).distinct()
            if roles:
                all_rights = []
                right_filter = Q(id_fiche_role_ou_equipe__isnull=False) & Q(type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_D_UN_ROLE_ET_SUBORDONNES)
                for r in [role.droits_entity_type.filter(right_filter) for role in roles]:
                    all_rights.extend(r)
                all_rights_ids = [right.id_fiche_role_ou_equipe for right in all_rights]

                targeted_roles = [CremeRole.objects.get(pk=right_id).get_descendants(True) for right_id in all_rights_ids]
                all_targeted_roles = []
                for role_list in targeted_roles:
                    all_targeted_roles.extend(role_list)

                if obj_role in all_targeted_roles + list(roles):
                    debug('DROIT_TEF_FICHES_D_UN_ROLE_ET_SUBORDONNES accordé')
                    return True

        #Sa fiche / User entity => A modifier
        if hasattr(object, 'is_user') and object.is_user==current_user \
                and user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_SA_FICHE):
            debug('DROIT_TEF_SA_FICHE accordé')
            return True

        #Fiches en relations avec sa fiche / Entities in relation with his own entity
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_EN_REL_AVC_SA_FICHE):
            try:
                owned_entity = Contact.objects.get(is_user=current_user)
            except Contact.DoesNotExist:
                return False

            if obj_id in [rel.object_id for rel in owned_entity.relations.all()]:
                debug('DROIT_TEF_EN_REL_AVC_SA_FICHE accordé')
                return True
            
        #Fiches equipes / Team entities
        # Vrai si l'utilisateur qui possède la fiche a un groupe en commun
        # avec l'utilisateur courant et si l'utilisateur courant a le droit
        # sur les fiches de l'equipe
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_FICHES_EQUIPE):
            roles = user_role.get_descendants(True)
            access_filters = Q(droits_app__name_app=app_name)
            access_filters &= Q(droits_entity_type__content_type=content_type)
            access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
            access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_EQUIPE)
            access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe__isnull=False)
            roles = roles.filter(access_filters).distinct()
            if roles :
                all_rights = []
                right_filter = Q(id_fiche_role_ou_equipe__isnull=False) & Q(type_ensemble_fiche__name=constants.DROIT_TEF_FICHES_EQUIPE)
                for r in [role.droits_entity_type.filter(right_filter) for role in roles]:
                    all_rights.extend(r)

                targeted_teams = [right.id_fiche_role_ou_equipe for right in all_rights]
                for group in object.user.groups.all():
                    if group.id in targeted_teams:
                        debug('DROIT_TEF_FICHES_EQUIPE accordé')
                        return True

        #Fiche unique / A particular entity
        if user_has_permission(request, app_name, content_type, type_droit, constants.DROIT_TEF_FICHE_UNIQUE):
            roles = user_role.get_descendants(True)
            access_filters = Q(droits_app__name_app=app_name)
            access_filters &= Q(droits_entity_type__content_type=content_type)
            access_filters &= Q(droits_entity_type__type_droit__name=type_droit)
            access_filters &= Q(droits_entity_type__type_ensemble_fiche__name=constants.DROIT_TEF_FICHE_UNIQUE)
            access_filters &= Q(droits_entity_type__id_fiche_role_ou_equipe__isnull=False)
            roles = roles.filter(access_filters).distinct()
            if roles :
                all_rights = []
                right_filter = Q(id_fiche_role_ou_equipe__isnull=False) & Q(type_ensemble_fiche__name=constants.DROIT_TEF_FICHE_UNIQUE)
                for r in [role.droits_entity_type.filter(right_filter) for role in roles]:
                    all_rights.extend(r)
                targeted_entities = [right.id_fiche_role_ou_equipe for right in all_rights]
                if obj_id in targeted_entities:
                    debug('DROIT_TEF_FICHE_UNIQUE accordé')
                    return True

        return False
    else:
        raise NotDjangoModel('%s.%s is not a django model', object.__class__, object)

def get_app_name(object):
    if hasattr(object, 'entity_type'):
        return object.entity_type.model_class()._meta.app_label
    else:
        try:
#            return ContentType.objects.get(name=object._meta.object_name).model_class()._meta.app_label
            return object._meta.app_label
        except ContentType.DoesNotExist:
            raise NotDjangoModel('%s.%s is not a django model', object.__class__, object)

######################## Helpers ###############################################
    #### Read ####
def user_has_read_permission(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    """
        Instanciate app_name always as you can, because it's too restrictive to get _meta.app_label of the content_type
    """
    if not app_name:
        app_name = content_type.model_class()._meta.app_label
    return user_has_permission(request, app_name, content_type, constants.DROIT_TYPE_DROIT_LIRE, type_ensemble, id_fiche_role_ou_equipe)

def user_has_read_permission_for_an_object(request, object, app_name=None):
    if not app_name:
        app_name = get_app_name(object)
    return user_has_permission_for_an_object(request, object, constants.DROIT_TYPE_DROIT_LIRE, app_name)


    #### Create ####
def user_has_create_permission(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    """
        Instanciate app_name always as you can, because it's too restrictive to get _meta.app_label of the content_type
    """
    if not app_name:
        app_name = content_type.model_class()._meta.app_label
    return user_has_permission(request, app_name, content_type, constants.DROIT_TYPE_DROIT_CREER, type_ensemble, id_fiche_role_ou_equipe)

def user_has_create_permission_for_an_object(request, object, app_name=None):
    if not app_name:
        app_name = get_app_name(object)
    return user_has_permission_for_an_object(request, object, constants.DROIT_TYPE_DROIT_CREER, app_name)


    #### Edit ####
def user_has_edit_permission(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    """
        Instanciate app_name always as you can, because it's too restrictive to get _meta.app_label of the content_type
    """
    if not app_name:
        app_name = content_type.model_class()._meta.app_label
    return user_has_permission(request, app_name, content_type, constants.DROIT_TYPE_DROIT_MODIFIER, type_ensemble, id_fiche_role_ou_equipe)

def user_has_edit_permission_for_an_object(request, object, app_name=None):
    if not app_name:
        app_name = get_app_name(object)
    return user_has_permission_for_an_object(request, object, constants.DROIT_TYPE_DROIT_MODIFIER, app_name)

    #### Delete ####
def user_has_delete_permission(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    """
        Instanciate app_name always as you can, because it's too restrictive to get _meta.app_label of the content_type
    """
    if not app_name:
        app_name = content_type.model_class()._meta.app_label
    return user_has_permission(request, app_name, content_type, constants.DROIT_TYPE_DROIT_SUPPRIMER, type_ensemble, id_fiche_role_ou_equipe)

def user_has_delete_permission_for_an_object(request, object, app_name=None):
    if not app_name:
        app_name = get_app_name(object)
    return user_has_permission_for_an_object(request, object, constants.DROIT_TYPE_DROIT_SUPPRIMER, app_name)


    #### Link ####
def user_has_link_permission(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    """
        Instanciate app_name always as you can, because it's too restrictive to get _meta.app_label of the content_type
    """
    if not app_name:
        app_name = content_type.model_class()._meta.app_label
    return user_has_permission(request, app_name, content_type, constants.DROIT_TYPE_DROIT_METTRE_RELATION, type_ensemble, id_fiche_role_ou_equipe)

def user_has_link_permission_for_an_object(request, object, app_name=None):
    if not app_name:
        app_name = get_app_name(object)
    return user_has_permission_for_an_object(request, object, constants.DROIT_TYPE_DROIT_METTRE_RELATION, app_name)

    #### All ####
def user_has_all_permissions(request, content_type, type_ensemble, app_name=None, id_fiche_role_ou_equipe=None):
    return user_has_read_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe) &    \
           user_has_create_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe) &  \
           user_has_edit_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe) &    \
           user_has_delete_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe) &  \
           user_has_link_permission(request, content_type, type_ensemble, app_name, id_fiche_role_ou_equipe)

def user_has_all_permissions_for_an_object(request, object, app_name=None):
    return user_has_read_permission_for_an_object(request, object, app_name) & \
           user_has_create_permission_for_an_object(request, object, app_name) & \
           user_has_edit_permission_for_an_object(request, object, app_name) & \
           user_has_delete_permission_for_an_object(request, object, app_name) & \
           user_has_link_permission_for_an_object(request, object, app_name)
