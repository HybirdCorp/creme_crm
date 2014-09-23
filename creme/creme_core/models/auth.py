# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

#from collections import defaultdict
import logging
from operator import or_ as or_op

from django.core.exceptions import PermissionDenied
from django.db.models import (Model, CharField, TextField, BooleanField,
                              PositiveSmallIntegerField, PositiveIntegerField,
                              ForeignKey, ManyToManyField, PROTECT)
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ..auth.entity_credentials import EntityCredentials
from ..registry import creme_registry, NotRegistered
from ..utils.contribute_to_model import contribute_to_model
from ..utils.unicode_collation import collator
from .fields import CTypeForeignKey
from .entity import CremeEntity


logger = logging.getLogger(__name__)


class UserRole(Model):
    name              = CharField(_(u'Name'), max_length=100)
    #superior         = ForeignKey('self', verbose_name=_(u"Superior"), null=True) #related_name='subordinates'
    creatable_ctypes  = ManyToManyField(ContentType, null=True, verbose_name=_(u'Creatable resources'), related_name='roles_allowing_creation')
    exportable_ctypes = ManyToManyField(ContentType, null=True, verbose_name=_(u'Exportable resources'), related_name='roles_allowing_export')
    raw_allowed_apps  = TextField(default='') #use 'allowed_apps' property
    raw_admin_4_apps  = TextField(default='') #use 'admin_4_apps' property

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(UserRole, self).__init__(*args, **kwargs)
        self._allowed_apps = None
        self._admin_4_apps = None
        self._creatable_ctypes_set = None
        self._exportable_ctypes_set = None
        self._setcredentials = None

    def __unicode__(self):
        return self.name

    @property
    def admin_4_apps(self):
        if self._admin_4_apps is None:
            self._admin_4_apps = {app_name for app_name in self.raw_admin_4_apps.split('\n') if app_name}

        return self._admin_4_apps

    @admin_4_apps.setter
    def admin_4_apps(self, apps):
        """@param apps Sequence of app labels (strings)"""
        self._admin_4_apps = set(apps)
        self.raw_admin_4_apps = '\n'.join(apps)

    @property
    def allowed_apps(self):
        if self._allowed_apps is None:
            self._allowed_apps = {app_name for app_name in self.raw_allowed_apps.split('\n') if app_name}

        return self._allowed_apps

    @allowed_apps.setter
    def allowed_apps(self, apps):
        """@param apps Sequence of app labels (strings)"""
        self._allowed_apps = set(apps)
        self.raw_allowed_apps = '\n'.join(apps)

    def is_app_allowed_or_administrable(self, app_name):
        return (app_name in self.allowed_apps) or (app_name in self.admin_4_apps)

    def _build_apps_verbose(self, app_names):
        get_app = creme_registry.get_app
        apps = [get_app(app_name).verbose_name for app_name in app_names]
        apps.sort(key=collator.sort_key)

        return apps

    def get_admin_4_apps_verbose(self): #for templates
        return self._build_apps_verbose(self.admin_4_apps)

    def get_allowed_apps_verbose(self): #for templates
        return self._build_apps_verbose(self.allowed_apps)

    def can_create(self, app_name, model_name):
        """@return True if a model with ContentType(app_name, model_name) can be created."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._creatable_ctypes_set is None:
            self._creatable_ctypes_set = frozenset(self.creatable_ctypes.values_list('id', flat=True))

        return (ct.id in self._creatable_ctypes_set)

    def can_export(self, app_name, model_name): #TODO: factorise with can_create() ??
        """@return True if a model with ContentType(app_name, model_name) can be exported."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._exportable_ctypes_set is None:
            self._exportable_ctypes_set = frozenset(self.exportable_ctypes.values_list('id', flat=True))

        return (ct.id in self._exportable_ctypes_set)

    def can_do_on_model(self, user, model, owner, perm):
        """Can the given user execute an action (VIEW, CHANGE etc..) on this model.
        @param user User instance ; user that try to do something.
        @param model Class inheriting CremeEntity
        @param owner User instance ; owner of the not-yet-existing instance of 'model'
                     None means any user that would allows the action (if it exists of course)
        @param perm See EntityCredentials.{VIEW, CHANGE, ...}
        """
        return SetCredentials._can_do(self._get_setcredentials(), user, model, owner, perm)

    def _get_setcredentials(self):
        setcredentials = self._setcredentials

        if setcredentials is None:
            logger.debug('UserRole.get_credentials(): Cache MISS for id=%s', self.id)
            self._setcredentials = setcredentials = list(self.credentials.all())
        else:
            logger.debug('UserRole.get_credentials(): Cache HIT for id=%s', self.id)

        return setcredentials

    def get_perms(self, user, entity):
        """@return (can_view, can_change, can_delete, can_link, can_unlink) 5 boolean tuple"""
        #todo: move this optimization in CremeEntity
        #real_entity_class = ContentType.objects.get_for_id(entity.entity_type_id).model_class()
        real_entity_class = entity.entity_type.model_class()

        if self.is_app_allowed_or_administrable(real_entity_class._meta.app_label):
            perms = SetCredentials.get_perms(self._get_setcredentials(), user, entity)
        else:
            perms = EntityCredentials.NONE

        return perms

    #TODO: factorise
    def filter(self, user, queryset, perm):
        """@param perm value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...)
        @return A new (filtered) queryset"""
        if self.is_app_allowed_or_administrable(queryset.model._meta.app_label):
            queryset = SetCredentials.filter(self._get_setcredentials(), user, queryset, perm)
        else:
            queryset = queryset.none()

        return queryset

    #@staticmethod
    #def populate_setcreds(roles):
        #role_ids = set(role.id for role in roles)
        #creds_by_role = defaultdict(list)

        #for setcreds in SetCredentials.objects.filter(role__in=role_ids):
            #creds_by_role[setcreds.role_id].append(setcreds)

        #for role in roles:
            #role._setcredentials = creds_by_role[role.id]


