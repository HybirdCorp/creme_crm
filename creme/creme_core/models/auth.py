################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
import uuid
from collections import OrderedDict, defaultdict
from functools import reduce
from operator import or_ as or_op
from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_backends
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    _user_has_perm,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.functional import partition
from django.utils.timezone import now, zoneinfo
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..auth import EntityCredentials
from ..auth.special import SpecialPermission, special_perm_registry
from ..core.setting_key import UserSettingValueManager
from ..utils.content_type import as_ctype, as_model
from ..utils.unicode_collation import collator
from . import fields as core_fields
from .custom_entity import CustomEntityType
from .entity import CremeEntity
from .utils import model_verbose_name

if TYPE_CHECKING:
    from typing import DefaultDict, Iterable, Sequence, Type, Union

    from ..core.sandbox import SandboxType
    from .base import CremeModel

    EntityInstanceOrClass = Union[Type[CremeEntity], CremeEntity]
    EntityInstanceOrClassOrCType = Union[Type[CremeEntity], CremeEntity, ContentType]

logger = logging.getLogger(__name__)


class UserRoleManager(models.Manager):
    def get_by_portable_key(self, key: str) -> UserRole:
        return self.get(uuid=key)

    def smart_create(self, *,
                     creatable_models: Iterable[type[CremeEntity]] = (),
                     listable_models: Iterable[type[CremeEntity]] = (),
                     exportable_models: Iterable[type[CremeEntity]] = (),
                     **kwargs
                     ) -> UserRole:
        """Helper to use instead of 'create()': it takes models instead of
        ContentType instances for the 2 many-to-many fields.
        """
        role = self.create(**kwargs)
        get_ct = ContentType.objects.get_for_model

        def as_ctypes(models):
            return [get_ct(model) for model in models]

        if creatable_models:
            role.creatable_ctypes.set(as_ctypes(creatable_models))

        if listable_models:
            role.listable_ctypes.set(as_ctypes(listable_models))

        if exportable_models:
            role.exportable_ctypes.set(as_ctypes(exportable_models))

        return role

    smart_create.alters_data = True


