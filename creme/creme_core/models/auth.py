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

from collections import defaultdict
from logging import debug

from django.db.models import (Model, CharField, ForeignKey, ManyToManyField,
                              PositiveSmallIntegerField, PositiveIntegerField, TextField, Q)
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from entity import CremeEntity
from creme_core.registry import creme_registry
from creme_core.utils.contribute_to_model import contribute_to_model


NO_CRED = ''
VIEW    = 'v'
CHANGE  = 'c'
DELETE  = 'd'
ALL_CREDS = ''.join((VIEW, CHANGE, DELETE))

CRED_MAP = { #private ? inner ??
        'creme_core.view_entity':   VIEW,
        'creme_core.change_entity': CHANGE,
        'creme_core.delete_entity': DELETE,
        #LINK ??
    }


class EntityCredentials(Model):
    entity = ForeignKey(CremeEntity, null=True, related_name='credentials') #NB: null means: default credentials
    user   = ForeignKey(User, null=True)
    value  = CharField(max_length='3')

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'<EntityCredentials: entity="%s", user="%s", value="%s">' % (self.entity, self.user, self.value)

    def can_change(self):
        return self.has_perm('creme_core.change_entity') #constant ??

    def can_delete(self):
        return self.has_perm('creme_core.delete_entity') #constant ??

    def can_view(self):
        return self.has_perm('creme_core.view_entity') #constant ??

    def has_perm(self, perm):
        return CRED_MAP.get(perm) in self.value

    @staticmethod
    def _build_credentials(view=False, change=False, delete=False):
        cred = ''

        if view:    cred += VIEW
        if change:  cred += CHANGE
        if delete:  cred += DELETE

        return cred

    @staticmethod
    def create(entity, created):
        if created:
            create_creds = EntityCredentials.objects.create
        else:
            existing_creds = dict((creds.user_id, creds) for creds in EntityCredentials.objects.filter(entity=entity.id))

            def create_creds(user, entity, value):
                creds = existing_creds.get(user.id)

                if creds is None:
                    #should never happen, but there can be race condition I suppose....
                    EntityCredentials.objects.create(user=user, entity=entity, value=value)
                elif value != creds.value:
                    creds.value = value
                    creds.save()
                else:
                    debug('EntityCredentials.create(): no change for entity=%s & user=%s', entity, user)

        users = User.objects.select_related('role')
        UserRole.populate_setcreds([user.role for user in users if user.role]) #NB: optimisation time !

        buildc = EntityCredentials._build_credentials

        for user in users:
            role = user.role

            if role:
                create_creds(user=user, entity=entity, value=buildc(*role.get_perms(user, entity)))

    @staticmethod
    def filter(user, queryset): #give wanted perm ???
        if not user.is_superuser:
            query = Q(credentials__user=user, credentials__value__contains=VIEW)

            default = EntityCredentials.get_default_creds() #cache ???
            if default.has_perm('creme_core.view_entity'):
                query |= Q(credentials__isnull=True)

            queryset = queryset.filter(query)

        return queryset

    @staticmethod
    def get_creds(user, entity):
        return EntityCredentials.get_creds_map(user, [entity])[entity.id]

    @staticmethod
    def get_creds_map(user, entities): #TODO: unit test better...
        """Return a dictionnary with items: (CremeEntity.id, EntityCredentials instance).
        Of course it managed default permissions.
        @param user User concerned by the request.
        @param entities A sequence of CremeEntity (beware, it's iterated twice --> not an iterator).
        """
        if user.is_superuser:
            return dict((e.id, EntityCredentials(entity=e, user=user, value=ALL_CREDS)) for e in entities)

        #NB: "e.id" instead of "e"  => avoid one parasit query by entity (ORM bug ??)
        creds_map = dict((creds.entity_id, creds) for creds in EntityCredentials.objects.filter(Q(entity__isnull=True) | Q(entity__in=[e.id for e in entities], user=user)))

        default_creds = creds_map.pop(None, None)
        default_value = default_creds.value if default_creds else NO_CRED

        for entity in entities:
            creds = creds_map.get(entity.id)

            if not creds:
                creds_map[entity.id] = EntityCredentials(entity=entity, user=user, value=default_value)

        return creds_map

    @staticmethod
    def get_default_creds():
        defaults = EntityCredentials.objects.filter(entity__isnull=True)[:1] #get ???

        return defaults[0] if defaults else EntityCredentials(entity=None, value=NO_CRED)

    @staticmethod
    def set_default_perms(view=False, change=False, delete=False):
        default = EntityCredentials.get_default_creds()
        default.value = EntityCredentials._build_credentials(view, change, delete)
        default.save()

    @staticmethod
    def set_entity_perms(user, entity, view=False, change=False, delete=False):
        try:
            perms = EntityCredentials.objects.get(user=user, entity=entity.id)
        except EntityCredentials.DoesNotExist:
            perms = EntityCredentials(user=user, entity=entity)

        perms.value = EntityCredentials._build_credentials(view, change, delete)

        perms.save()