class SetCredentials(Model):
    role     = ForeignKey(UserRole, related_name='credentials')
    value    = PositiveSmallIntegerField() #see EntityCredentials.VIEW|CHANGE|DELETE|LINK|UNLINK
    set_type = PositiveIntegerField() #see SetCredentials.ESET_*
    #ctype    = ForeignKey(ContentType, null=True, blank=True)
    ctype    = CTypeForeignKey(null=True, blank=True)
    #entity  = ForeignKey(CremeEntity, null=True) ??

    #ESET means 'Entities SET'
    ESET_ALL = 1 # => all entities
    ESET_OWN = 2 # => his own entities

    ESETS_MAP = {ESET_ALL: _(u'all entities'),
                 ESET_OWN: _(u"user's own entities"),
                }

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        value = self.value
        perms = []
        append = perms.append

        if value & EntityCredentials.VIEW:   append(ugettext('View'))
        if value & EntityCredentials.CHANGE: append(ugettext('Change'))
        if value & EntityCredentials.DELETE: append(ugettext('Delete'))
        if value & EntityCredentials.LINK:   append(ugettext('Link'))
        if value & EntityCredentials.UNLINK: append(ugettext('Unlink'))

        if not perms:
            append(ugettext(u'Nothing allowed'))

        args = {'set':   SetCredentials.ESETS_MAP[self.set_type],
                'perms': u', '.join(perms),
               }

        if self.ctype:
            args['type'] = self.ctype
            format_str = ugettext(u'For %(set)s of type “%(type)s”: %(perms)s')
        else:
            format_str = ugettext(u'For %(set)s: %(perms)s')

        return format_str % args

    def _get_perms(self, user, entity):
        """@return an integer with binary flags for permissions"""
        ctype_id = self.ctype_id

        if not ctype_id or ctype_id == entity.entity_type_id:
            if self.set_type == SetCredentials.ESET_ALL:
                return self.value
            else: #SetCredentials.ESET_OWN
                user_id = entity.user_id
                if user.id == user_id or any(user_id == t.id for t in user.teams):
                    return self.value

        return EntityCredentials.NONE

    @staticmethod
    def get_perms(sc_sequence, user, entity):
        """@param sc_sequence Sequence of SetCredentials instances."""
        return reduce(or_op, (sc._get_perms(user, entity) for sc in sc_sequence), EntityCredentials.NONE)

    @staticmethod
    def _can_do(sc_sequence, user, model, owner=None, perm=EntityCredentials.VIEW):
        allowed_ctype_ids = (None, ContentType.objects.get_for_model(model).id) #TODO: factorise

        if owner is None: #None means: all user that allows the action
            filtered_sc_sequence = sc_sequence
        else:
            ESET_OWN = SetCredentials.ESET_OWN

            def generator():
                for sc in sc_sequence:
                    if sc.set_type == ESET_OWN:
                        if owner.is_team:
                            if user.id not in owner.teammates:
                                continue
                        elif user != owner:
                            continue

                    yield sc

            filtered_sc_sequence = generator()

        return any(sc.ctype_id in allowed_ctype_ids and sc.value & perm
                        for sc in filtered_sc_sequence
                  )

    @staticmethod
    def filter(sc_sequence, user, queryset, perm):
        """Filter a queryset of entities with credentials.
        @param sc_sequence Sequence of SetCredentials instances.
        @param user from django.contrib.auth.models.User instance.
        @param queryset Queryset of CremeEntity (or a child class of course).
        @param perm value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...)
        @return A new queryset.
        """
        allowed_ctype_ids = (None, ContentType.objects.get_for_model(queryset.model).id)
        ESET_ALL = SetCredentials.ESET_ALL

        #NB: we sorte to get ESET_ALL creds before ESET_OWN ones (more priority)
        for sc in sorted(sc_sequence, key=lambda sc: sc.set_type):
            if sc.ctype_id in allowed_ctype_ids and sc.value & perm:
                if sc.set_type == ESET_ALL:
                    return queryset #no additionnal filtering needed
                else: #SetCredentials.ESET_OWN
                    teams = user.teams
                    return queryset.filter(user__in=[user] + teams) if teams else \
                           queryset.filter(user=user)

        return queryset.none()

    def set_value(self, can_view, can_change, can_delete, can_link, can_unlink):
        """Set the 'value' attribute from 5 booleans"""
        value = EntityCredentials.NONE

        if can_view:   value |= EntityCredentials.VIEW
        if can_change: value |= EntityCredentials.CHANGE
        if can_delete: value |= EntityCredentials.DELETE
        if can_link:   value |= EntityCredentials.LINK
        if can_unlink: value |= EntityCredentials.UNLINK

        self.value = value