class UserRole(models.Model):
    name = models.CharField(_('Name'), max_length=100, unique=True)
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    deactivated_on = models.DateTimeField(
        _('Deactivated on'), null=True, default=None, editable=False,
    )

    # superior = ForeignKey('self', verbose_name=_('Superior'), null=True)
    # TODO: CTypeManyToManyField ?
    creatable_ctypes = models.ManyToManyField(
        ContentType, verbose_name=_('Creatable resources'),
        related_name='roles_allowing_creation',
    )
    listable_ctypes = models.ManyToManyField(
        ContentType, verbose_name=_('Listable resources'),
        related_name='roles_allowing_list',  # TODO: '+' ?
    )
    exportable_ctypes = models.ManyToManyField(
        ContentType, verbose_name=_('Exportable resources'),
        related_name='roles_allowing_export',
    )
    raw_allowed_apps = models.TextField(default='')  # Use 'allowed_apps' property
    raw_admin_4_apps = models.TextField(default='')  # Use 'admin_4_apps' property

    raw_special_perms = models.TextField(default='')  # Use 'special_permissions' property

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    objects = UserRoleManager()

    creation_label = _('Create a role')
    save_label     = _('Save the role')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ('name',)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._allowed_apps: set[str] | None = None
        self._extended_allowed_apps: set[str] | None = None

        self._admin_4_apps: set[str] | None = None
        self._extended_admin_4_apps: set[str] | None = None

        self._special_perms: dict[str, SpecialPermission] | None = None

        self._creatable_ctypes_set: frozenset[int] | None = None
        self._exportable_ctypes_set: frozenset[int] | None = None
        self._listable_ctypes_set: frozenset[int] | None = None

        self._setcredentials: list[SetCredentials] | None = None

    def __str__(self):
        return self.name if self.deactivated_on is None else gettext(
            '{role} [deactivated]'
        ).format(role=self.name)

    @property
    def admin_4_apps(self) -> set[str]:
        if self._admin_4_apps is None:
            self._admin_4_apps = {
                app_name
                for app_name in self.raw_admin_4_apps.split('\n')
                if app_name
            }

        return self._admin_4_apps

    @admin_4_apps.setter
    def admin_4_apps(self, apps: Sequence[str]) -> None:
        """@param apps: Sequence of app labels (strings)."""
        self._admin_4_apps = {*apps}
        self.raw_admin_4_apps = '\n'.join(apps)

    @property
    def allowed_apps(self) -> set[str]:
        if self._allowed_apps is None:
            self._allowed_apps = {
                app_name
                for app_name in self.raw_allowed_apps.split('\n')
                if app_name
            }

        # TODO: FrozenSet to avoid modifications ?
        return self._allowed_apps

    @allowed_apps.setter
    def allowed_apps(self, apps: Sequence[str]) -> None:
        """@param apps: Sequence of app labels (strings)."""
        self._allowed_apps = {*apps}
        self.raw_allowed_apps = '\n'.join(apps)

    @property
    def special_permissions(self) -> dict[str, SpecialPermission]:
        if self._special_perms is None:
            self._special_perms = {
                perm_id: perm
                for perm_id in self.raw_special_perms.split('\n')
                if perm_id and (perm := special_perm_registry.get_permission(perm_id))
            }

        return self._special_perms

    @special_permissions.setter
    def special_permissions(self, perms: Iterable[SpecialPermission]) -> None:
        self._special_perms = {perm.id: perm for perm in perms}
        self.raw_special_perms = '\n'.join(self._special_perms.keys())

    @staticmethod
    def _build_extended_apps(apps: Iterable[str]) -> set[str]:
        from ..apps import extended_app_configs

        return {app_config.label for app_config in extended_app_configs(apps)}

    @property
    def extended_admin_4_apps(self) -> set[str]:
        if self._extended_admin_4_apps is None:
            self._extended_admin_4_apps = self._build_extended_apps(self.admin_4_apps)

        return self._extended_admin_4_apps

    @property
    def extended_allowed_apps(self) -> set[str]:
        if self._extended_allowed_apps is None:
            self._extended_allowed_apps = self._build_extended_apps(self.allowed_apps)

        return self._extended_allowed_apps

    def is_app_administrable(self, app_name: str) -> bool:  # TODO: rename "app_label"
        return self.deactivated_on is None and app_name in self.extended_admin_4_apps

    # TODO: rename "app_label"
    def is_app_allowed_or_administrable(self, app_name: str) -> bool:
        return self.deactivated_on is None and (
            (app_name in self.extended_allowed_apps)
            or self.is_app_administrable(app_name)
        )

    # TODO: rename app_labels
    def _build_apps_verbose(self, app_names: Iterable[str]) -> list[str]:
        verbose_names = []
        get_app = apps.get_app_config

        for app_label in app_names:
            try:
                app = get_app(app_label)
            except LookupError:
                logger.warning(
                    'The app "%s" seems not registered (from UserRole "%s").',
                    app_label, self,
                )
            else:
                verbose_names.append(app.verbose_name)  # TODO: str() ??

        verbose_names.sort(key=collator.sort_key)

        return verbose_names

    def get_admin_4_apps_verbose(self) -> list[str]:  # For templates
        return self._build_apps_verbose(self.admin_4_apps)

    def get_allowed_apps_verbose(self) -> list[str]:  # For templates
        return self._build_apps_verbose(self.allowed_apps)

    def can_create(self, ctype: ContentType, /) -> bool:  # TODO: accept model too?
        """Creation credentials.
        @param ctype: ContentType of the model we want to create.
        @return True if the model can be created.
        """
        if self.deactivated_on:
            return False

        if self._creatable_ctypes_set is None:
            self._creatable_ctypes_set = frozenset(
                self.creatable_ctypes.values_list('id', flat=True)
            )

        return ctype.id in self._creatable_ctypes_set

    # TODO: factorise with can_create() ??
    def can_export(self, ctype: ContentType, /) -> bool:
        """Mass-export credentials.
        @param ctype: ContentType of the model we want to export.
        @return True if the model can be exported.
        """
        if self.deactivated_on:
            return False

        if self._exportable_ctypes_set is None:
            self._exportable_ctypes_set = frozenset(
                self.exportable_ctypes.values_list('id', flat=True)
            )

        return ctype.id in self._exportable_ctypes_set

    def can_list(self, ctype: ContentType, /) -> bool:
        """List-view credentials.
        @param ctype: ContentType of the model we want to list.
        @return True if the model can be listed.
        """
        if self.deactivated_on:
            return False

        if self._listable_ctypes_set is None:
            self._listable_ctypes_set = frozenset(
                self.listable_ctypes.values_list('id', flat=True)
            )

        return ctype.id in self._listable_ctypes_set

    def can_do_on_model(self, user, model: CremeEntity, owner, perm: int) -> bool:
        """Can the given user execute an action (VIEW, CHANGE etc..) on this model.
        @param user: User instance; user which tries to do something.
        @param model: Class inheriting CremeEntity
        @param owner: User instance; owner of the not-yet-existing instance of 'model'.
               None means any user that would be allowed to perform the action
               (if it exists of course).
        @param perm: See <EntityCredentials.{VIEW, CHANGE, ...}> .
        """
        if not self.is_app_allowed_or_administrable(model._meta.app_label):
            return False

        return SetCredentials._can_do(self._get_setcredentials(), user, model, owner, perm)

    def _get_setcredentials(self) -> list[SetCredentials]:
        setcredentials = self._setcredentials

        if setcredentials is None:
            logger.debug('UserRole.get_credentials(): Cache MISS for id=%s', self.id)
            self._setcredentials = setcredentials = [*self.credentials.all()]
        else:
            logger.debug('UserRole.get_credentials(): Cache HIT for id=%s', self.id)

        return setcredentials

    def get_perms(self, user, entity: CremeEntity) -> int:
        """@return (can_view, can_change, can_delete, can_link, can_unlink) 5 boolean tuple."""
        real_entity_class = entity.entity_type.model_class()

        if self.is_app_allowed_or_administrable(real_entity_class._meta.app_label):
            perms = SetCredentials.get_perms(self._get_setcredentials(), user, entity)
        else:
            perms = EntityCredentials.NONE

        return perms

    # TODO: factorise
    def filter(self,
               user,
               queryset: QuerySet,
               perm: int,
               ) -> QuerySet:
        """Filter a QuerySet of CremeEntities by the credentials related to this role.
        Beware, the model class must be a child class of CremeEntity,
        but cannot be CremeEntity itself.

        @param user: A <django.contrib.auth.get_user_model()> instance (e.g. CremeUser) ;
                     should be related to the UserRole instance.
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A combination of values in (EntityCredentials.{VIEW, CHANGE} etc...).
               E.g. 'EntityCredentials.DELETE'
                   'EntityCredentials.VIEW | EntityCredentials.CHANGE'
        @return: A new (filtered) queryset on the same model.
        """
        model = queryset.model
        assert issubclass(model, CremeEntity)
        assert model is not CremeEntity

        if self.is_app_allowed_or_administrable(model._meta.app_label):
            queryset = SetCredentials.filter(self._get_setcredentials(), user, queryset, perm)
        else:
            queryset = queryset.none()

        return queryset

    def filter_entities(self,
                        user,
                        queryset: QuerySet,
                        perm: int,
                        as_model: type[CremeEntity] | None = None,
                        ) -> QuerySet:
        """Filter a QuerySet of CremeEntities by the credentials related to this role.
        Beware, model class must be CremeEntity ; it cannot be a child class
        of CremeEntity.

        @param user: A django.contrib.auth.get_user_model() instance (e.g. CremeUser) ;
               should be related to the UserRole instance.
        @param queryset: A Queryset with model=CremeEntity.
        @param perm: A value in EntityCredentials.{VIEW, CHANGE, ...}.
               If the argument "as_model" is not None, you can use a combination
               of values like 'EntityCredentials.VIEW | EntityCredentials.CHANGE'.
        @param as_model: A model inheriting CremeEntity, or None.
               If a model is given, all the entities in the queryset are
               filtered with the credentials for this model.
               BEWARE: you should probably use this feature only if the queryset
               is already filtered by its field 'entity_type' (to keep only
               entities of the right model, & so do not make mistakes with credentials).
        @return: A new (filtered) queryset on the same model.
        @raise: EntityCredentials.FilteringError if there is an EntityFilter,
                which cannot be used on CremeEntity, in the SetCredentials
                concerning the models of the allowed apps.
        """
        assert queryset.model is CremeEntity

        from ..registry import creme_registry

        is_app_allowed = self.is_app_allowed_or_administrable

        return SetCredentials.filter_entities(
            sc_sequence=self._get_setcredentials(),
            user=user, queryset=queryset,
            perm=perm,
            models=[
                model
                for model in creme_registry.iter_entity_models()
                if is_app_allowed(model._meta.app_label)
            ],
            as_model=as_model,
        )

    def portable_key(self) -> str:
        return str(self.uuid)

    def save(self, *args, **kwargs):
        # TODO: remove in the next major version
        # NB see creme_core.populate.py (we mark the role to avoid a
        #    modification if the command is run again).
        self.extra_data['listablemigr'] = True

        super().save(*args, **kwargs)