class UserRole(Model):
    name             = CharField(_(u'Name'), max_length=100)
    #superior        = ForeignKey('self', verbose_name=_(u"Superior"), null=True) #related_name='subordinates'
    creatable_ctypes = ManyToManyField(ContentType, null=True, verbose_name=_(u'Creatable resources'))
    raw_allowed_apps = TextField(default='') #use 'allowed_apps' property
    raw_admin_4_apps = TextField(default='') #use 'admin_4_apps' property

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(UserRole, self).__init__(*args, **kwargs)
        self._allowed_apps = None
        self._admin_4_apps = None
        self._creatable_ctypes_set = None
        self._setcredentials = None

    def __unicode__(self):
        return self.name

    def delete(self):
        users = list(User.objects.filter(role=self))

        for user in users:
            user.role = None
            user.save()

        EntityCredentials.objects.filter(user__in=users).delete()

        super(UserRole, self).delete()

    def _get_admin_4_apps(self):
        if self._admin_4_apps is None:
            self._admin_4_apps = set(app_name for app_name in self.raw_admin_4_apps.split('\n') if app_name)

        return self._admin_4_apps

    def _set_admin_4_apps(self, apps):
        """@param apps Sequence of app labels (strings)"""
        self._admin_4_apps = set(apps)
        self.raw_admin_4_apps = '\n'.join(apps)

    admin_4_apps = property(_get_admin_4_apps, _set_admin_4_apps); del _get_admin_4_apps, _set_admin_4_apps

    def _get_allowed_apps(self):
        if self._allowed_apps is None:
            self._allowed_apps = set(app_name for app_name in self.raw_allowed_apps.split('\n') if app_name)

        return self._allowed_apps

    def _set_allowed_apps(self, apps):
        """@param apps Sequence of app labels (strings)"""
        self._allowed_apps = set(apps)
        self.raw_allowed_apps = '\n'.join(apps)

    allowed_apps = property(_get_allowed_apps, _set_allowed_apps); del _get_allowed_apps, _set_allowed_apps

    def is_app_allowed_or_administrable(self, app_name):
        return (app_name in self.allowed_apps) or (app_name in self.admin_4_apps)

    def get_admin_4_apps_verbose(self): #for templates
        get_app = creme_registry.get_app
        return [get_app(app_name).verbose_name for app_name in self.admin_4_apps]

    def get_allowed_apps_verbose(self): #for templates
        get_app = creme_registry.get_app
        return [get_app(app_name).verbose_name for app_name in self.allowed_apps]

    def can_create(self, app_name, model_name):
        """@return True if a model with ContentType(app_name, model_name) can be created."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._creatable_ctypes_set is None:
            self._creatable_ctypes_set = frozenset(self.creatable_ctypes.values_list('id', flat=True))

        return (ct.id in self._creatable_ctypes_set)

    def get_perms(self, user, entity):
        """@return (can_view, can_change, can_delete) 3 boolean tuple"""
        raw_perms = SetCredentials.CRED_NONE
        real_entity_class = ContentType.objects.get_for_id(entity.entity_type_id).model_class()

        if self.is_app_allowed_or_administrable(real_entity_class._meta.app_label):
            setcredentials = self._setcredentials

            if setcredentials is None: #TODO: implement a true getter get_set_credentials() ??
                debug('UserRole.get_perms(): Cache MISS for id=%s', self.id)
                self._setcredentials = setcredentials = list(self.credentials.all())
            else:
                debug('UserRole.get_perms(): Cache HIT for id=%s', self.id)

            for creds in setcredentials:
                raw_perms |= creds.get_raw_perms(user, entity)

        return SetCredentials.get_perms(raw_perms)

    @staticmethod
    def populate_setcreds(roles):
        role_ids = set(role.id for role in roles)
        creds_by_role = defaultdict(list)

        for setcreds in SetCredentials.objects.filter(role__in=role_ids):
            creds_by_role[setcreds.role_id].append(setcreds)

        for role in roles:
            role._setcredentials = creds_by_role[role.id]


class SetCredentials(Model):
    role     = ForeignKey(UserRole, related_name='credentials')
    value    = PositiveSmallIntegerField() #see SetCredentials.CRED_*
    set_type = PositiveIntegerField() #see SetCredentials.ESET_*
    #content_type        = ForeignKey(ContentType, null=True)
    #entity              = ForeignKey(CremeEntity, null=True) #id_fiche_role_ou_equipe = PositiveIntegerField( blank=True, null=True) ??

    CRED_NONE   = 0
    #For python 2.5 compatibility
    #CRED_ADD    = 0b0001 #to be used....
    CRED_ADD    = 1 #to be used....
    #CRED_VIEW   = 0b0010
    CRED_VIEW   = 2
    #CRED_CHANGE = 0b0100
    CRED_CHANGE = 4
    #CRED_DELETE = 0b1000
    CRED_DELETE = 8
    #CRED_LINK ??

    #ESET means 'Entities SET'
    #ESET_ALL = 0b0001 #all entities
    ESET_ALL = 1 #all entities
    #ESET_OWN = 0b0010 #his own entities
    ESET_OWN = 2
    #DROIT_TEF_FICHE_UNIQUE = "fiche_unique"
    #DROIT_TEF_FICHES_EQUIPE = "les_fiches_de_l_equipe"
    #DROIT_TEF_SA_FICHE = "sa_fiche"
    #DROIT_TEF_FICHES_D_UN_ROLE = "fiche_d_un_role"
    #DROIT_TEF_FICHES_D_UN_ROLE_ET_SUBORDONNES = "fiche_d_un_role_et_subordonnees"
    #DROIT_TEF_FICHES_DE_SES_SUBORDONNES = "les_fiches_de_ses_subordonnes"
    #DROIT_TEF_LES_AUTRES_FICHES = "les_autres_fiches"
    #DROIT_TEF_EN_REL_AVC_SA_FICHE = "fiche_en_rel_avec_sa_fiche"

    ESET_MAP = {
            ESET_ALL: _(u'all entities'),
            ESET_OWN: _(u"user's own entities"),
        }

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        value = self.value
        perms = []

        if value & SetCredentials.CRED_VIEW:
            perms.append(ugettext('Can view'))
        if value & SetCredentials.CRED_CHANGE:
            perms.append(ugettext('Can change'))
        if value & SetCredentials.CRED_CHANGE:
            perms.append(ugettext('Can delete'))

        if not perms:
            perms.append(ugettext(u'Nothing allowed'))

        return ugettext(u'For %(set)s => %(perms)s') % {
                    'set':      SetCredentials.ESET_MAP[self.set_type],
                    'perms':    u'|'.join(perms),
                }

    @staticmethod
    def get_perms(raw_perms):
        """Get boolean perms from binary perms.
        @param raw_perms Binary perms returned by SetCredentials.get_raw_perms().
        @return (view, change, delete) 3 boolean tuple
        """
        return (bool(raw_perms & SetCredentials.CRED_VIEW),
                bool(raw_perms & SetCredentials.CRED_CHANGE),
                bool(raw_perms & SetCredentials.CRED_DELETE)
               )

    def get_raw_perms(self, user, entity):
        """@return an integer with binary flags for perms (see get_perms)"""
        if self.set_type == SetCredentials.ESET_ALL:
            return self.value
        else: #SetCredentials.ESET_OWN
            if user.id == entity.user_id:
                return self.value

        return SetCredentials.CRED_NONE

    def set_value(self, can_view, can_change, can_delete):
        """Set the 'value' attribute from 3 booleans"""
        value = SetCredentials.CRED_NONE

        if can_view:
            value |= SetCredentials.CRED_VIEW

        if can_change:
            value |= SetCredentials.CRED_CHANGE

        if can_delete:
            value |= SetCredentials.CRED_DELETE

        self.value = value


class UserProfile(Model):
    role = ForeignKey(UserRole, verbose_name=_(u'Role'), null=True)
    #permissions = None #TODO; can we "erase" 'permissions' fields ?? doesn't seem to work

    class Meta:
        abstract = True

    def has_perm_to_create(self, model_or_entity):
        """Helper for has_perm( method)
        eg: user.has_perm('myapp.add_mymodel') => user.has_perm_to_create(MyModel)"""
        meta = model_or_entity._meta
        return self.has_perm('%s.add_%s' % (meta.app_label, meta.object_name.lower()))

    def update_credentials(self):
        role = self.role

        EntityCredentials.objects.filter(user=self).delete()

        if role is not None: #TODO factorise with EntityCredentials.create() ??
            build_value  = EntityCredentials._build_credentials
            create_creds = EntityCredentials.objects.create
            get_perms    = role.get_perms

            for entity in CremeEntity.objects.all():
                create_creds(user=self, entity=entity, value=build_value(*get_perms(self, entity)))


#NB: We use a contribute_to_model() instead of regular Django's profile
# management to avoid having a additional DB table and creating a annoying
# signal handler to create the corresponding Profile object each time a User is
# created
contribute_to_model(UserProfile, User)
