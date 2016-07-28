# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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
import logging
from operator import or_ as or_op
from re import compile as re_compile

import pytz

from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, _user_has_perm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db.models import (Model, CharField, TextField, BooleanField,
        PositiveSmallIntegerField, PositiveIntegerField, EmailField,
        DateTimeField, ForeignKey, ManyToManyField, PROTECT, Q)
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext

from ..auth.entity_credentials import EntityCredentials
from ..registry import creme_registry, NotRegistered
from ..utils import split_filter
from ..utils.unicode_collation import collator
from .fields import CTypeForeignKey


logger = logging.getLogger(__name__)


class UserRole(Model):
    name              = CharField(_(u'Name'), max_length=100) # TODO: unique=True
    # superior         = ForeignKey('self', verbose_name=_(u"Superior"), null=True) #related_name='subordinates'
    creatable_ctypes  = ManyToManyField(ContentType, verbose_name=_(u'Creatable resources'),  related_name='roles_allowing_creation') # null=True,
    exportable_ctypes = ManyToManyField(ContentType, verbose_name=_(u'Exportable resources'), related_name='roles_allowing_export')   # null=True,
    raw_allowed_apps  = TextField(default='')  # Use 'allowed_apps' property
    raw_admin_4_apps  = TextField(default='')  # Use 'admin_4_apps' property

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(UserRole, self).__init__(*args, **kwargs)
        self._allowed_apps = None; self._extended_allowed_apps = None
        self._admin_4_apps = None; self._extended_admin_4_apps = None
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

    def _build_extended_apps(self, apps):
        ext_apps = (ext_app
                        for app in apps
                            for ext_app in creme_registry.get_extending_apps(app)
                   )

        return set(chain(apps, ext_apps))

    @property
    def extended_admin_4_apps(self):
        if self._extended_admin_4_apps is None:
            self._extended_admin_4_apps = self._build_extended_apps(self.admin_4_apps)

        return self._extended_admin_4_apps

    @property
    def extended_allowed_apps(self):
        if self._extended_allowed_apps is None:
            self._extended_allowed_apps = self._build_extended_apps(self.allowed_apps)

        return self._extended_allowed_apps

    def is_app_administrable(self, app_name):
        return app_name in self.extended_admin_4_apps

    def is_app_allowed_or_administrable(self, app_name):
        return (app_name in self.extended_allowed_apps) or self.is_app_administrable(app_name)

    def _build_apps_verbose(self, app_names):
        get_app = creme_registry.get_app
        apps = [get_app(app_name).verbose_name for app_name in app_names]
        apps.sort(key=collator.sort_key)

        return apps

    def get_admin_4_apps_verbose(self):  # For templates
        return self._build_apps_verbose(self.admin_4_apps)

    def get_allowed_apps_verbose(self):  # For templates
        return self._build_apps_verbose(self.allowed_apps)

    def can_create(self, app_name, model_name):
        """@return True if a model with ContentType(app_name, model_name) can be created."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._creatable_ctypes_set is None:
            self._creatable_ctypes_set = frozenset(self.creatable_ctypes.values_list('id', flat=True))

        return (ct.id in self._creatable_ctypes_set)

    def can_export(self, app_name, model_name):  # TODO: factorise with can_create() ??
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
        real_entity_class = entity.entity_type.model_class()

        if self.is_app_allowed_or_administrable(real_entity_class._meta.app_label):
            perms = SetCredentials.get_perms(self._get_setcredentials(), user, entity)
        else:
            perms = EntityCredentials.NONE

        return perms

    # TODO: factorise
    def filter(self, user, queryset, perm):
        """Filter a QuerySet of CremeEntities by the credentials related to this role.
        Beware, the model class must be a child class of CremeEntity, but cannot be CremeEntity itself.

        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser) ;
                     should be related to the UserRole instance.
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @return: A new (filtered) queryset on the same model.
        """
        from .entity import CremeEntity

        model = queryset.model
        assert issubclass(model, CremeEntity)
        assert model is not CremeEntity

        if self.is_app_allowed_or_administrable(model._meta.app_label):
            queryset = SetCredentials.filter(self._get_setcredentials(), user, queryset, perm)
        else:
            queryset = queryset.none()

        return queryset

    def filter_entities(self, user, queryset, perm):
        """Filter a QuerySet of CremeEntities by the credentials related to this role.
        Beware, model class must be CremeEntity ; it cannot be a child class of CremeEntity.

        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser) ;
                     should be related to the UserRole instance.
        @param queryset: A Queryset with model=CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @return: A new (filtered) queryset on the same model.
        """
        from creme.creme_core.models import CremeEntity
        assert queryset.model is CremeEntity

        from ..registry import creme_registry

        is_app_allowed = self.is_app_allowed_or_administrable

        return SetCredentials.filter_entities(
                    self._get_setcredentials(), user, queryset, perm,
                    models=[model
                                for model in creme_registry.iter_entity_models()
                                    if is_app_allowed(model._meta.app_label)
                           ],
                )


class SetCredentials(Model):
    role     = ForeignKey(UserRole, related_name='credentials')
    value    = PositiveSmallIntegerField()  # See EntityCredentials.VIEW|CHANGE|DELETE|LINK|UNLINK
    set_type = PositiveIntegerField()  # See SetCredentials.ESET_* TODO: choices ?
    ctype    = CTypeForeignKey(null=True, blank=True)
    # entity  = ForeignKey(CremeEntity, null=True) ??

    # 'ESET' means 'Entities SET'
    ESET_ALL = 1  # => all entities
    ESET_OWN = 2  # => his own entities

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
            else:  # SetCredentials.ESET_OWN
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

        if owner is None:  # None means: all users who are allowed to do the action
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
        """Filter a queryset of entities with the given credentials.
        Beware, the model class must be a child class of CremeEntity, but cannot be CremeEntity itself.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser).
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @return: A new queryset on the same model.
        """
        from .entity import CremeEntity

        model = queryset.model
        assert issubclass(model, CremeEntity)
        assert model is not CremeEntity

        allowed_ctype_ids = (None, ContentType.objects.get_for_model(model).id)
        ESET_ALL = SetCredentials.ESET_ALL

        # NB: we sort to get ESET_ALL creds before ESET_OWN ones (more priority)
        for sc in sorted(sc_sequence, key=lambda sc: sc.set_type):
            if sc.ctype_id in allowed_ctype_ids and sc.value & perm:
                if sc.set_type == ESET_ALL:
                    return queryset  # No additional filtering needed
                else:  # SetCredentials.ESET_OWN
                    teams = user.teams
                    return queryset.filter(user__in=[user] + teams) if teams else \
                           queryset.filter(user=user)

        return queryset.none()

    @staticmethod
    def filter_entities(sc_sequence, user, queryset, perm, models):
        """Filter a queryset of entities with the given credentials.
        Beware, model class must be CremeEntity ; it cannot be a child class of CremeEntity.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser).e.
        @param queryset: Queryset with model=CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @param models: An iterable of CremeEntity-child-classes, corresponding to allowed models.
        @return: A new queryset on CremeEntity.
        """
        from .entity import CremeEntity
        assert queryset.model is CremeEntity

        get_for_model = ContentType.objects.get_for_model
        ct_ids = {get_for_model(model).id for model in models}

        ESET_ALL = SetCredentials.ESET_ALL
        sc_all, sc_owner = split_filter(predicate=(lambda sc: sc.set_type == ESET_ALL),
                                        iterable=(sc for sc in sc_sequence if sc.value & perm),
                                       )

        def extract_ct_ids(sc_instances):
            extracted_ct_ids = []

            for sc in sc_instances:
                ct_id = sc.ctype_id

                if ct_id is None:
                    extracted_ct_ids.extend(ct_ids)
                    ct_ids.clear()
                    break

                if ct_id in ct_ids:
                    extracted_ct_ids.append(ct_id)
                    ct_ids.remove(ct_id)

            return extracted_ct_ids

        ctype_ids_all = extract_ct_ids(sc_all)
        ctype_ids_owner = extract_ct_ids(sc_owner)

        if not ctype_ids_all and not ctype_ids_owner:
            queryset = queryset.none()
        else:
            q = Q(entity_type_id__in=ctype_ids_all) if ctype_ids_all else Q()

            if ctype_ids_owner:
                teams = user.teams
                kwargs = {'user__in': [user] + teams} if teams else {'user': user}
                q |= Q(entity_type_id__in=ctype_ids_owner, **kwargs)

            queryset = queryset.filter(q)

        return queryset

    def set_value(self, can_view, can_change, can_delete, can_link, can_unlink):
        """Set the 'value' attribute from 5 booleans"""
        value = EntityCredentials.NONE

        if can_view:   value |= EntityCredentials.VIEW
        if can_change: value |= EntityCredentials.CHANGE
        if can_delete: value |= EntityCredentials.DELETE
        if can_link:   value |= EntityCredentials.LINK
        if can_unlink: value |= EntityCredentials.UNLINK

        self.value = value


class CremeUserManager(BaseUserManager):
    def create_user(self, username, first_name, last_name, email, password=None, **extra_fields):
        "Creates and saves a User"
        if not username:
            raise ValueError('The given username must be set')

        user = self.model(username=username,
                          first_name=first_name, last_name=last_name,
                          email=self.normalize_email(email),
                          **extra_fields
                         )

        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, username, first_name, last_name, email, password=None, **extra_fields):
        "Creates and saves a superuser"
        extra_fields['is_superuser'] = True

        return self.create_user(username=username,
                                first_name=first_name, last_name=last_name,
                                email=email,
                                password=password,
                                **extra_fields
                               )

    # TODO: create_staff_user ??

    def get_admin(self):
        user_qs = self.get_queryset().order_by('id')

        return user_qs.filter(is_superuser=True, is_staff=False).first() or \
               user_qs.filter(is_superuser=True).first() or \
               user_qs[0]


class CremeUser(AbstractBaseUser):
    username = CharField(_('Username'), max_length=30, unique=True,
                         help_text=_('Required. 30 characters or fewer. '
                                     'Letters, digits and @/./+/-/_ only.'
                                    ),
                         validators=[RegexValidator(re_compile('^[\w.@+-]+$'),
                                                    _('Enter a valid username.'),
                                                    'invalid',
                                                   ),
                                    ],
                        )
    last_name  = CharField(_(u'Last name'), max_length=100, blank=True)
    first_name = CharField(_(u'First name'), max_length=100, blank=True)\
                          .set_tags(viewable=False)  # NB: blank=True for teams
    email      = EmailField(_('Email address'), blank=True)

    date_joined = DateTimeField(_('Date joined'), default=now).set_tags(viewable=False)
    is_active   = BooleanField(_('Is active?'), default=True,
                               # help_text=_('Designates whether this user should be treated as '
                               #             'active. Deselect this instead of deleting accounts.'
                               #            ), TODO
                              ).set_tags(viewable=False)

    is_staff     = BooleanField(_('Is staff?'), default=False,
                                # help_text=_('Designates whether the user can log into this admin site.'), TODO
                               ).set_tags(viewable=False)
    is_superuser = BooleanField(_('Is a superuser?'), default=False,
                                # help_text=_('If True, can create groups & events.') TODO
                               ).set_tags(viewable=False)
    role         = ForeignKey(UserRole, verbose_name=_(u'Role'), null=True,
                              on_delete=PROTECT,
                             ).set_tags(viewable=False)

    is_team       = BooleanField(verbose_name=_(u'Is a team?'), default=False).set_tags(viewable=False)
    teammates_set = ManyToManyField('self', verbose_name=_(u'Teammates'),
                                    symmetrical=False, related_name='teams_set',
                                   ).set_tags(viewable=False)

    time_zone = CharField(_(u'Time zone'), max_length=50, default=settings.TIME_ZONE,
                          choices=[(tz, tz) for tz in pytz.common_timezones],
                         ).set_tags(viewable=False)
    theme     = CharField(_(u'Theme'), max_length=50,
                          default=settings.THEMES[0][0],
                          choices=settings.THEMES,
                         ).set_tags(viewable=False)

    # NB: do not use directly ; use the property 'settings'
    json_settings = TextField(editable=False, default='{}').set_tags(viewable=False)  # TODO: JSONField ?

    objects = CremeUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    _settings = None
    _teams = None
    _teammates = None

    class Meta:
        # abstract = True TODO class  AbstractCremeUser ?
        ordering = ('username',)
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        app_label = 'creme_core'

    def __unicode__(self):
        return self.get_full_name()

    def get_full_name(self):
        # TODO: we could also check related contact to find first_name, last_name
        first_name = self.first_name
        last_name  = self.last_name

        if first_name and last_name:
            return ugettext(u"%(first_name)s %(last_name)s.") % {
                        'first_name': first_name,
                        'last_name':  last_name[0],
                    }
        else:
            return self.username  # TODO: if not self.is_team else ugettext('%s (team)') % self.username

    def get_short_name(self):
        return self.username

    # TODO: def clean() ?? (team + role= None etc...)

    # TODO find where forms are imported, making that method called BEFORE User has been contributed
    # @staticmethod
    # def get_common_ones():
    #     return User.objects.filter(is_staff=False)

    @property
    def settings(self):
        settings = self._settings

        if settings is None:
            from ..core.setting_key import UserSettingValueManager
            settings = self._settings = UserSettingValueManager(user_class=self.__class__,
                                                                user_id=self.id,
                                                                json_settings=self.json_settings,
                                                               )

        return settings

    @property
    def theme_info(self):
        THEMES = settings.THEMES
        theme_name = self.theme

        for theme_info in settings.THEMES:
            if theme_name == theme_info[0]:
                return theme_info

        return THEMES[0]

    @property  # NB notice that a cache is built
    def teams(self):
        assert not self.is_team

        teams = self._teams
        if teams is None:
            self._teams = teams = list(self.teams_set.all())

        return teams

    @property  # NB notice that cache and credentials are well updated when using this property
    def teammates(self):
        assert self.is_team

        teammates = self._teammates

        if teammates is None:
            logger.debug('User.teammates: Cache MISS for user_id=%s', self.id)
            self._teammates = teammates = {u.id: u for u in self.teammates_set.all()}
        else:
            logger.debug('User.teammates: Cache HIT for user_id=%s', self.id)

        return teammates

    @teammates.setter
    def teammates(self, users):
        assert self.is_team
        assert not any(user.is_team for user in users)

        self.teammates_set = users
        self._teammates = None  # Clear cache (we could rebuild it but ...)

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

    # Copied from auth.models.PermissionsMixin.has_perm
    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """
        if self.is_active and self.is_superuser:
            return True

        # Check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        has_perm = self.has_perm

        return all(has_perm(perm, obj) for perm in perm_list)

    def has_perm_to_access(self, app_name):
        return self.is_superuser or self.role.is_app_allowed_or_administrable(app_name)

    def has_perm_to_admin(self, app_name):
        return self.is_superuser or self.role.is_app_administrable(app_name)

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

        # get_related_entity = getattr(entity, 'get_related_entity', None)
        # main_entity = get_related_entity() if get_related_entity else entity
        main_entity = entity.get_real_entity().get_related_entity() \
                      if hasattr(entity.entity_type.model_class(), 'get_related_entity') \
                      else entity

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
        # get_related_entity = getattr(entity, 'get_related_entity', None)
        # if get_related_entity:
        #     return self._get_credentials(get_related_entity()).can_change()
        if hasattr(entity.entity_type.model_class(), 'get_related_entity'):  # TODO: factorise
            return self._get_credentials(entity.get_real_entity().get_related_entity()).can_change()

        return self._get_credentials(entity).can_delete()

    def has_perm_to_delete_or_die(self, entity):
        if not self.has_perm_to_delete(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to delete this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )

    def has_perm_to_export(self, model_or_entity):  # TODO: factorise with has_perm_to_create() ??
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
        assert not self.is_team  # Teams can not be logged, it has no sense

        from .entity import CremeEntity

        if isinstance(entity_or_model, CremeEntity):
            # TODO: what about related_entity ?
            return False if entity_or_model.is_deleted else \
                   self._get_credentials(entity_or_model).can_link()

        assert issubclass(entity_or_model, CremeEntity)
        return True if self.is_superuser else \
               self.role.can_do_on_model(self, entity_or_model, owner, EntityCredentials.LINK)

    def has_perm_to_link_or_die(self, entity_or_model, owner=None):  # TODO: factorise ??
        from .entity import CremeEntity

        if not self.has_perm_to_link(entity_or_model, owner):
            if isinstance(entity_or_model, CremeEntity):
                msg = ugettext(u'You are not allowed to link this entity: %s') % \
                                        entity_or_model.allowed_unicode(self)
            else:
                msg = ugettext(u'You are not allowed to link: %s') % \
                            entity_or_model._meta.verbose_name

            raise PermissionDenied(msg)

    def has_perm_to_unlink(self, entity):
        # TODO: what about related_entity ?
        return self._get_credentials(entity).can_unlink()

    def has_perm_to_unlink_or_die(self, entity):
        if not self.has_perm_to_unlink(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to unlink this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )

    def has_perm_to_view(self, entity):
        # TODO: what about related_entity ?
        return self._get_credentials(entity).can_view()

    def has_perm_to_view_or_die(self, entity):
        if not self.has_perm_to_view(entity):
            raise PermissionDenied(ugettext(u'You are not allowed to view this entity: %s') %
                                    entity.allowed_unicode(self)
                                  )


get_user_field = CremeUser._meta.get_field
for fname in ('password', 'last_login'):
    get_user_field(fname).set_tags(viewable=False)

del get_user_field