class SetCredentials(models.Model):
    # 'ESET' means 'Entities SET'
    ESET_ALL    = 1  # => all entities
    ESET_OWN    = 2  # => his own entities
    ESET_FILTER = 3  # => use an EntityFilter

    ESETS_MAP = OrderedDict([
        (ESET_ALL,    _('All entities')),
        (ESET_OWN,    _("User's own entities")),
        (ESET_FILTER, _('Filtered entities')),
    ])  # TODO: inline ?

    role = models.ForeignKey(
        UserRole,
        related_name='credentials', on_delete=models.CASCADE, editable=False,
    )
    # See EntityCredentials.VIEW|CHANGE|DELETE|LINK|UNLINK
    value = models.PositiveSmallIntegerField()
    set_type = models.PositiveIntegerField(
        verbose_name=_('Type of entities set'),
        choices=ESETS_MAP.items(),
        default=ESET_ALL,
        help_text=_(
            'The choice «Filtered entities» allows to configure credentials '
            'based on values of fields or relationships for example.'
        ),
    )
    ctype = core_fields.EntityCTypeForeignKey(
        verbose_name=_('Apply to a specific type'),
        # NB: NULL means "No specific type" (i.e. any kind of CremeEntity)
        null=True, blank=True,
    )
    # entity  = models.ForeignKey(CremeEntity, null=True) ??
    forbidden = models.BooleanField(
        verbose_name=_('Allow or forbid?'),
        default=False,
        choices=[
            (False, _('The users are allowed to perform the selected actions')),
            (True,  _('The users are NOT allowed to perform the selected actions')),
        ],
        help_text=_(
            'Notice that actions which are forbidden & allowed at '
            'the same time are considered as forbidden when final '
            'permissions are computed.'
        ),
    )
    efilter = models.ForeignKey(
        'EntityFilter', editable=False, null=True, on_delete=models.PROTECT,
    )

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        value = self.value
        forbidden = self.forbidden
        perms = []
        append = perms.append

        if value is not None:
            if value & EntityCredentials.VIEW:
                append(gettext('view'))

            if value & EntityCredentials.CHANGE:
                append(gettext('change'))

            if value & EntityCredentials.DELETE:
                append(gettext('delete'))

            if value & EntityCredentials.LINK:
                append(gettext('link'))

            if value & EntityCredentials.UNLINK:
                append(gettext('unlink'))

        if not perms:
            append(
                gettext('nothing forbidden') if forbidden else
                gettext('nothing allowed')
            )

        args = {
            'set':   self.get_set_type_display(),
            'perms': ', '.join(perms),
        }

        if self.ctype:
            args['type'] = self.ctype
            format_str = (
                gettext('For “{set}“ of type “{type}” it is forbidden to: {perms}')
                if forbidden else
                gettext('For “{set}“ of type “{type}” it is allowed to: {perms}')
            )
        else:
            format_str = (
                gettext('For “{set}“ it is forbidden to: {perms}')
                if forbidden else
                gettext('For “{set}“ it is allowed to: {perms}')
            )

        return format_str.format(**args)

    def _get_perms(self, user, entity: CremeEntity) -> int:
        """@return An integer with binary flags for permissions."""
        ctype_id = self.ctype_id

        if not ctype_id or ctype_id == entity.entity_type_id:
            match self.set_type:
                case SetCredentials.ESET_ALL:
                    return self.value
                case SetCredentials.ESET_OWN:
                    user_id = entity.user_id
                    if user.id == user_id or any(user_id == t.id for t in user.teams):
                        return self.value
                case _:  # SetCredentials.ESET_FILTER
                    if self.efilter.accept(entity=entity.get_real_entity(), user=user):
                        return self.value

        return EntityCredentials.NONE

    @staticmethod
    def get_perms(sc_sequence: Sequence[SetCredentials],
                  user,
                  entity: CremeEntity,
                  ) -> int:
        """@param sc_sequence: Sequence of SetCredentials instances."""
        perms = reduce(
            or_op,
            (sc._get_perms(user, entity) for sc in sc_sequence if not sc.forbidden),
            EntityCredentials.NONE
        )

        for sc in sc_sequence:
            if sc.forbidden:
                perms &= ~sc._get_perms(user, entity)

        return perms

    @classmethod
    def _can_do(cls,
                sc_sequence: Sequence[SetCredentials],
                user,
                model: type[CremeEntity],
                owner=None,
                perm: int = EntityCredentials.VIEW,
                ) -> bool:
        if owner is None:
            def user_is_concerned(sc):
                return not sc.forbidden
        else:
            def user_is_concerned(sc):
                return user.id in owner.teammates if owner.is_team else user == owner

        ESET_ALL = cls.ESET_ALL
        ESET_OWN = cls.ESET_OWN
        allowed_ctype_ids = (None, ContentType.objects.get_for_model(model).id)  # TODO: factorise
        allowed_found = False

        for sc in sc_sequence:
            if sc.ctype_id in allowed_ctype_ids and sc.value & perm:
                set_type = sc.set_type

                # NB: it's hard to manage ESET_FILTER in a satisfactory way,
                #     so we ignore this type of credentials when checking models
                #     (so LINK credentials + filter == no relationships adding at entity creation).
                if set_type == ESET_ALL or (set_type == ESET_OWN and user_is_concerned(sc)):
                    if sc.forbidden:
                        return False
                    else:
                        allowed_found = True

        return allowed_found

    @classmethod
    def _aux_filter(cls,
                    model: type[CremeEntity],
                    sc_sequence: Sequence[SetCredentials],
                    user,
                    queryset: QuerySet,
                    perm: int,
                    ) -> QuerySet:
        allowed_ctype_ids = {None, ContentType.objects.get_for_model(model).id}
        ESET_ALL = cls.ESET_ALL
        ESET_OWN = cls.ESET_OWN

        filtered_qs = queryset

        # TODO: _PERMS_MAP public ?
        for single_perm in EntityCredentials._PERMS_MAP.values():
            if not single_perm & perm:
                continue

            allowed, forbidden = partition(
                lambda sc: sc.forbidden,
                sorted(
                    (
                        sc
                        for sc in sc_sequence
                        if sc.ctype_id in allowed_ctype_ids and sc.value & single_perm
                    ),
                    # NB: we sort to get ESET_ALL creds before ESET_OWN ones,
                    #     then ESET_FILTER ones.
                    key=lambda sc: sc.set_type,
                )
            )

            if not allowed:
                return queryset.none()

            if any(f.set_type == ESET_ALL for f in forbidden):
                return queryset.none()

            def user_filtering_kwargs():  # TODO: cache/lazy
                teams = user.teams
                return {'user__in': [user, *teams]} if teams else {'user': user}

            q = Q()
            for cred in allowed:
                set_type = cred.set_type

                if set_type == ESET_ALL:
                    break

                if set_type == ESET_OWN:
                    q |= Q(**user_filtering_kwargs())
                else:  # SetCredentials.ESET_FILTER
                    # TODO: distinct ? (see EntityFilter.filter())
                    q |= cred.efilter.get_q(user=user)
            else:
                filtered_qs = filtered_qs.filter(q)

            for cred in forbidden:
                if cred.set_type == ESET_OWN:
                    filtered_qs = filtered_qs.exclude(**user_filtering_kwargs())
                else:  # SetCredentials.ESET_FILTER
                    filtered_qs = filtered_qs.exclude(cred.efilter.get_q(user=user))

        return filtered_qs

    @classmethod
    def filter(cls,
               sc_sequence: Sequence[SetCredentials],
               user,
               queryset: QuerySet,
               perm: int,
               ) -> QuerySet:
        """Filter a queryset of entities with the given credentials.
        Beware, the model class must be a child class of CremeEntity,
        but cannot be CremeEntity itself.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A <django.contrib.auth.get_user_model()> instance (e.g. CremeUser).
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A combination of values in EntityCredentials.{VIEW, CHANGE, ...}.
               E.g. 'EntityCredentials.DELETE'
                   'EntityCredentials.VIEW | EntityCredentials.CHANGE'
        @return: A new queryset on the same model.
        """
        model = queryset.model
        assert issubclass(model, CremeEntity)
        assert model is not CremeEntity

        return cls._aux_filter(
            model=model, sc_sequence=sc_sequence, user=user,
            queryset=queryset, perm=perm,
        )

    @classmethod
    def filter_entities(cls,
                        sc_sequence: Sequence[SetCredentials],
                        user,
                        queryset: QuerySet,
                        perm: int,
                        models: Iterable[type[CremeEntity]],
                        as_model=None,
                        ) -> QuerySet:
        """Filter a queryset of entities with the given credentials.
        Beware, model class must be CremeEntity ; it cannot be a child class
        of CremeEntity.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A django.contrib.auth.get_user_model() instance (e.g. CremeUser).
        @param queryset: Queryset with model=CremeEntity.
        @param perm: A value in EntityCredentials.{VIEW, CHANGE, ...}.
               If the argument "as_model" is not None, you can use a combination
               of values like 'EntityCredentials.VIEW | EntityCredentials.CHANGE'.
        @param models: An iterable of CremeEntity-child-classes, corresponding
               to allowed models.
        @param as_model: A model inheriting CremeEntity, or None. If a model is
               given, all the entities in the queryset are filtered with the
               credentials for this model.
               BEWARE: you should probably use this feature only if the queryset
               is already filtered by its field 'entity_type' (to keep only
               entities of the right model, & so do not make mistakes with credentials).
        @return: A new queryset on CremeEntity.
        @raise: EntityCredentials.FilteringError if an EntityFilter which cannot
                be used on CremeEntity is found in <sc_sequence>.
        """
        assert queryset.model is CremeEntity

        get_for_model = ContentType.objects.get_for_model

        def _check_efilters(sc_seq):
            if any(sc.efilter_id and not sc.efilter.applicable_on_entity_base for sc in sc_seq):
                raise EntityCredentials.FilteringError(
                    "An EntityFilter (not targeting CremeEntity) is used by a "
                    "{cls} instance so it's not possible to use "
                    "{cls}.filter_entities().".format(cls=cls.__name__)
                )

        if as_model is not None:
            assert issubclass(as_model, CremeEntity)

            narrowed_ct_ids = {None, get_for_model(as_model).id}
            narrowed_sc = [sc for sc in sc_sequence if sc.ctype_id in narrowed_ct_ids]
            _check_efilters(narrowed_sc)

            return cls._aux_filter(
                model=as_model, sc_sequence=narrowed_sc, user=user,
                queryset=queryset, perm=perm,
            )

        # if bin(perm).count('1') > 1:
        if perm.bit_count() > 1:
            raise ValueError(
                'filter_entities() does not (yet) manage permissions '
                'combination when the argument "as_model" is None.',
            )

        all_ct_ids = {
            None,
            *(get_for_model(model).id for model in models),
        }
        sorted_sc = sorted(
            (sc for sc in sc_sequence if sc.ctype_id in all_ct_ids),
            # NB: we sort to get ESET_ALL creds before ESET_OWN/ESET_FILTER ones.
            key=lambda sc: sc.set_type,
        )
        _check_efilters(sorted_sc)

        # NB: some explanations on the algorithm :
        #  we try to regroup ContentTypes (corresponding to CremeEntity sub_classes)
        #  which have the same filtering rules ; so we can generate a Query which looks like
        #    entity_type__in=[...] OR (entity_type__in=[...] AND user__exact=current-user) OR
        #    (entity_type__in=[...] AND field1__startswith='foo')

        OWN_FILTER_ID = 0  # Fake EntityFilter ID corresponding to ESET_OWN.

        ESET_ALL = cls.ESET_ALL
        ESET_OWN = cls.ESET_OWN
        ESET_FILTER = cls.ESET_FILTER

        def _extract_filter_ids(set_creds):
            for sc in set_creds:
                if sc.set_type == ESET_OWN:
                    yield OWN_FILTER_ID
                    break  # Avoid several OWN_FILTER_ID (should not happen)

            for sc in set_creds:
                if sc.set_type == ESET_FILTER:
                    yield sc.efilter_id

        # Map of EntityFilters to apply on ContentTypes groups
        #   key = tuple containing 2 tuples of filter IDs: forbidden rules & allowed ones.
        #   value = list of ContentType IDs.
        #  Note: special values for EntityFilter ID:
        #    None: means ESET_ALL (no filtering)
        #    OWN_FILTER_ID: means ESET_OWN (a virtual EntityFilter on "user" field).
        ctypes_filtering: DefaultDict[tuple, list[int]] = defaultdict(list)

        efilters_per_id = {sc.efilter_id: sc.efilter for sc in sc_sequence}

        for model in models:
            ct_id = get_for_model(model).id
            model_ct_ids = {None, ct_id}   # <None> means <CremeEntity>

            allowed, forbidden = partition(
                lambda sc: sc.forbidden,
                (
                    sc for sc in sorted_sc
                    if sc.ctype_id in model_ct_ids and sc.value & perm
                )
            )

            if allowed:
                if forbidden and forbidden[0].set_type == ESET_ALL:
                    continue

                allowed_filter_ids = (
                    [None]
                    if allowed[0].set_type == ESET_ALL else
                    [*_extract_filter_ids(allowed)]
                )
                forbidden_filter_ids = [*_extract_filter_ids(forbidden)]

                ctypes_filtering[(
                    tuple(forbidden_filter_ids),
                    tuple(allowed_filter_ids),
                )].append(ct_id)

        if not ctypes_filtering:
            queryset = queryset.none()
        else:
            def _user_filtering_q():  # TODO: cached/lazy ?
                teams = user.teams
                return Q(**{'user__in': [user, *teams]} if teams else {'user': user})

            def _efilter_ids_to_Q(efilter_ids):
                filters_q = Q()

                for filter_id in efilter_ids:
                    # TODO: condexpr
                    if filter_id is not None:  # None == ESET_ALL
                        if filter_id == OWN_FILTER_ID:
                            filter_q = _user_filtering_q()
                        else:
                            # TODO: distinct ??
                            filter_q = efilters_per_id[filter_id].get_q(user=user)

                        filters_q |= filter_q

                return filters_q

            q = Q()
            for (forbidden_filter_ids, allowed_filter_ids), ct_ids in ctypes_filtering.items():
                q |= (
                    (
                        Q(entity_type_id=ct_ids[0])
                        if len(ct_ids) == 1 else
                        Q(entity_type_id__in=ct_ids)
                    )
                    & _efilter_ids_to_Q(allowed_filter_ids)
                    & ~_efilter_ids_to_Q(forbidden_filter_ids)
                )

            queryset = queryset.filter(q)

        return queryset

    def save(self, *args, **kwargs):
        ct = self.ctype
        if ct is None:
            model = CremeEntity
        else:
            model = ct.model_class()
            if model is CremeEntity:
                raise ValueError(
                    f'{type(self).__name__}: '
                    f'<ctype> cannot be <CremeEntity> (use <None> instead).'
                )

        if self.set_type == self.ESET_FILTER:
            if not self.efilter_id:
                raise ValueError(
                    f'{type(self).__name__} with <set_type == ESET_FILTER> must have a filter.'
                )

            filter_model = self.efilter.entity_type.model_class()

            if filter_model != model:
                raise ValueError(
                    f'{type(self).__name__} must have a filter related to the '
                    f'same type: {model} != {filter_model}'
                )
        elif self.efilter_id:
            raise ValueError(
                f'Only {type(self).__name__} with <set_type == ESET_FILTER> '
                f'can have a filter.'
            )

        super().save(*args, **kwargs)

    def set_value(self, *,
                  can_view: bool,
                  can_change: bool,
                  can_delete: bool,
                  can_link: bool,
                  can_unlink: bool,
                  ) -> None:
        """Set the 'value' attribute from 5 booleans."""
        value = EntityCredentials.NONE

        if can_view:
            value |= EntityCredentials.VIEW

        if can_change:
            value |= EntityCredentials.CHANGE

        if can_delete:
            value |= EntityCredentials.DELETE

        if can_link:
            value |= EntityCredentials.LINK

        if can_unlink:
            value |= EntityCredentials.UNLINK

        self.value = value