class UserProfile(Model):
    role    = ForeignKey(UserRole, verbose_name=_(u'Role'), null=True, on_delete=PROTECT)
    is_team = BooleanField(verbose_name=_(u'Is a team ?'), default=False)
    #TODO: delete 'permissions' table

    _teams = None
    _teammates = None

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.username if not self.is_team else ugettext('%s (team)') % self.username

    #TODO: full_clean() ?? (team + role= None etc...)

    #TODO find where forms are imported, making that method called BEFORE User has been contributed
    # @staticmethod
    # def get_common_ones():
    #     return User.objects.filter(is_staff=False)

    @property #NB notice that a cache is built
    def teams(self):
        assert not self.is_team

        teams = self._teams
        if teams is None:
            self._teams = teams = list(User.objects.filter(team_m2m_teamside__teammate=self))

        return teams

    @property #NB notice that cache and credentials are well updated when using this property
    def teammates(self):
        assert self.is_team

        teammates = self._teammates

        if teammates is None:
            logger.debug('User.teammates: Cache MISS for user_id=%s', self.id)
            self._teammates = teammates = {u.id: u for u in User.objects.filter(team_m2m__team=self)}
        else:
            logger.debug('User.teammates: Cache HIT for user_id=%s', self.id)

        return teammates

    @teammates.setter
    def teammates(self, users):
        assert self.is_team
        assert not any(user.is_team for user in users)

        old_teammates = self.teammates
        new_teammates = {u.id: u for u in users}

        old_set = set(old_teammates.iterkeys())
        new_set = set(new_teammates.iterkeys())

        users2remove = [old_teammates[user_id] for user_id in (old_set - new_set)]
        TeamM2M.objects.filter(team=self, teammate__in=users2remove).delete()

        users2add = [new_teammates[user_id] for user_id in (new_set - old_set)]
        for user in users2add:
            TeamM2M.objects.get_or_create(team=self, teammate=user)

        self._teammates = None #clear cache (we could rebuild it but ...)

    def _get_credentials(self, entity):
        creds_map = getattr(entity, '_credentials_map', None)

        if creds_map is None:
            entity._credentials_map = creds_map = {}
            creds = None
        else:
            creds = creds_map.get(self.id)

        if creds is None:
            logger.debug('UserProfile._get_credentials(): Cache MISS for id=%s user=%s', entity.id, self)
            creds_map[self.id] = creds = EntityCredentials(self, entity)
        else:
            logger.debug('UserProfile._get_credentials(): Cache HIT for id=%s user=%s', entity.id, self)

        return creds

    def has_perm_to_access(self, app_name):
        return self.is_superuser or self.role.is_app_allowed_or_administrable(app_name)

    def has_perm_to_admin(self, app_name):
        #return self.has_perm('%s.can_admin' % app_name) #todo: app_name in self.role.admin_4_apps + use this method in backend
        return self.is_superuser or (app_name in self.role.admin_4_apps)

    def has_perm_to_admin_or_die(self, app_name):
        if not self.has_perm_to_admin(app_name):
            try:
                verbose_name = creme_registry.get_app(app_name).verbose_name
            except NotRegistered:
                verbose_name = ugettext('Invalid app "%s"') % app_name

            raise PermissionDenied(ugettext('You are not allowed to configure this app: %s') %
                                        verbose_name
                                  )

    def has_perm_to_change(self, entity):
        if entity.is_deleted:
            return False

        get_related_entity = getattr(entity, 'get_related_entity', None)
        main_entity = get_related_entity() if get_related_entity else entity

        return self._get_credentials(main_entity).can_change()

    def has_perm_to_change_or_die(self, entity):
        if not self.has_perm_to_change(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to edit this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )

    def has_perm_to_create(self, model_or_entity):
        """Helper for has_perm() method.
        eg: user.has_perm('myapp.add_mymodel') => user.has_perm_to_create(MyModel)
        """
        meta = model_or_entity._meta
        return self.has_perm('%s.add_%s' % (meta.app_label, meta.object_name.lower()))

    def has_perm_to_create_or_die(self, model_or_entity):
        if not self.has_perm_to_create(model_or_entity):
            raise PermissionDenied(ugettext(u'You are not allowed to create: %s') %
                                        model_or_entity._meta.verbose_name
                                  )

    def has_perm_to_delete(self, entity):
        get_related_entity = getattr(entity, 'get_related_entity', None)
        if get_related_entity:
            return self._get_credentials(get_related_entity()).can_change()

        return self._get_credentials(entity).can_delete()

    def has_perm_to_delete_or_die(self, entity):
        if not self.has_perm_to_delete(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to delete this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )

    def has_perm_to_export(self, model_or_entity): #TODO: factorise with has_perm_to_create() ??
        """Helper for has_perm() method.
        eg: user.has_perm('myapp.export_mymodel') => user.has_perm_to_export(MyModel)
        """
        meta = model_or_entity._meta
        return self.has_perm('%s.export_%s' % (meta.app_label, meta.object_name.lower()))

    def has_perm_to_export_or_die(self, model_or_entity):
        if not self.has_perm_to_export(model_or_entity):
            raise PermissionDenied(ugettext(u'You are not allowed to export: %s') %
                                        model_or_entity._meta.verbose_name
                                  )

    def has_perm_to_link(self, entity_or_model, owner=None):
        """Can the user link a future entity of a given class ?
        @param entity_or_model {Instance of} class inheriting CremeEntity.
        @param owner (only used when 1rst param is a class) Instance of auth.User ;
                     owner of the (future) entity. 'None' means: is there an
                     owner (at least) that allows linking.
        """
        assert not self.is_team #teams can not be logged, it has no sense

        if isinstance(entity_or_model, CremeEntity):
            return False if entity_or_model.is_deleted else \
                   self._get_credentials(entity_or_model).can_link()

        assert issubclass(entity_or_model, CremeEntity)
        return True if self.is_superuser else \
               self.role.can_do_on_model(self, entity_or_model, owner, EntityCredentials.LINK)

    def has_perm_to_link_or_die(self, entity_or_model, owner=None): #TODO: factorise ??
        if not self.has_perm_to_link(entity_or_model, owner):
            if isinstance(entity_or_model, CremeEntity):
                msg = ugettext(u'You are not allowed to link this entity: %s') % \
                                        entity_or_model.allowed_unicode(self)
            else:
                msg = ugettext(u'You are not allowed to link: %s') % \
                            entity_or_model._meta.verbose_name

            raise PermissionDenied(msg)

    def has_perm_to_unlink(self, entity):
        return self._get_credentials(entity).can_unlink()

    def has_perm_to_unlink_or_die(self, entity):
        if not self.has_perm_to_unlink(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to unlink this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )

    def has_perm_to_view(self, entity):
        return self._get_credentials(entity).can_view()

    def has_perm_to_view_or_die(self, entity):
        if not self.has_perm_to_view(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to view this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )


