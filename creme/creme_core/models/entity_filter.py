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
# import warnings
from itertools import zip_longest
from json import loads as json_load
from re import compile as compile_re
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext, pgettext_lazy

from ..core.entity_filter import (
    EF_USER,
    _EntityFilterRegistry,
    entity_filter_registries,
)
from ..global_info import get_global_info
from ..utils import update_model_instance
from ..utils.serializers import json_encode
from . import CremeEntity
from . import fields as core_fields

if TYPE_CHECKING:
    from creme.creme_core.core.entity_filter.condition_handler import (
        FilterConditionHandler,
    )

logger = logging.getLogger(__name__)


# TODO: move to core.entity_filter ? (what about HeaderFilterList ?)
class EntityFilterList(list):
    """Contains all the EntityFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's as a cache.
    """
    def __init__(self, content_type: ContentType, user):
        super().__init__(
            EntityFilter.objects.filter_by_user(user).filter(entity_type=content_type)
        )
        self._selected: Optional['EntityFilter'] = None

    @property
    def selected(self) -> Optional['EntityFilter']:
        return self._selected

    def select_by_id(self, *ids: str) -> Optional['EntityFilter']:
        """Try several EntityFilter ids."""
        # Linear search but with few items after all...
        for efilter_id in ids:
            for efilter in self:
                if efilter.id == efilter_id:
                    self._selected = efilter
                    return efilter

        return self._selected