class CremeUserManager(BaseUserManager):
    def create_user(self,
                    username: str,
                    first_name: str,
                    last_name: str,
                    email: str,
                    password: str | None = None,
                    role: UserRole | None = None,
                    roles: Iterable[UserRole] = (),
                    **extra_fields) -> CremeUser:
        """Creates a (Creme)User instance in DB & returns it.

        About 'role' & 'roles': to create a regular user, you just have to set
        at least one of these arguments.
        """
        if not username:
            raise ValueError('The given username must be set')

        roles = [*roles]
        if role:
            roles.append(role)
        elif roles:
            role = roles[0]

        user = self.model(
            username=username,
            first_name=first_name, last_name=last_name,
            email=self.normalize_email(email),
            role=role,
            **extra_fields
        )

        user.set_password(password)
        user.clean()
        user.save()

        if roles:
            user.roles.set(roles)

        return user

    create_user.alters_data = True

    def create_superuser(self,
                         username: str,
                         first_name: str,
                         last_name: str,
                         email: str,
                         password: str | None = None,
                         **extra_fields) -> CremeUser:
        "Creates and saves a superuser."
        extra_fields['is_superuser'] = True

        return self.create_user(
            username=username,
            first_name=first_name, last_name=last_name,
            email=email,
            password=password,
            **extra_fields
        )

    create_superuser.alters_data = True

    # TODO: create_staff_user ??

    def get_admin(self) -> CremeUser:
        user_qs = self.get_queryset().order_by('id')

        return (
            user_qs.filter(is_superuser=True, is_staff=False).first()
            or user_qs.filter(is_superuser=True).first()
            or user_qs[0]
        )

    def get_by_portable_key(self, key: str) -> CremeUser:
        return self.get(uuid=key)