#TODO: remove this class when we can contribute_to_model with a ManyToManyField
class TeamM2M(Model):
    team     = ForeignKey(User, related_name='team_m2m_teamside')
    teammate = ForeignKey(User, related_name='team_m2m')

    class Meta:
        app_label = 'creme_core'


#NB: We use a contribute_to_model() instead of regular Django's profile
# management to avoid having a additional DB table and creating a annoying
# signal handler to create the corresponding Profile object each time a User is
# created
contribute_to_model(UserProfile, User)

#TODO: we could also check related contact to find first_name, last_name
def _user_unicode(user):
    first_name = user.first_name
    last_name  = user.last_name

    if first_name and last_name:
        return ugettext(u"%(first_name)s %(last_name)s.") % {
                    'first_name': first_name,
                    'last_name':  last_name[0],
                }
    else:
        return user.username

User.__unicode__ = _user_unicode
User._meta.ordering = ('username',)

get_user_field = User._meta.get_field
for fname in ('first_name', 'password', 'is_staff', 'is_active', 'is_superuser',
              'last_login', 'date_joined', 'groups', 'user_permissions',
              'role', 'is_team',
             ):
    get_user_field(fname).set_tags(viewable=False)

get_user_field('username').verbose_name = _('Username')
get_user_field('last_name').verbose_name = _('Last name')
get_user_field('email').verbose_name = _('Email address')

del get_user_field