class EntityFilterManager(models.Manager):
    def get_latest_version(self, base_pk: str) -> 'EntityFilter':
        """Get the latest EntityFilter from the family which uses the 'base_pk'.
        @raises EntityFilter.DoesNotExist If there is none instance in this family
        """
        efilters = [*self.filter(Q(pk=base_pk) | Q(pk__startswith=base_pk + '['))]

        if not efilters:
            raise self.model.DoesNotExist(f'No EntityFilter with pk="{base_pk}"')

        VERSION_RE = compile_re(
            r'([\w,-]+)(\[(?P<version_num>\d[\d\.]+)'
            r'(([ ,-]+)(?P<version_mod>alpha|beta|rc)'
            r'(?P<version_modnum>\d+)?)?\](?P<copy_num>\d+)?)?$'
        )

        def key(efilter):
            # We build a tuple which can easily compared with the other generated tuples.
            # Example of PKs: 'base_pk' 'base_pk[1.15]' 'base_pk[1.15 alpha]'
            #                 'base_pk[1.15 rc]' 'base_pk[1.15 rc11]' 'base_pk[1.15 rc11]2'
            # eg: 'base_pk[1.15 rc11]2'
            #   ==> we extract '1.15', 'aplha', '11' & '2' and build ((1, 15), 'rc', 11, 2)
            search = VERSION_RE.search(efilter.pk)

            if not search:
                logger.critical('Malformed %s PK/version: %s', self.model.__name__, efilter.pk)
                return ((-1,),)

            groupdict = search.groupdict()
            version_num = groupdict['version_num']  # eg '1.5'
            if not version_num:
                return ((0,),)

            version_num_tuple = tuple(int(x) for x in version_num.split('.'))

            # '', alpha', 'beta' or 'rc' -> yeah, they are already alphabetically sorted.
            version_mod = groupdict['version_mod'] or ''

            version_modnum_str = groupdict['version_modnum']  # eg '11' in 'rc11'
            version_modnum = int(version_modnum_str) if version_modnum_str else 1

            copy_num_str = groupdict['copy_num']  # eg '11' in 'base_pk[1.5]11'
            copy_num = int(copy_num_str) if copy_num_str else 0

            return version_num_tuple, version_mod, version_modnum, copy_num

        efilters.sort(key=key)

        return efilters[-1]  # TODO: max()

    def filter_by_user(self, user) -> QuerySet:
        """Get the EntityFilter queryset corresponding of filters which a user can see.
        @param user: A User instance.
        """
        if user.is_team:
            raise ValueError(
                f'EntityFilterManager.filter_by_user(): '
                f'user cannot be a team ({user})'
            )

        qs = self.filter(filter_type=EF_USER)

        return (
            qs
            if user.is_staff else
            qs.filter(
                Q(is_private=False)
                | Q(is_private=True, user__in=[user, *user.teams])
            )
        )

    def smart_update_or_create(
            self,
            pk: str,
            name: str,
            model: Type[CremeEntity],
            is_custom: bool = False,
            user=None,
            use_or: bool = False,
            is_private: bool = False,
            conditions=()) -> 'EntityFilter':
        """Creation helper ; useful for populate.py scripts.
        @param user: Can be None (ie: 'All users'), a User instance, or the string
                     'admin', which means 'the first admin user'.
        """
        forbidden = {'[', ']', '#', '?'}  # '&'

        if any((c in forbidden) for c in pk):
            raise ValueError(
                f'EntityFilterManager.smart_update_or_create(): '
                f'invalid character in "pk" (forbidden: {forbidden})'
            )

        if is_private:
            if not user:
                raise ValueError(
                    'EntityFilterManager.smart_update_or_create(): '
                    'a private filter must belong to a User.'
                )

            if not is_custom:
                # It should not be useful to create a private EntityFilter (so it
                # belongs to a user) which cannot be deleted.
                raise ValueError(
                    'EntityFilterManager.smart_update_or_create(): '
                    'a private filter must be custom.'
                )

        User = get_user_model()

        if isinstance(user, User):
            if user.is_staff:
                # Staff users cannot be owner in order to stay 'invisible'.
                raise ValueError(
                    'EntityFilterManager.smart_update_or_create(): '
                    'the owner cannot be a staff user.'
                )
        elif user == 'admin':
            user = User.objects.get_admin()

        ct = ContentType.objects.get_for_model(model)

        if is_custom:
            try:
                ef = self.get(pk=pk)
            except EntityFilter.DoesNotExist:
                ef = self.create(
                    pk=pk, name=name, is_custom=is_custom,
                    user=user, use_or=use_or, entity_type=ct,
                    is_private=is_private,
                )
            else:
                if ef.entity_type != ct:
                    # Changing the ContentType would create mess in related Report for example.
                    raise ValueError(
                        'You cannot change the entity type of an existing filter'
                    )

                if not ef.is_custom:
                    raise ValueError(
                        'You cannot change the "is_custom" value of an existing filter'
                    )

                update_model_instance(ef, name=name, user=user, use_or=use_or)
        else:
            if not conditions:
                raise ValueError(
                    'You must provide conditions for a non-custom Filter '
                    '(in order to compare with existing ones)'
                )

            try:
                ef = self.get_latest_version(pk)
            except self.model.DoesNotExist:
                ef = self.create(
                    pk=pk, name=name, is_custom=is_custom,
                    user=user, use_or=use_or, entity_type=ct,
                )
            else:
                if ef.entity_type != ct:
                    raise ValueError(
                        'You cannot change the entity type of an existing filter'
                    )

                if ef.is_custom:
                    raise ValueError(
                        'You cannot change the "is_custom" value of an existing filter'
                    )

                if use_or != ef.use_or or \
                   not EntityFilterCondition.conditions_equal(conditions, ef.get_conditions()):
                    from creme import __version__

                    new_pk = f'{pk}[{__version__}]'
                    new_name = f'{name} [{__version__}]'

                    latest_pk = ef.pk

                    if latest_pk.startswith(new_pk):
                        copy_num_str = latest_pk[len(new_pk):]

                        if not copy_num_str:
                            new_pk += '2'
                            new_name += '(2)'
                        else:
                            try:
                                copy_num = int(copy_num_str) + 1
                            except ValueError as e:
                                raise ValueError(
                                    f'Malformed EntityFilter PK/version: {latest_pk}'
                                ) from e

                            new_pk += str(copy_num)
                            new_name += f'({copy_num})'

                    ef = self.create(
                        pk=new_pk, name=new_name,
                        is_custom=is_custom,
                        user=user, use_or=use_or, entity_type=ct,
                    )
                else:
                    update_model_instance(ef, name=name)

        ef.set_conditions(conditions)

        return ef