class CremeUser(AbstractBaseUser):
    username_validator = UnicodeUsernameValidator()

    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    # NB: auth.models.AbstractUser.username max_length == 150 (since django 1.10) => increase too ?
    username = models.CharField(
        _('Username'), max_length=30, unique=True,
        help_text=_(
            'Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'
        ),
        validators=[username_validator],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )

    last_name = models.CharField(_('Last name'), max_length=100, blank=True)
    # NB: blank=True for teams
    first_name = models.CharField(_('First name'), max_length=100, blank=True)
    email = models.EmailField(_('Email address'), blank=True)

    displayed_name = models.CharField(
        _('Displayed name'),
        max_length=50, blank=True,
        help_text=_(
            'If you do not fill this field, an automatic name will be used '
            '(«John Doe» will be displayed as «John D.»).'
        ),
    )

    date_joined = models.DateTimeField(_('Date joined'), default=now, editable=False)
    # Not viewable by users, For administrators currently.
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    is_active = models.BooleanField(_('Active?'), default=True)
    deactivated_on = models.DateTimeField(
        _('Deactivated on'), null=True, default=None, editable=False,
    )

    is_staff = models.BooleanField(
        _('Is staff?'), default=False, editable=False,
    ).set_tags(viewable=False)
    is_superuser = models.BooleanField(_('Is a superuser?'), default=False, editable=False)
    role = models.ForeignKey(
        UserRole, verbose_name=_('Role'), null=True, on_delete=models.PROTECT, editable=False,
    )
    roles = models.ManyToManyField(
        UserRole, verbose_name='Possible roles', related_name='+', blank=True,
        help_text=_(
            'A normal user must have at least one role.\n'
            ' - A user with no role will be a SUPERUSER.\n'
            ' - If you choose several roles, the user will be able to switch between them.'
        )
    ).set_tags(viewable=False)

    is_team = models.BooleanField(verbose_name=_('Is a team?'), default=False)
    teammates_set = models.ManyToManyField(
        'self', verbose_name=_('Teammates'), symmetrical=False, related_name='teams_set',
    ).set_tags(viewable=False)

    time_zone = models.CharField(
        _('Time zone'), max_length=50, default=settings.TIME_ZONE,
        # TODO: (note from Python's doc)
        #   These values are not designed to be exposed to end-users; for user
        #   facing elements, applications should use something like CLDR (the
        #   Unicode Common Locale Data Repository) to get more user-friendly strings
        choices=[(tz, tz) for tz in zoneinfo.available_timezones()],
    ).set_tags(viewable=False)
    theme = models.CharField(
        _('Theme'),
        max_length=50, default=settings.THEMES[0][0], choices=settings.THEMES,
    ).set_tags(viewable=False)
    language = models.CharField(
        _('Language'), max_length=10,
        default='', blank=True,
        choices=[('', _('Language of your browser')), *settings.LANGUAGES],
    ).set_tags(viewable=False)

    # NB: do not use directly ; use the property 'settings'
    # TODO: JSONField ?
    json_settings = models.TextField(
        editable=False, default='{}',
    ).set_tags(viewable=False)

    objects = CremeUserManager()

    error_messages = {
        'used_email': _('An active user with the same email address already exists.'),
    }

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    creation_label = _('Create a user')
    save_label     = _('Save the user')

    _settings: UserSettingValueManager | None = None
    _teams: list[CremeUser] | None = None
    _teammates: dict[int, CremeUser] | None = None

    class Meta:
        # abstract = True TODO: class AbstractCremeUser ?
        ordering = ('username',)
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        app_label = 'creme_core'

    def __str__(self):
        return self.get_full_name()

    def clean(self):
        # TODO: split in sub methods?
        # TODO: check is_staff too?
        if self.is_team:
            if self.role_id:
                raise ValidationError('A team cannot have a role.')

            if self.is_superuser:
                raise ValidationError('A team cannot be marked as superuser.')

            if self.last_name:
                raise ValidationError('A team cannot have a last name.')

            if self.first_name:
                raise ValidationError('A team cannot have a first name.')

            if self.displayed_name:
                raise ValidationError('A team cannot have a displayed name.')
        else:
            if self.is_superuser:
                if self.role_id:
                    raise ValidationError('A superuser cannot have a role.')
            elif not self.role_id:
                raise ValidationError('A regular user must have a role.')

            # ---
            email = self.email
            qs = type(self)._default_manager.filter(is_active=True, email=email)

            if self.id:
                qs = qs.exclude(id=self.id)

            if qs.exists():
                raise ValidationError({
                    'email': ValidationError(
                        self.error_messages['used_email'],
                        code='used_email',
                    ),
                })

    def get_full_name(self) -> str:
        if self.is_team:
            return gettext('{user} (team)').format(user=self.username)

        displayed_name = self.displayed_name
        if displayed_name:
            return displayed_name

        # TODO: we could also check related contact to find first_name, last_name
        first_name = self.first_name
        last_name  = self.last_name

        if first_name and last_name:
            return gettext('{first_name} {last_name}.').format(
                first_name=first_name,
                last_name=last_name[0],
            )
        else:
            return self.username

    def get_short_name(self) -> str:
        return self.username

    @property
    def settings(self) -> UserSettingValueManager:
        """Get a manager to read or write extra settings stored in the user instance.

        Example:
            # NB: 'sk' in an instance of <creme_core.core.setting_key.UserSettingKey>

            # Read
            value = my_user.settings.get(sk)

            # Write - we use the manager as a context manager
            with my_user.settings as settings:
                settings[sk] = value
        """
        settings = self._settings

        if settings is None:
            settings = self._settings = UserSettingValueManager(
                user_class=self.__class__,
                user_id=self.id,
                json_settings=self.json_settings,
            )

        return settings

    @property
    def theme_info(self) -> tuple[str, str]:
        THEMES = settings.THEMES
        theme_name = self.theme

        for theme_info in settings.THEMES:
            if theme_name == theme_info[0]:
                return theme_info

        return THEMES[0]

    @property  # NB notice that a cache is built
    def teams(self) -> list[CremeUser]:
        # assert not self.is_team
        if self.is_team:
            raise ValueError('A team cannot belong to another team')

        teams = self._teams
        if teams is None:
            self._teams = teams = [*self.teams_set.all()]

        return teams

    @property  # NB notice that cache and credentials are well updated when using this property
    def teammates(self) -> dict[int, CremeUser]:
        """Dictionary of teammates users
            key: user ID.
            value CremeUser instance.
        """
        # assert self.is_team
        if not self.is_team:
            raise ValueError('Only a team can have teammates')

        teammates = self._teammates

        if teammates is None:
            logger.debug('User.teammates: Cache MISS for user_id=%s', self.id)
            self._teammates = teammates = self.teammates_set.in_bulk()
        else:
            logger.debug('User.teammates: Cache HIT for user_id=%s', self.id)

        return teammates

    @teammates.setter
    def teammates(self, users: Sequence[CremeUser]):
        # assert self.is_team
        if not self.is_team:
            raise ValueError('Only a team can have teammates')

        # assert not any(user.is_team for user in users)
        if any(user.is_team for user in users):
            raise ValueError('A teammate cannot be a team')

        self.teammates_set.set(users)
        self._teammates = None  # Clear cache (we could rebuild it but ...)

    def _get_credentials(self, entity: CremeEntity) -> EntityCredentials:
        creds_map = getattr(entity, '_credentials_map', None)

        if creds_map is None:
            entity._credentials_map = creds_map = {}
            creds = None
        else:
            creds = creds_map.get(self.id)

        if creds is None:
            logger.debug(
                'CremeUser._get_credentials(): Cache MISS for id=%s user=%s',
                entity.id, self,
            )
            creds_map[self.id] = creds = EntityCredentials(self, entity)
        else:
            logger.debug(
                'CremeUser._get_credentials(): Cache HIT for id=%s user=%s',
                entity.id, self,
            )

        return creds

    def has_perm(self, perm: str, obj=None) -> bool:
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """
        # Check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perm_or_die(self, perm: str, obj=None) -> None:
        """Version of 'has_perm()' which raises <PermissionDenied> instead of
        returning <False>.
        Notice: the backend should forge human-friendly messages (it's the case of
        the default backend).
        @raise PermissionDenied.
        """
        for backend in get_backends():
            if not hasattr(backend, 'has_perm'):
                continue

            # Can raise PermissionDenied
            if backend.has_perm(self, perm, obj):
                return

        # TODO: unit test
        raise PermissionDenied(gettext('Forbidden (unspecified reason)'))

    def has_perms(self, perm_list: str | Iterable[str], obj=None) -> bool:
        """Helper for has_perm() when you need to check several permission
        strings.
        """
        if not perm_list:
            return True

        has_perm = self.has_perm

        return (
            has_perm(perm_list, obj)
            if isinstance(perm_list, str) else
            all(has_perm(perm, obj) for perm in perm_list)
        )

    def has_perms_or_die(self, perm_list: str | Iterable[str], obj=None) -> None:
        """Version of 'has_perms()' which raises <PermissionDenied> instead of
        returning <False>.
        @raise PermissionDenied.
        """
        if perm_list:
            if isinstance(perm_list, str):
                self.has_perm_or_die(perm_list, obj)
            else:
                for perm in perm_list:
                    self.has_perm_or_die(perm, obj)

    def has_special_perm(self, perm: SpecialPermission, /) -> bool:
        if self.is_superuser:
            return True

        role = self.role
        return role.deactivated_on is None and perm.id in role.special_permissions

    def has_special_perm_or_die(self, perm: SpecialPermission, /) -> None:
        if not self.has_special_perm(perm):
            raise PermissionDenied(
                gettext('You have not this special permission: «{}»').format(
                    perm.verbose_name
                )
            )

    def has_perm_to_access(self, app_label: str, /) -> bool:
        return self.is_superuser or self.role.is_app_allowed_or_administrable(app_label)

    @staticmethod  # TODO: move in utils ?
    def _get_app_verbose_name(app_label: str) -> str:
        try:
            return apps.get_app_config(app_label).verbose_name
        except LookupError:
            return gettext('Invalid app "{}"').format(app_label)

    def has_perm_to_access_or_die(self, app_label: str, /) -> None:
        if not self.has_perm_to_access(app_label):
            raise PermissionDenied(
                gettext('You are not allowed to access to the app: {}').format(
                    self._get_app_verbose_name(app_label),
                )
            )

    def has_perm_to_admin(self, app_label: str, /) -> bool:
        return self.is_superuser or self.role.is_app_administrable(app_label)

    def has_perm_to_admin_or_die(self, app_label: str, /) -> None:
        if not self.has_perm_to_admin(app_label):
            raise PermissionDenied(
                gettext('You are not allowed to configure this app: {}').format(
                    self._get_app_verbose_name(app_label),
                )
            )

    def _get_related_entity(self, instance: CremeModel) -> CremeEntity:
        try:
            get_related_entity = instance.get_related_entity
        except AttributeError as e:
            raise TypeError(
                'The permission system need an instance of CremeEntity or a '
                'model with a method <get_related_entity()>'
            ) from e

        entity = get_related_entity()

        if not isinstance(entity, CremeEntity):
            # TODO: unit test
            raise TypeError(
                f'The get_related_entity() of "{instance}" MUST return a CremeEntity instance'
            )

        if hasattr(entity, 'get_related_entity'):
            # TODO: unit test
            raise TypeError(
                f'The get_related_entity() of "{instance}" MUST return a '
                f'CremeEntity instance without method <get_related_entity()>'
            )

        return entity

    def _get_main_entity(self, instance: CremeModel) -> CremeEntity:
        if isinstance(instance, CremeEntity):
            return (
                self._get_related_entity(instance.get_real_entity())
                if hasattr(instance.entity_type.model_class(), 'get_related_entity')
                else instance
            )
        else:
            return self._get_related_entity(instance)

    # TODO: change argument name ("instance")
    def has_perm_to_change(self, entity: CremeModel) -> bool:
        """Has a user the permission to modify an instance.
        @param entity: An instance of CremeEntity, or an auxiliary instance
               (i.e. with a method get_related_entity()).
        """
        main_entity = self._get_main_entity(entity)

        # TODO: move to UserRole? improve UserRole.filter() too?
        ce_type = CustomEntityType.objects.get_for_model(type(main_entity))
        if ce_type and ce_type.deleted:
            return False

        return False if main_entity.is_deleted else self._get_credentials(main_entity).can_change()

    def has_perm_to_change_or_die(self, entity: CremeModel) -> None:
        if not self.has_perm_to_change(entity):
            raise PermissionDenied(
                gettext('You are not allowed to edit this entity: {}').format(
                    self._get_main_entity(entity).allowed_str(self),
                )
            )

    def has_perm_to_create(self,
                           ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                           /) -> bool:
        """Is the user allowed to create instances of a model?
        >> user.has_perm_to_create(ContentType.objects.get_for_model(Contact))

        >> user.has_perm_to_create(Contact)

        >> contact = Contact.objects.create(user=user, last_name='Doe')
        >> user.has_perm_to_create(contact)
        """
        # TODO: check is a CremeEntity? (as_entity_model()?)
        ce_type = CustomEntityType.objects.get_for_model(as_model(ct_or_model_or_entity))
        if ce_type and (not ce_type.enabled or ce_type.deleted):
            return False

        if self.is_superuser:
            return True

        return self.role.can_create(as_ctype(ct_or_model_or_entity))

    def has_perm_to_create_or_die(self,
                                  ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                                  /) -> None:
        if not self.has_perm_to_create(ct_or_model_or_entity):
            raise PermissionDenied(
                gettext('You are not allowed to create: {}').format(
                    model_verbose_name(as_model(ct_or_model_or_entity))
                )
            )

    # TODO: rename argument (see <has_perm_to_change()>)
    def has_perm_to_delete(self, entity: CremeModel) -> bool:
        """Has a user the permission to delete an instance.
        @param entity: An instance of CremeEntity, or an auxiliary instance
               (i.e. with a method get_related_entity()).
        """
        if not isinstance(entity, CremeEntity):
            return self._get_credentials(self._get_related_entity(entity)).can_change()

        if hasattr(entity.entity_type.model_class(), 'get_related_entity'):
            return self._get_credentials(
                self._get_related_entity(entity.get_real_entity()),
            ).can_change()

        return self._get_credentials(entity).can_delete()

    def has_perm_to_delete_or_die(self, entity: CremeModel) -> None:
        if not self.has_perm_to_delete(entity):
            raise PermissionDenied(
                gettext('You are not allowed to delete this entity: {}').format(
                    self._get_main_entity(entity).allowed_str(self),
                )
            )

    # TODO: factorise with has_perm_to_create() ??
    def has_perm_to_export(self,
                           ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                           /) -> bool:
        """Is the user allowed to mass-export the instances of a model?
        >> user.has_perm_to_export(ContentType.objects.get_for_model(Contact))

        >> user.has_perm_to_export(Contact)

        >> contact = Contact.objects.create(user=user, last_name='Doe')
        >> user.has_perm_to_export(contact)
        """
        # TODO: check is a CremeEntity?
        return self.is_superuser or self.role.can_export(as_ctype(ct_or_model_or_entity))

    def has_perm_to_export_or_die(self,
                                  ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                                  /) -> None:
        if not self.has_perm_to_export(ct_or_model_or_entity):
            meta = (
                ct_or_model_or_entity.model_class()._meta
                if isinstance(ct_or_model_or_entity, ContentType) else
                ct_or_model_or_entity._meta
            )

            raise PermissionDenied(
                gettext('You are not allowed to export: {}').format(meta.verbose_name)
            )

    def has_perm_to_link(self,
                         ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                         /,
                         owner: CremeUser | None = None,
                         ) -> bool:
        """Can the user link a future entity of a given class ?
        @param entity_or_model: {Instance of} class inheriting CremeEntity.
        @param owner: (only used when 1rst param is a class) Instance of CremeUser;
                      owner of the (future) entity. 'None' means: is there an
                      owner (at least) that allows linking.
        """
        assert not self.is_team  # Teams can not be logged, it has no sense

        # TODO: move to UserRole? improve UserRole.filter() too?
        model = as_model(ct_or_model_or_entity)
        ce_type = CustomEntityType.objects.get_for_model(model)
        if ce_type and ce_type.deleted:
            return False

        if isinstance(ct_or_model_or_entity, CremeEntity):
            # TODO: what about related_entity ?
            return (
                False if ct_or_model_or_entity.is_deleted else
                self._get_credentials(ct_or_model_or_entity).can_link()
            )

        assert issubclass(model, CremeEntity)

        return True if self.is_superuser else self.role.can_do_on_model(
            user=self, model=model, owner=owner, perm=EntityCredentials.LINK,
        )

    # TODO: factorise ??
    def has_perm_to_link_or_die(self,
                                ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                                /,
                                owner: CremeUser | None = None,
                                ) -> None:
        if not self.has_perm_to_link(ct_or_model_or_entity, owner):
            raise PermissionDenied(
                gettext('You are not allowed to link this entity: {}').format(
                    ct_or_model_or_entity.allowed_str(user=self)
                )
                if isinstance(ct_or_model_or_entity, CremeEntity) else
                gettext('You are not allowed to link: {}').format(
                    model_verbose_name(as_model(ct_or_model_or_entity))
                )
            )

    def has_perm_to_unlink(self, entity: CremeEntity) -> bool:
        # TODO: what about related_entity ?
        return self._get_credentials(entity).can_unlink()

    def has_perm_to_unlink_or_die(self, entity: CremeEntity) -> None:
        if not self.has_perm_to_unlink(entity):
            raise PermissionDenied(
                gettext('You are not allowed to unlink this entity: {}').format(
                    entity.allowed_str(self),
                )
            )

    # TODO: factorise?
    def has_perm_to_list(self,
                         ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                         /) -> bool:
        """Is the user allowed to access the list-views of a model?
        NB: is concerns page-wide list-views & inner-popup list (used to
            select entities in forms).

        >> user.has_perm_to_list(ContentType.objects.get_for_model(Contact))

        >> user.has_perm_to_list(Contact)

        >> contact = Contact.objects.create(user=user, last_name='Doe')
        >> user.has_perm_to_list(contact)
        """
        # TODO: check is a CremeEntity?
        return self.is_superuser or self.role.can_list(as_ctype(ct_or_model_or_entity))

    def has_perm_to_list_or_die(self,
                                ct_or_model_or_entity: EntityInstanceOrClassOrCType,
                                /) -> None:
        if not self.has_perm_to_list(ct_or_model_or_entity):
            meta = (
                ct_or_model_or_entity.model_class()._meta
                if isinstance(ct_or_model_or_entity, ContentType) else
                ct_or_model_or_entity._meta
            )

            raise PermissionDenied(
                gettext('You are not allowed to list: {}').format(meta.verbose_name)
            )

    # TODO: rename argument (see <has_perm_to_change()>)
    def has_perm_to_view(self, entity: CremeModel) -> bool:
        """Has a user the permission to view an instance.
        @param entity: An instance of CremeEntity, or an auxiliary instance
               (i.e. with a method get_related_entity()).
        """
        return self._get_credentials(self._get_main_entity(entity)).can_view()

    def has_perm_to_view_or_die(self, entity: CremeModel) -> None:
        if not self.has_perm_to_view(entity):
            raise PermissionDenied(
                gettext('You are not allowed to view this entity: {}').format(
                    self._get_main_entity(entity).allowed_str(self),
                )
            )

    def normalize_roles(self) -> None:
        """Fix pool of roles which does not contain the current role.
        (internal use).
        Hint: prefetch 'roles' to avoid queries
        """
        role = self.role
        if role and role not in self.roles.all():
            self.roles.add(role)
            logger.warning(
                'The possible roles of the user "%s" did not contain '
                'its current job (user has been fixed).', self.username,
            )

    def portable_key(self) -> str:
        return str(self.uuid)


CremeUser._meta.get_field('password').set_tags(viewable=False)


class Sandbox(models.Model):
    """When a CremeEntity is associated to a sandbox, only the user related to this sandbox
    can have its regular permission on this entity.
    A Sandbox can be related to a UserRole ; in these case all users with this
    role can access to this entity.

    Notice that superusers ignore the Sandboxes ; so if a SandBox has no related
    user/role, the entities in this sandbox are only accessible to the superusers
    (like the Sandbox built in creme_core.populate.py)
    """
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    type_id = models.CharField('Type of sandbox', max_length=48, editable=False)
    role = models.ForeignKey(
        UserRole, verbose_name='Related role', null=True,
        default=None, on_delete=models.CASCADE, editable=False,
    )
    # superuser = BooleanField('related to superusers', default=False, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Related user',
        null=True, default=None, on_delete=models.CASCADE, editable=False,
    )

    class Meta:
        app_label = 'creme_core'

    @property
    def type(self) -> SandboxType | None:
        # TODO: pass registry as argument
        from ..core.sandbox import sandbox_type_registry

        return sandbox_type_registry.get(self)

    @type.setter
    def type(self, value: SandboxType):
        self.type_id = value.id
