# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
import uuid
from collections import OrderedDict, defaultdict
from functools import reduce
from operator import or_ as or_op
# from re import compile as re_compile
from typing import (
    TYPE_CHECKING,
    DefaultDict,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

import pytz
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    _user_has_perm,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
# from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..auth import EntityCredentials
from ..core.setting_key import UserSettingValueManager
from ..utils import split_filter
from ..utils.unicode_collation import collator
from .entity import CremeEntity
from .fields import EntityCTypeForeignKey  # CTypeForeignKey

if TYPE_CHECKING:
    from ..core.sandbox import SandboxType

logger = logging.getLogger(__name__)


class UserRole(models.Model):
    name = models.CharField(_('Name'), max_length=100, unique=True)
    # superior = ForeignKey('self', verbose_name=_('Superior'), null=True)
    # TODO: CTypeManyToManyField ?
    creatable_ctypes = models.ManyToManyField(
        ContentType, verbose_name=_('Creatable resources'),
        related_name='roles_allowing_creation',  # TODO: '+' ?
    )
    exportable_ctypes = models.ManyToManyField(
        ContentType, verbose_name=_('Exportable resources'),
        related_name='roles_allowing_export',  # TODO: '+' ?
    )
    raw_allowed_apps = models.TextField(default='')  # Use 'allowed_apps' property
    raw_admin_4_apps = models.TextField(default='')  # Use 'admin_4_apps' property

    creation_label = _('Create a role')
    save_label     = _('Save the role')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_apps: Optional[Set[str]] = None
        self._extended_allowed_apps: Optional[Set[str]] = None

        self._admin_4_apps: Optional[Set[str]] = None
        self._extended_admin_4_apps: Optional[Set[str]] = None

        self._creatable_ctypes_set: Optional[FrozenSet[int]] = None
        self._exportable_ctypes_set: Optional[FrozenSet[int]] = None

        self._setcredentials: Optional[List[SetCredentials]] = None

    def __str__(self):
        return self.name

    @property
    def admin_4_apps(self) -> Set[str]:
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
    def allowed_apps(self) -> Set[str]:
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

    def _build_extended_apps(self, apps: Iterable[str]) -> Set[str]:
        from ..apps import extended_app_configs

        return {app_config.label for app_config in extended_app_configs(apps)}

    @property
    def extended_admin_4_apps(self) -> Set[str]:
        if self._extended_admin_4_apps is None:
            self._extended_admin_4_apps = self._build_extended_apps(self.admin_4_apps)

        return self._extended_admin_4_apps

    @property
    def extended_allowed_apps(self) -> Set[str]:
        if self._extended_allowed_apps is None:
            self._extended_allowed_apps = self._build_extended_apps(self.allowed_apps)

        return self._extended_allowed_apps

    def is_app_administrable(self, app_name: str) -> bool:  # TODO: rename "app_label"
        return app_name in self.extended_admin_4_apps

    # TODO: rename "app_label"
    def is_app_allowed_or_administrable(self, app_name: str) -> bool:
        return (app_name in self.extended_allowed_apps) or self.is_app_administrable(app_name)

    # TODO: rename app_labels
    def _build_apps_verbose(self, app_names: Iterable[str]) -> List[str]:
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

    def get_admin_4_apps_verbose(self) -> List[str]:  # For templates
        return self._build_apps_verbose(self.admin_4_apps)

    def get_allowed_apps_verbose(self) -> List[str]:  # For templates
        return self._build_apps_verbose(self.allowed_apps)

    def can_create(self, app_name: str, model_name: str) -> bool:
        """@return True if a model with ContentType(app_name, model_name) can be created."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._creatable_ctypes_set is None:
            self._creatable_ctypes_set = frozenset(
                self.creatable_ctypes.values_list('id', flat=True)
            )

        return ct.id in self._creatable_ctypes_set

    # TODO: factorise with can_create() ??
    def can_export(self, app_name: str, model_name: str) -> bool:
        """@return True if a model with ContentType(app_name, model_name) can be exported."""
        ct = ContentType.objects.get_by_natural_key(app_name, model_name)

        if self._exportable_ctypes_set is None:
            self._exportable_ctypes_set = frozenset(
                self.exportable_ctypes.values_list('id', flat=True)
            )

        return ct.id in self._exportable_ctypes_set

    def can_do_on_model(self, user, model: 'CremeEntity', owner, perm: int) -> bool:
        """Can the given user execute an action (VIEW, CHANGE etc..) on this model.
        @param user: User instance ; user that try to do something.
        @param model: Class inheriting CremeEntity
        @param owner: User instance ; owner of the not-yet-existing instance of 'model'
                      None means any user that would allows the action (if it exists of course).
        @param perm: See EntityCredentials.{VIEW, CHANGE, ...}
        """
        return SetCredentials._can_do(self._get_setcredentials(), user, model, owner, perm)

    def _get_setcredentials(self) -> List['SetCredentials']:
        setcredentials = self._setcredentials

        if setcredentials is None:
            logger.debug('UserRole.get_credentials(): Cache MISS for id=%s', self.id)
            self._setcredentials = setcredentials = [*self.credentials.all()]
        else:
            logger.debug('UserRole.get_credentials(): Cache HIT for id=%s', self.id)

        return setcredentials

    def get_perms(self, user, entity: 'CremeEntity') -> int:
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

        @param user: A <django.contrib.auth.get_user_model()> instance (eg: CremeUser) ;
                     should be related to the UserRole instance.
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
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
                        as_model: Optional[Type['CremeEntity']] = None,
                        ) -> QuerySet:
        """Filter a QuerySet of CremeEntities by the credentials related to this role.
        Beware, model class must be CremeEntity ; it cannot be a child class
        of CremeEntity.

        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser) ;
                     should be related to the UserRole instance.
        @param queryset: A Queryset with model=CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @param as_model: A model inheriting CremeEntity, or None.
               If a model is given, all the entities in the queryset are
               filtered with the credentials for this model.
               BEWARE: you should probably use this feature only if the queryset
               if already filtered by its field 'entity_type' (to keep only
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
    ctype = EntityCTypeForeignKey(
        verbose_name=_('Apply to a specific type'),
        # NB: NULL means "No specific type" (ie: any kind of CremeEntity)
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
            # 'set':   self.ESETS_MAP.get(self.set_type, '??'),
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

    def _get_perms(self, user, entity: 'CremeEntity') -> int:
        """@return An integer with binary flags for permissions."""
        ctype_id = self.ctype_id

        if not ctype_id or ctype_id == entity.entity_type_id:
            set_type = self.set_type

            if set_type == SetCredentials.ESET_ALL:
                return self.value
            elif set_type == SetCredentials.ESET_OWN:
                user_id = entity.user_id
                if user.id == user_id or any(user_id == t.id for t in user.teams):
                    return self.value
            else:  # SetCredentials.ESET_FILTER
                if self.efilter.accept(entity=entity.get_real_entity(), user=user):
                    return self.value

        return EntityCredentials.NONE

    @staticmethod
    def get_perms(sc_sequence: Sequence['SetCredentials'],
                  user,
                  entity: 'CremeEntity',
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
                sc_sequence: Sequence['SetCredentials'],
                user,
                model: Type['CremeEntity'],
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
                    model: Type['CremeEntity'],
                    sc_sequence: Sequence['SetCredentials'],
                    user,
                    queryset: QuerySet,
                    perm: int,
                    ) -> QuerySet:
        allowed_ctype_ids = {None, ContentType.objects.get_for_model(model).id}
        ESET_ALL = cls.ESET_ALL
        ESET_OWN = cls.ESET_OWN

        forbidden, allowed = split_filter(
            lambda sc: sc.forbidden,
            sorted(
                (
                    sc
                    for sc in sc_sequence
                    if sc.ctype_id in allowed_ctype_ids and sc.value & perm
                ),
                # NB: we sort to get ESET_ALL creds before ESET_OWN ones, then ESET_FILTER ones.
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

        filtered_qs = queryset

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
               sc_sequence: Sequence['SetCredentials'],
               user,
               queryset: QuerySet,
               perm: int,
               ) -> QuerySet:
        """Filter a queryset of entities with the given credentials.
        Beware, the model class must be a child class of CremeEntity,
        but cannot be CremeEntity itself.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A <django.contrib.auth.get_user_model()> instance (eg: CremeUser).
        @param queryset: A Queryset on a child class of CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
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
                        sc_sequence: Sequence['SetCredentials'],
                        user,
                        queryset: QuerySet,
                        perm: int,
                        models: Iterable[Type['CremeEntity']],
                        as_model=None,
                        ) -> QuerySet:
        """Filter a queryset of entities with the given credentials.
        Beware, model class must be CremeEntity ; it cannot be a child class
        of CremeEntity.

        @param sc_sequence: A sequence of SetCredentials instances.
        @param user: A django.contrib.auth.get_user_model() instance (eg: CremeUser).e.
        @param queryset: Queryset with model=CremeEntity.
        @param perm: A value in (EntityCredentials.VIEW, EntityCredentials.CHANGE etc...).
        @param models: An iterable of CremeEntity-child-classes, corresponding
               to allowed models.
        @param as_model: A model inheriting CremeEntity, or None. If a model is
               given, all the entities in the queryset are filtered with the
               credentials for this model.
               BEWARE: you should probably use this feature only if the queryset
               if already filtered by its field 'entity_type' (to keep only
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
        ctypes_filtering: DefaultDict[tuple, List[int]] = defaultdict(list)

        efilters_per_id = {sc.efilter_id: sc.efilter for sc in sc_sequence}

        for model in models:
            ct_id = get_for_model(model).id
            model_ct_ids = {None, ct_id}   # <None> means <CremeEntity>

            forbidden, allowed = split_filter(
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
                    username,
                    first_name,
                    last_name,
                    email,
                    password=None,
                    **extra_fields):
        "Creates and saves a (Creme)User instance."
        if not username:
            raise ValueError('The given username must be set')

        user = self.model(
            username=username,
            first_name=first_name, last_name=last_name,
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.save()

        return user

    def create_superuser(self,
                         username,
                         first_name,
                         last_name,
                         email,
                         password=None,
                         **extra_fields):
        "Creates and saves a superuser."
        extra_fields['is_superuser'] = True

        return self.create_user(
            username=username,
            first_name=first_name, last_name=last_name,
            email=email,
            password=password,
            **extra_fields
        )

    # TODO: create_staff_user ??

    def get_admin(self):
        user_qs = self.get_queryset().order_by('id')

        return (
            user_qs.filter(is_superuser=True, is_staff=False).first()
            or user_qs.filter(is_superuser=True).first()
            or user_qs[0]
        )


_EntityInstanceOrClass = Union[Type['CremeEntity'], 'CremeEntity']


class CremeUser(AbstractBaseUser):
    username_validator = UnicodeUsernameValidator()

    # NB: auth.models.AbstractUser.username max_length == 150 (since django 1.10) => increase too ?
    username = models.CharField(
        _('Username'), max_length=30, unique=True,
        help_text=_(
            'Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'
        ),
        validators=[
            # RegexValidator(
            #     re_compile(r'^[\w.@+-]+$'),
            #     _(
            #         'Enter a valid username. '
            #         'This value may contain only letters, numbers, '
            #         'and @/./+/-/_ characters.'
            #     ),
            #     'invalid',
            # ),
            username_validator,
        ],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )

    last_name = models.CharField(_('Last name'), max_length=100, blank=True)
    first_name = models.CharField(
        _('First name'), max_length=100, blank=True,
    ).set_tags(viewable=False)  # NB: blank=True for teams
    email = models.EmailField(_('Email address'), blank=True)

    date_joined = models.DateTimeField(
        _('Date joined'), default=now,
    ).set_tags(viewable=False)

    is_active = models.BooleanField(
        _('Active?'), default=True,
    ).set_tags(viewable=False)

    is_staff = models.BooleanField(
        _('Is staff?'), default=False
    ).set_tags(viewable=False)
    is_superuser = models.BooleanField(
        _('Is a superuser?'), default=False,
    ).set_tags(viewable=False)
    role = models.ForeignKey(
        UserRole, verbose_name=_('Role'), null=True, on_delete=models.PROTECT,
    ).set_tags(viewable=False)

    is_team = models.BooleanField(
        verbose_name=_('Is a team?'), default=False,
    ).set_tags(viewable=False)
    teammates_set = models.ManyToManyField(
        'self', verbose_name=_('Teammates'), symmetrical=False, related_name='teams_set',
    ).set_tags(viewable=False)

    time_zone = models.CharField(
        _('Time zone'), max_length=50, default=settings.TIME_ZONE,
        choices=[(tz, tz) for tz in pytz.common_timezones],
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
        editable=False, default='{}'
    ).set_tags(viewable=False)

    objects = CremeUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    creation_label = _('Create a user')
    save_label     = _('Save the user')

    _settings: Optional[UserSettingValueManager] = None
    _teams: Optional[List['CremeUser']] = None
    _teammates: Optional[Dict[int, 'CremeUser']] = None

    class Meta:
        # abstract = True TODO: class AbstractCremeUser ?
        ordering = ('username',)
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        app_label = 'creme_core'

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self) -> str:
        if self.is_team:
            return gettext('{user} (team)').format(user=self.username)

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

    # TODO: def clean() ?? (team + role= None etc...)

    @property
    def settings(self) -> UserSettingValueManager:
        """Get a manager to read or write extra settings stored in the user instance.

        eg:
            # NB sk in an instance of <creme_core.core.setting_key.UserSettingKey>

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
    def theme_info(self) -> Tuple[str, str]:
        THEMES = settings.THEMES
        theme_name = self.theme

        for theme_info in settings.THEMES:
            if theme_name == theme_info[0]:
                return theme_info

        return THEMES[0]

    @property  # NB notice that a cache is built
    def teams(self) -> List['CremeUser']:
        assert not self.is_team

        teams = self._teams
        if teams is None:
            self._teams = teams = [*self.teams_set.all()]

        return teams

    @property  # NB notice that cache and credentials are well updated when using this property
    def teammates(self) -> Dict[int, 'CremeUser']:
        """Dictionary of teammates users
            key: user ID.
            value CremeUser instance.
        """
        assert self.is_team

        teammates = self._teammates

        if teammates is None:
            logger.debug('User.teammates: Cache MISS for user_id=%s', self.id)
            self._teammates = teammates = self.teammates_set.in_bulk()
        else:
            logger.debug('User.teammates: Cache HIT for user_id=%s', self.id)

        return teammates

    @teammates.setter
    def teammates(self, users: Sequence['CremeUser']):
        assert self.is_team
        assert not any(user.is_team for user in users)

        self.teammates_set.set(users)
        self._teammates = None  # Clear cache (we could rebuild it but ...)

    def _get_credentials(self, entity: 'CremeEntity') -> EntityCredentials:
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

    # Copied from auth.models.PermissionsMixin.has_perm
    def has_perm(self, perm: str, obj=None) -> bool:
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """
        # if self.is_active and self.is_superuser:
        #     return True

        # Check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list: Iterable[str], obj=None) -> bool:
        has_perm = self.has_perm

        return all(has_perm(perm, obj) for perm in perm_list)

    def has_perm_to_access(self, app_name: str) -> bool:  # TODO: rename "app_label"
        return self.is_superuser or self.role.is_app_allowed_or_administrable(app_name)

    @staticmethod  # TODO: move in utils ?
    def _get_app_verbose_name(app_label: str) -> str:
        try:
            return apps.get_app_config(app_label).verbose_name
        except LookupError:
            return gettext('Invalid app "{}"').format(app_label)

    def has_perm_to_access_or_die(self, app_label: str) -> None:
        if not self.has_perm_to_access(app_label):
            raise PermissionDenied(
                gettext('You are not allowed to access to the app: {}').format(
                    self._get_app_verbose_name(app_label),
                )
            )

    # TODO: rename "app_label"
    def has_perm_to_admin(self, app_name: str) -> bool:
        return self.is_superuser or self.role.is_app_administrable(app_name)

    # TODO: rename 'app_label'
    def has_perm_to_admin_or_die(self, app_name: str) -> None:
        if not self.has_perm_to_admin(app_name):
            raise PermissionDenied(
                gettext('You are not allowed to configure this app: {}').format(
                    self._get_app_verbose_name(app_name),
                )
            )

    def has_perm_to_change(self, entity: 'CremeEntity') -> bool:
        if entity.is_deleted:
            return False

        main_entity = (
            entity.get_real_entity().get_related_entity()
            if hasattr(entity.entity_type.model_class(), 'get_related_entity')
            else entity
        )

        return self._get_credentials(main_entity).can_change()

    def has_perm_to_change_or_die(self, entity: 'CremeEntity') -> None:
        if not self.has_perm_to_change(entity):
            raise PermissionDenied(
                gettext('You are not allowed to edit this entity: {}').format(
                    entity.allowed_str(self),
                )
            )

    def has_perm_to_create(self, model_or_entity: _EntityInstanceOrClass) -> bool:
        """Helper for has_perm() method.
        eg: user.has_perm('myapp.add_mymodel') => user.has_perm_to_create(MyModel)
        """
        meta = model_or_entity._meta
        return self.has_perm(f'{meta.app_label}.add_{meta.object_name.lower()}')

    def has_perm_to_create_or_die(self, model_or_entity: _EntityInstanceOrClass) -> None:
        if not self.has_perm_to_create(model_or_entity):
            raise PermissionDenied(
                gettext('You are not allowed to create: {}').format(
                    model_or_entity._meta.verbose_name,
                )
            )

    def has_perm_to_delete(self, entity: 'CremeEntity') -> bool:
        if hasattr(entity.entity_type.model_class(), 'get_related_entity'):  # TODO: factorise
            return self._get_credentials(
                entity.get_real_entity().get_related_entity(),
            ).can_change()

        return self._get_credentials(entity).can_delete()

    def has_perm_to_delete_or_die(self, entity: 'CremeEntity') -> None:
        if not self.has_perm_to_delete(entity):
            raise PermissionDenied(
                gettext('You are not allowed to delete this entity: {}').format(
                    entity.allowed_str(self),
                )
            )

    # TODO: factorise with has_perm_to_create() ??
    def has_perm_to_export(self, model_or_entity: _EntityInstanceOrClass) -> bool:
        """Helper for has_perm() method.
        eg: user.has_perm('myapp.export_mymodel') => user.has_perm_to_export(MyModel)
        """
        meta = model_or_entity._meta
        return self.has_perm(f'{meta.app_label}.export_{meta.object_name.lower()}')

    def has_perm_to_export_or_die(self,
                                  model_or_entity: Union[Type['CremeEntity'], 'CremeEntity'],
                                  ) -> None:
        if not self.has_perm_to_export(model_or_entity):
            raise PermissionDenied(
                gettext('You are not allowed to export: {}').format(
                    model_or_entity._meta.verbose_name
                )
            )

    def has_perm_to_link(self,
                         entity_or_model: _EntityInstanceOrClass,
                         owner: Optional['CremeUser'] = None,
                         ) -> bool:
        """Can the user link a future entity of a given class ?
        @param entity_or_model: {Instance of} class inheriting CremeEntity.
        @param owner: (only used when 1rst param is a class) Instance of CremeUser ;
                      owner of the (future) entity. 'None' means: is there an
                      owner (at least) that allows linking.
        """
        assert not self.is_team  # Teams can not be logged, it has no sense

        if isinstance(entity_or_model, CremeEntity):
            # TODO: what about related_entity ?
            return (
                False if entity_or_model.is_deleted else
                self._get_credentials(entity_or_model).can_link()
            )

        assert issubclass(entity_or_model, CremeEntity)

        return (
            True if self.is_superuser else
            self.role.can_do_on_model(self, entity_or_model, owner, EntityCredentials.LINK)
        )

    # TODO: factorise ??
    def has_perm_to_link_or_die(self,
                                entity_or_model: _EntityInstanceOrClass,
                                owner: Optional['CremeUser'] = None,
                                ) -> None:
        if not self.has_perm_to_link(entity_or_model, owner):
            if isinstance(entity_or_model, CremeEntity):
                msg = gettext('You are not allowed to link this entity: {}').format(
                    entity_or_model.allowed_str(self)
                )
            else:
                msg = gettext('You are not allowed to link: {}').format(
                    entity_or_model._meta.verbose_name
                )

            raise PermissionDenied(msg)

    def has_perm_to_unlink(self, entity: 'CremeEntity') -> bool:
        # TODO: what about related_entity ?
        return self._get_credentials(entity).can_unlink()

    def has_perm_to_unlink_or_die(self, entity: 'CremeEntity') -> None:
        if not self.has_perm_to_unlink(entity):
            raise PermissionDenied(
                gettext('You are not allowed to unlink this entity: {}').format(
                    entity.allowed_str(self),
                )
            )

    def has_perm_to_view(self, entity: 'CremeEntity') -> bool:
        # TODO: what about related_entity ?
        return self._get_credentials(entity).can_view()

    def has_perm_to_view_or_die(self, entity: 'CremeEntity') -> None:
        if not self.has_perm_to_view(entity):
            raise PermissionDenied(
                gettext('You are not allowed to view this entity: {}').format(
                    entity.allowed_str(self),
                )
            )


get_user_field = CremeUser._meta.get_field
for fname in ('password', 'last_login'):
    get_user_field(fname).set_tags(viewable=False)

del get_user_field


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
    def type(self) -> Optional['SandboxType']:
        # TODO: pass registry as argument
        from ..core.sandbox import sandbox_type_registry

        return sandbox_type_registry.get(self)