class EntityFilter(models.Model):  # CremeModel ???
    """A model that contains conditions that filter queries on CremeEntity objects.
    They are principally used in the list views.
    Conditions can be :
     - On regular fields (eg: CharField, IntegerField) with a special behaviour for date fields.
     - On related fields (through ForeignKey or Many2Many).
     - On CustomFields (with a special behaviour for CustomFields with DATE type).
     - An other EntityFilter
     - The existence (or the not existence) of a kind of Relationship.
     - The holding (or the not holding) of a kind of CremeProperty
    """
    id = models.CharField(
        primary_key=True, max_length=100, editable=False,
    ).set_tags(viewable=False)
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    filter_type = models.PositiveSmallIntegerField(
        editable=False, default=EF_USER,
        choices=[(registry.id, registry.verbose_name) for registry in entity_filter_registries],
    ).set_tags(viewable=False)

    is_custom = models.BooleanField(editable=False, default=True).set_tags(viewable=False)
    user = core_fields.CremeUserForeignKey(
        verbose_name=_('Owner user'), blank=True, null=True,
        help_text=_('All users can see this filter, but only the owner can edit or delete it'),
    ).set_tags(viewable=False)
    is_private = models.BooleanField(
        pgettext_lazy('creme_core-entity_filter', 'Is private?'),
        default=False,
        help_text=_(
            'A private filter can only be used by its owner '
            '(or the teammates if the owner is a team)'
        ),
    )

    entity_type = core_fields.CTypeForeignKey(editable=False).set_tags(viewable=False)
    use_or = models.BooleanField(
        verbose_name=_('The entity is accepted if'),
        choices=[
            (False, _('All the conditions are met')),
            (True,  _('Any condition is met')),
        ],
        default=False,
    ).set_tags(viewable=False)

    objects = EntityFilterManager()

    creation_label = _('Create a filter')
    save_label     = _('Save the filter')

    _conditions_cache = None
    _connected_filter_cache = None
    _subfilter_conditions_cache = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Filter of Entity')
        verbose_name_plural = _('Filters of Entity')
        ordering = ('name',)

    class CycleError(Exception):
        pass

    class DependenciesError(Exception):
        pass

    class PrivacyError(Exception):
        pass

    def __str__(self):
        return self.name

    def accept(self, entity: CremeEntity, user) -> bool:
        """Check if a CremeEntity instance is accepted or refused by the filter.
        Use it for entities which have already been retrieved ; but prefer
        the method filter() in order to retrieve the least entities as possible.

        @param entity: Instance of <CremeEntity>.
        @param user: Instance of <django.contrib.auth.get_user_model()> ; it's
               the current user (& so is used to retrieve it & it's teams by the
               operand <CurrentUserOperand>.
        @return: A boolean ; True means the entity is accepted
                (ie: pass the conditions).
        """
        accepted = (
            condition.accept(entity=entity, user=user)
            for condition in self.get_conditions()
        )

        return any(accepted) if self.use_or else all(accepted)

    @property
    def applicable_on_entity_base(self) -> bool:
        """Can this filter be applied on CremeEntity (QuerySet or simple instance)?
        Eg: if a condition reads a model-field specific to a child class, the
            filter won't be applicable to CremeEntity.
        """
        return all(c.handler.applicable_on_entity_base for c in self.get_conditions())

    def can_delete(self, user) -> Tuple[bool, str]:
        if not self.is_custom:
            return False, gettext("This filter can't be edited/deleted")

        return self.can_edit(user)

    def can_edit(self, user) -> Tuple[bool, str]:
        assert not user.is_team

        if self.filter_type != EF_USER:
            return False, gettext('You cannot edit/delete a system filter')

        if not self.user_id:  # All users allowed
            return True, 'OK'

        if user.is_staff:
            return True, 'OK'

        if user.is_superuser and not self.is_private:
            return True, 'OK'

        if not user.has_perm(self.entity_type.app_label):
            return False, gettext('You are not allowed to access to this app')

        if not self.user.is_team:
            if self.user_id == user.id:
                return True, 'OK'

        elif user.id in self.user.teammates:  # TODO: move in a User method ??
            return True, 'OK'

        return False, gettext('You are not allowed to view/edit/delete this filter')

    def can_view(self, user, content_type: Optional[ContentType] = None) -> Tuple[bool, str]:
        if content_type and content_type != self.entity_type:
            return False, 'Invalid entity type'

        return self.can_edit(user)

    def check_cycle(self, conditions: Iterable['EntityFilterCondition']) -> None:
        assert self.id

        # Ids of EntityFilters that are referenced by these conditions
        ref_filter_ids = {
            sf_id
            for sf_id in (cond._get_subfilter_id() for cond in conditions)
            if sf_id
        }

        if self.id in ref_filter_ids:
            raise EntityFilter.CycleError(
                gettext('A condition can not reference its own filter.')
            )

        # TODO: method intersection not null
        if self.get_connected_filter_ids() & ref_filter_ids:
            raise EntityFilter.CycleError(
                gettext('There is a cycle with a sub-filter.')
            )

    def _check_privacy_parent_filters(self, is_private: bool, owner) -> None:
        if not self.id:
            return  # Cannot have a parent because we are creating the filter

        if not is_private:
            return  # Public children filters cannot cause problem to their parents

        for cond in self._iter_parent_conditions():
            parent_filter = cond.filter

            if not parent_filter.is_private:
                raise EntityFilter.PrivacyError(
                    gettext(
                        'This filter cannot be private because '
                        'it is a sub-filter for the public filter "{}"'
                    ).format(parent_filter.name)
                )

            if owner.is_team:
                if parent_filter.user.is_team:
                    if parent_filter.user != owner:
                        raise EntityFilter.PrivacyError(
                            gettext(
                                'This filter cannot be private and belong to this team '
                                'because it is a sub-filter for the filter "{filter}" '
                                'which belongs to the team "{team}".'
                            ).format(
                                filter=parent_filter.name,
                                team=parent_filter.user,
                            )
                        )
                elif parent_filter.user.id not in owner.teammates:
                    raise EntityFilter.PrivacyError(
                        gettext(
                            'This filter cannot be private and belong to this team '
                            'because it is a sub-filter for the filter "{filter}" '
                            'which belongs to the user "{user}" '
                            '(who is not a member of this team).'
                        ).format(
                            filter=parent_filter.name,
                            user=parent_filter.user,
                        )
                    )
            else:
                if not parent_filter.can_view(owner)[0]:
                    raise EntityFilter.PrivacyError(
                        gettext(
                            'This filter cannot be private because '
                            'it is a sub-filter for a private filter of another user.'
                        )
                    )

                if parent_filter.user.is_team:
                    raise EntityFilter.PrivacyError(
                        gettext(
                            'This filter cannot be private and belong to a user '
                            'because it is a sub-filter for the filter "{}" '
                            'which belongs to a team.'
                        ).format(parent_filter.name)
                    )

    def _check_privacy_sub_filters(
            self,
            conditions: Iterable['EntityFilterCondition'],
            is_private: bool,
            owner) -> None:
        # TODO: factorise
        ref_filter_ids = {
            sf_id
            for sf_id in (cond._get_subfilter_id() for cond in conditions)
            if sf_id
        }

        if is_private:
            if not owner:
                raise EntityFilter.PrivacyError(
                    gettext('A private filter must be assigned to a user/team.')
                )

            if owner.is_team:
                # All the teammate should have the permission to see the sub-filters,
                # so they have to be public or belong to the team.
                invalid_filter_names = EntityFilter.objects.filter(
                    pk__in=ref_filter_ids, is_private=True,
                ).exclude(user=owner).values_list('name', flat=True)

                if invalid_filter_names:
                    raise EntityFilter.PrivacyError(
                        ngettext(
                            'A private filter which belongs to a team can only '
                            'use public sub-filters & private sub-filters which '
                            'belong to this team.'
                            ' So this private sub-filter cannot be chosen: {}',
                            'A private filter which belongs to a team can only '
                            'use public sub-filters & private sub-filters which '
                            'belong to this team.'
                            ' So these private sub-filters cannot be chosen: {}',
                            len(invalid_filter_names)
                        ).format(', '.join(invalid_filter_names))
                    )
            else:
                invalid_filter_names = EntityFilter.objects.filter(
                    pk__in=ref_filter_ids, is_private=True,
                ).exclude(
                    user__in=[owner, *owner.teams],
                ).values_list('name', flat=True)

                if invalid_filter_names:
                    raise EntityFilter.PrivacyError(
                        ngettext(
                            'A private filter can only use public sub-filters, '
                            '& private sub-filters which belong to the same '
                            'user and his teams.'
                            ' So this private sub-filter cannot be chosen: {}',
                            'A private filter can only use public sub-filters, '
                            '& private sub-filters which belong to the same '
                            'user and his teams.'
                            ' So these private sub-filters cannot be chosen: {}',
                            len(invalid_filter_names)
                        ).format(', '.join(invalid_filter_names))
                    )
        else:
            invalid_filter_names = EntityFilter.objects.filter(
                pk__in=ref_filter_ids, is_private=True,
            ).values_list('name', flat=True)

            if invalid_filter_names:
                # All user can see this filter, so all user should have the permission
                # to see the sub-filters too ; so they have to be public (is_private=False)
                raise EntityFilter.PrivacyError(
                    ngettext(
                        'Your filter must be private in order to use this '
                        'private sub-filter: {}',
                        'Your filter must be private in order to use these '
                        'private sub-filters: {}',
                        len(invalid_filter_names)
                    ).format(', '.join(invalid_filter_names))
                )

    def check_privacy(
            self,
            conditions: Iterable['EntityFilterCondition'],
            is_private: bool,
            owner,
    ) -> None:
        "@raises EntityFilter.PrivacyError"
        self._check_privacy_sub_filters(conditions, is_private, owner)
        self._check_privacy_parent_filters(is_private, owner)

    # @classmethod
    # def create(cls, pk, name, model, is_custom=False, user=None, use_or=False,
    #            is_private=False, conditions=(),
    #           ):
    #     """Creation helper ; useful for populate.py scripts.
    #     @param user: Can be None (ie: 'All users'), a User instance, or the string
    #                  'admin', which means 'the first admin user'.
    #     """
    #     warnings.warn(
    #         'EntityFilter.create() is deprecated ; '
    #         'use EntityFilter.objects.smart_update_or_create() instead.',
    #         DeprecationWarning
    #     )
    #
    #     return cls.objects.smart_update_or_create(
    #         pk=pk, name=name, model=model,
    #         is_custom=is_custom, user=user,
    #         use_or=use_or, is_private=is_private, conditions=conditions,
    #     )

    def delete(self, check_orphan=True, *args, **kwargs):
        if check_orphan:
            parents = {str(cond.filter) for cond in self._iter_parent_conditions()}

            if parents:
                raise self.DependenciesError(
                    gettext(
                        'You can not delete this filter, '
                        'because it is used as sub-filter by: {}'
                    ).format(', '.join(parents))
                )

        super().delete(*args, **kwargs)

    @property
    def entities_are_distinct(self) -> bool:
        return all(cond.entities_are_distinct() for cond in self.get_conditions())
        # TODO ?
        # conds = self.get_conditions()
        # return all(cond.entities_are_distinct(conds) for cond in conds)

    @property
    def registry(self) -> _EntityFilterRegistry:
        return entity_filter_registries[self.filter_type]

    def filter(self, qs: QuerySet, user=None) -> QuerySet:
        qs = qs.filter(self.get_q(user))

        if not self.entities_are_distinct:
            qs = qs.distinct()

        return qs

    def _get_subfilter_conditions(self) -> QuerySet:
        sfc = self._subfilter_conditions_cache

        if sfc is None:
            q = Q()
            for handler_cls in self.registry.handler_classes:
                q |= handler_cls.query_for_parent_conditions(ctype=self.entity_type)

            self._subfilter_conditions_cache = sfc = (
                EntityFilterCondition.objects.filter(q) if q else
                EntityFilterCondition.objects.none()
            )

        return sfc

    def _iter_parent_conditions(self) -> Iterator['EntityFilterCondition']:
        pk = self.id

        for cond in self._get_subfilter_conditions():
            if cond._get_subfilter_id() == pk:
                yield cond

    def get_connected_filter_ids(self) -> Set[str]:
        # NB: 'level' means a level of filters connected to this filter :
        #  - 1rst level is 'self'.
        #  - 2rst level is filters with a sub-filter conditions relative to 'self'.
        #  - 3rd level  is filters with a sub-filter conditions relative to a
        #    filter of the 2nd level.
        # etc....
        if self._connected_filter_cache:
            return self._connected_filter_cache

        self._connected_filter_cache = connected = level_ids = {self.id}

        # Sub-filters conditions
        sf_conds = [
            (cond, cond._get_subfilter_id())
            for cond in self._get_subfilter_conditions()
        ]

        while level_ids:
            level_ids = {
                cond.filter_id
                for cond, filter_id in sf_conds
                if filter_id in level_ids
            }
            connected.update(level_ids)

        return connected

    def get_edit_absolute_url(self):
        return reverse('creme_core__edit_efilter', args=(self.id,))

    # @classmethod
    # def get_for_user(cls, user, content_type=None):
    #     """Get the EntityFilter queryset corresponding of filters which a user can see.
    #     @param user: A User instance.
    #     @param content_type: None (means 'for all ContentTypes').
    #            A ContentType instance (means 'filters related to this CT').
    #            An iterable of ContentType instances (means 'filters related to these CT').
    #     """
    #     warnings.warn(
    #         'EntityFilter.get_for_user() is deprecated ; '
    #         'use EntityFilter.objects.filter_by_user(...).filter(entity_type[__in]=...) '
    #         'instead.',
    #         DeprecationWarning
    #     )
    #
    #     assert not user.is_team
    #
    #     qs = cls.objects.filter(filter_type=EF_USER)
    #
    #     if content_type:
    #         qs = (
    #             qs.filter(entity_type=content_type)
    #             if isinstance(content_type, ContentType) else
    #             qs.filter(entity_type__in=content_type)
    #         )
    #
    #     return (
    #         qs if user.is_staff else
    #         qs.filter(
    #             Q(is_private=False) |
    #             Q(is_private=True, user__in=[user, *user.teams])
    #         )
    #     )

    def get_q(self, user=None) -> Q:
        query = Q()

        if user is None:
            user = get_global_info('user')

        if self.use_or:
            for condition in self.get_conditions():
                query |= condition.get_q(user)
        else:
            for condition in self.get_conditions():
                query &= condition.get_q(user)

        return query

    def _build_conditions_cache(self, conditions) -> None:
        checked_conds: List[EntityFilterCondition] = []
        append = checked_conds.append

        model = self.entity_type.model_class()

        for condition in conditions:
            condition.filter = self
            error = condition.error

            if error:
                # NB: we do not delete the instance of condition, because it can
                #     be temporarily erroneous (eg: commented app which
                #     registers handler/operator)
                logger.warning('%s => EntityFilterCondition instance is ignored', error)
            elif model != condition.handler.model:
                logger.warning(
                    'EntityFilterCondition related to a different model => we removed it'
                )
                condition.delete()
            else:
                append(condition)

        self._conditions_cache = checked_conds

    def get_conditions(self) -> List['EntityFilterCondition']:
        if self._conditions_cache is None:
            self._build_conditions_cache(self.conditions.all())

        return self._conditions_cache

    def set_conditions(self,
                       conditions,
                       check_cycles: bool = True,
                       check_privacy: bool = True,
                       ) -> None:
        assert all(c.filter_type == self.filter_type for c in conditions)

        if check_cycles:
            self.check_cycle(conditions)

        if check_privacy:
            self.check_privacy(conditions, self.is_private, owner=self.user)

        old_conditions = EntityFilterCondition.objects.filter(filter=self).order_by('id')
        conds2del = []

        for old_condition, condition in zip_longest(old_conditions, conditions):
            if not condition:
                # Less new conditions than old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.filter = self
                condition.save()
            elif old_condition.update(condition):
                old_condition.save()
                condition.pk = old_condition.pk  # If there is an error we delete it

        if conds2del:
            EntityFilterCondition.objects.filter(pk__in=conds2del).delete()

        self._build_conditions_cache(conditions)

    # @classmethod
    # def get_latest_version(cls, base_pk):
    #     """Get the latest EntityFilter from the family which uses the 'base_pk'.
    #     @raises EntityFilter.DoesNotExist If there is none instance in this family
    #     """
    #     warnings.warn('EntityFilter.get_latest_version() is deprecated ; '
    #                   'use EntityFilter.objects.get_latest_version() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.get_latest_version(base_pk)

    def get_verbose_conditions(self, user):
        "Generators of human-readable strings explaining the conditions."
        for cond in self.get_conditions():
            yield cond.description(user)


class EntityFilterCondition(models.Model):
    """Component of EntityFilter containing of data for conditions.

    Code for filtering (ie: building Q instances) is in 'core.entity_filter.condition_handler'
    in the child-classes of 'FilterConditionHandler'.

    Attributes/fields:
        - type: used to retrieve the right handler class.
        - name: used to store the main data of the condition, like the
                field's name or the RelationType's ID to use.
        - value: used to store other data of filtering (if needed), like the
                 value of field and the operator (eg: equal, contains, <= ...).

    Tip: use the helper methods 'build_condition()' in child-classes of
    'FilterConditionHandler' instead of calling directly the constructor.
    """
    filter = models.ForeignKey(
        EntityFilter, related_name='conditions', on_delete=models.CASCADE,
    )

    # NB: see core.entity_filter.condition_handler.FilterConditionHandler.type_id
    type = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=100)
    raw_value = models.TextField()  # TODO: use a JSONField ?

    _handler = None  # Cache for FilterConditionHandler instance.
    _model = None

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, model=None, filter_type=EF_USER, **kwargs):
        self.filter_type = filter_type
        super().__init__(*args, **kwargs)

        if self.filter_id is None:
            if model is None:
                raise ValueError('{}.__init__(): pass a filter or model', type(self))

            self._model = model

    def __repr__(self):
        return (
            'EntityFilterCondition('
            'filter_id={filter}, type={type}, name={name}, value={value}'
            ')'.format(
                filter=self.filter_id,
                type=self.type,
                name=self.name or 'None',
                value=self.value,
            )
        )

    def accept(self, entity: CremeEntity, user) -> bool:
        """Check if a CremeEntity instance is accepted or refused by the condition.
        Use it for entities which have already been retrieved ; but prefer
        the method get_q() in order to retrieve the least entities as possible.

        @param entity: Instance of <CremeEntity>.
        @param user: Instance of <django.contrib.auth.get_user_model()> ; it's
               the current user (& so is used to retrieve it & it's teams by the
               operand <CurrentUserOperand>.
        @return: A boolean ; True means the entity is accepted
                (ie: pass the condition).
        """
        return self.handler.accept(entity=entity, user=user)

    @staticmethod
    def conditions_equal(conditions1: Iterable['EntityFilterCondition'],
                         conditions2: Iterable['EntityFilterCondition'],
                         ) -> bool:
        """Compare 2 sequences on EntityFilterConditions related to the _same_
        EntityFilter instance.
        Beware: the 'filter' fields are not compared (so the related ContentType
        is not used).
        """
        # key = lambda cond: (cond.type, cond.name, cond.decoded_value)
        def key(cond):
            return cond.type, cond.name, cond.value

        return all(
            cond1
            and cond2
            and cond1.type == cond2.type
            and cond1.name == cond2.name
            and cond1.value == cond2.value
            for cond1, cond2 in zip_longest(
                sorted(conditions1, key=key),
                sorted(conditions2, key=key),
            )
        )

    def description(self, user):
        "Human-readable string explaining the condition."
        return self.handler.description(user)

    @property
    def handler(self) -> 'FilterConditionHandler':
        _handler = self._handler

        if _handler is None:
            registry = (
                self.filter.registry
                if self.filter_id else
                entity_filter_registries[self.filter_type]
            )
            self._handler = _handler = registry.get_handler(
                type_id=self.type,
                model=self.model,
                name=self.name,
                data=self.value,
            )

        return _handler

    @handler.setter
    def handler(self, value: 'FilterConditionHandler'):
        self._handler = value

    def entities_are_distinct(self) -> bool:  # TODO: argument "all_conditions" ?
        return self.handler.entities_are_distinct()

    @property
    def error(self) -> Optional[str]:
        handler = self.handler
        if handler is None:
            return 'Invalid data, cannot build a handler'

        return handler.error

    def get_q(self, user=None) -> Q:
        return self.handler.get_q(user)

    def _get_subfilter_id(self) -> Optional[str]:
        return self.handler.subfilter_id

    @property
    def model(self) -> Type[CremeEntity]:  # TODO: test
        return self._model or self.filter.entity_type.model_class()

    def update(self, other_condition: 'EntityFilterCondition') -> bool:
        """Fill a condition with the content a another one
        (in order to reuse the old instance if possible).
        @return True if there is at least one change, else False.
        """
        changed = False

        for attr in ('type', 'name', 'value'):
            other = getattr(other_condition, attr)

            if getattr(self, attr) != other:
                setattr(self, attr, other)
                changed = True

        return changed

    @property
    def value(self):
        raw_value = self.raw_value
        return json_load(raw_value) if raw_value else None

    @value.setter
    def value(self, raw_value) -> None:
        self.raw_value = json_encode(raw_value)


# TODO: manage also deletion of:
#  - instance linked with FK (Sector, Priority...).
#  - instance of CremeEntity used by Relation handlers.
@receiver(pre_delete)
def _delete_related_efc(sender, instance, **kwargs):
    from ..core.entity_filter.condition_handler import all_handlers

    q = Q()
    for handler_cls in all_handlers:
        q |= handler_cls.query_for_related_conditions(instance)

    if q:
        EntityFilterCondition.objects.filter(q).delete()
