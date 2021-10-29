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
from collections import defaultdict
# from typing import Tuple
from typing import (
    TYPE_CHECKING,
    DefaultDict,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
    Union,
)

from django.contrib.contenttypes.models import ContentType
# from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.query_utils import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..utils import find_first
# from ..utils.meta import FieldInfo
from ..utils.meta import ModelFieldEnumerator
from .auth import UserRole
from .base import CremeModel
from .entity import CremeEntity
from .fields import DatePeriodField, EntityCTypeForeignKey

if TYPE_CHECKING:
    from ..core.entity_cell import EntityCell

logger = logging.getLogger(__name__)


# class SearchField:
#     __slots__ = ('__name', '__verbose_name')
#
#     def __init__(self, field_name: str, field_verbose_name: str):
#         self.__name = field_name
#         self.__verbose_name = field_verbose_name
#
#     def __str__(self):
#         return self.__verbose_name
#
#     @property
#     def name(self) -> str:
#         return self.__name
#
#     @property
#     def verbose_name(self) -> str:
#         return self.__verbose_name


class SearchConfigItemManager(models.Manager):
    def create_if_needed(self,
                         model: Type[CremeEntity],
                         fields: Iterable[str],
                         role: Union[UserRole, str, None] = None,
                         disabled: bool = False,
                         ) -> 'SearchConfigItem':
        """Create a config item & its fields if one does not already exists.
        @param model: Model class the configuration is related to.
        @param fields: Sequence of strings representing regular field names.
        @param role: UserRole instance; or 'superuser'; or None, for default configuration.
        @param disabled: Boolean.
        """
        from ..core.entity_cell import EntityCellRegularField

        ct = ContentType.objects.get_for_model(model)  # TODO: accept ContentType instance ?
        superuser = False

        if role == 'superuser':
            superuser = True
            role = None
        elif role is not None:
            assert isinstance(role, UserRole)

        sci, created = self.get_or_create(
            content_type=ct,
            role=role,
            superuser=superuser,
            defaults={
                'disabled': disabled,
                'cells': [
                    EntityCellRegularField.build(model, field_name)
                    for field_name in fields
                ],
            },
        )

        # if created:
        #     sci._build_searchfields(model, fields)

        return sci

    def iter_for_models(self,
                        models: Iterable[Type[CremeEntity]],
                        user,
                        ) -> Iterator['SearchConfigItem']:
        "Get the SearchConfigItem instances corresponding to the given models (generator)."
        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(model) for model in models]

        role_query = Q(role__isnull=True)
        if user.is_superuser:
            role_query |= Q(superuser=True)

            def filter_func(sci):
                return sci.superuser
        else:
            role = user.role
            role_query |= Q(role=role)

            def filter_func(sci):
                return sci.role == role

# TODO: use a similar way if superuser is a role
#       (PG does not return a cool result if we do a ".order_by('role', 'superuser')")
#        sc_items = {
#            sci.content_type: sci
#            for sci in SearchConfigItem.objects
#                                       .filter(content_type__in=ctypes)
#                                       .filter(Q(user=user) | Q(user__isnull=True))
#                                       # Config of the user has higher priority
#                                       # than the default one
#                                       .order_by('user')
#        }
#
#        for ctype in ctypes:
#            yield sc_items.get(ctype) or SearchConfigItem(content_type=ctype)
        sc_items_per_ctid: DefaultDict[int, list] = defaultdict(list)
        for sci in self.filter(content_type__in=ctypes).filter(role_query):
            sc_items_per_ctid[sci.content_type_id].append(sci)

        for ctype in ctypes:
            sc_items = sc_items_per_ctid.get(ctype.id)

            if sc_items:
                try:
                    yield find_first(sc_items, filter_func)
                except IndexError:
                    yield sc_items[0]
            else:
                yield self.model(content_type=ctype)


class SearchConfigItem(CremeModel):
    content_type = EntityCTypeForeignKey(verbose_name=_('Related resource'))
    role = models.ForeignKey(
        UserRole, verbose_name=_('Related role'),
        null=True, default=None, on_delete=models.CASCADE,
    )
    # TODO: a UserRole for superusers instead ??
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    disabled = models.BooleanField(
        pgettext_lazy('creme_core-search_conf', 'Disabled?'), default=False,
    )

    # # Do not this field directly; use 'searchfields' property
    # field_names = models.TextField(null=True)
    # Do not this field directly; use 'cells' property instead
    json_cells = models.JSONField(editable=False, default=list)  # TODO: CellsField ?

    objects = SearchConfigItemManager()

    creation_label = _('Create a search configuration')
    save_label     = _('Save the configuration')

    # _searchfields: Optional[Tuple[SearchField, ...]] = None
    _cells: Optional[List['EntityCell']] = None
    # _all_fields: bool

    EXCLUDED_FIELDS_TYPES: List[Type[models.Field]] = [
        models.DateTimeField, models.DateField,
        models.FileField, models.ImageField,
        models.BooleanField, models.NullBooleanField,
        DatePeriodField,  # TODO: JSONField ?
    ]

    class Meta:
        app_label = 'creme_core'
        unique_together = ('content_type', 'role', 'superuser')

    def __str__(self):
        if self.superuser:
            return gettext('Search configuration of super-users for «{model}»').format(
                model=self.content_type,
            )

        role = self.role

        if role is None:
            return gettext('Default search configuration for «{model}»').format(
                model=self.content_type,
            )

        return gettext('Search configuration of «{role}» for «{model}»').format(
            role=role,
            model=self.content_type,
        )

    @property
    def all_fields(self) -> bool:
        """@return True means that all fields are used to search
                   (no specific configuration).
        """
        # self.searchfields  # NOQA  # Computes self._all_fields
        # return self._all_fields
        return next(self.cells, None) is None

    @property
    def is_default(self) -> bool:
        "Is default configuration?"
        return self.role_id is None and not self.superuser

    # @classmethod
    # def _get_modelfields_choices(cls, model: Type[CremeEntity]) -> List[Tuple[str, str]]:
    #     excluded = tuple(cls.EXCLUDED_FIELDS_TYPES)
    #     return ModelFieldEnumerator(
    #         model, deep=1
    #     ).filter(
    #         viewable=True,
    #     ).exclude(
    #         lambda f, depth: isinstance(f, excluded) or f.choices
    #     ).choices()

    # def _build_searchfields(self,
    #                         model: Type[CremeEntity],
    #                         fields: Iterable[str],
    #                         save: bool = True) -> None:
    #     sfields: List[SearchField] = []
    #     old_field_names = self.field_names
    #
    #     for field_name in fields:
    #         try:
    #             field_info = FieldInfo(model, field_name)
    #         except FieldDoesNotExist as e:
    #             logger.warning('%s => SearchField removed', e)
    #         else:
    #             sfields.append(
    #                 SearchField(field_name=field_name,
    #                             field_verbose_name=field_info.verbose_name,
    #                            )
    #             )
    #
    #     self.field_names = ','.join(sf.name for sf in sfields) or None
    #
    #     if not sfields:  # field_names is empty => use all compatible fields
    #         sfields.extend(
    #             SearchField(field_name=field_name, field_verbose_name=verbose_name)
    #             for field_name, verbose_name in self._get_modelfields_choices(model)
    #         )
    #         self._all_fields = True
    #     else:
    #         self._all_fields = False
    #
    #     # We can pass the reference to this immutable collections
    #     # (and SearchFields are hardly mutable).
    #     self._searchfields = tuple(sfields)
    #
    #     if save and old_field_names != self.field_names:
    #         self.save()
    #
    # @property
    # def searchfields(self) -> Tuple[SearchField, ...]:
    #     if self._searchfields is None:
    #         names = self.field_names
    #         self._build_searchfields(
    #             self.content_type.model_class(), names.split(',') if names else ()
    #         )
    #
    #     return self._searchfields
    #
    # @searchfields.setter
    # def searchfields(self, fields: Iterable[str]) -> None:
    #     "@param fields: Iterable of strings representing field names."
    #     self._build_searchfields(self.content_type.model_class(), fields, save=False)
    #
    # def get_modelfields_choices(self) -> List[Tuple[str, str]]:
    #     """Return a list of tuples (useful for Select.choices) representing
    #     Fields that can be chosen by the user.
    #     """
    #     return self._get_modelfields_choices(self.content_type.model_class())

    @property
    def cells(self) -> Iterator['EntityCell']:
        "Return the stored EntityCell instance."
        cells = self._cells

        if cells is None:
            from ..core.entity_cell import CELLS_MAP

            cells, errors = CELLS_MAP.build_cells_from_dicts(
                model=self.content_type.model_class(),
                dicts=self.json_cells,
            )

            # TODO ??
            # if errors:
            #     logger.warning('SearchConfigItem(id="%s") is saved with valid cells.', self.id)
            #     self._dump_cells(cells)
            #     self.save()

            self._cells = cells

        yield from cells

    @cells.setter
    def cells(self, cells: Iterable['EntityCell']) -> None:
        self._cells = cells = [cell for cell in cells if cell]
        self.json_cells = [cell.to_dict() for cell in cells]

    @property
    def refined_cells(self) -> Iterator['EntityCell']:
        """Yield the EntityCell instances which should be used to search.
        It avoids fields hidden with FieldsConfig & deleted CustomFields.
        It builds the cells to use when no specific cell have been configured.
        """
        if self.all_fields:
            from ..core.entity_cell import EntityCellRegularField

            model = self.content_type.model_class()
            excluded = tuple(self.EXCLUDED_FIELDS_TYPES)
            enumerator = ModelFieldEnumerator(
                model=model, depth=1,
            ).filter(
                viewable=True,
            ).exclude(
                lambda model, field, depth: isinstance(field, excluded) or field.choices
            )

            for field_parts in enumerator:
                # TODO: constructor for FieldInfo from fields sequence
                #       (to avoid useless '__' join then split)
                yield EntityCellRegularField.build(
                    model, '__'.join(field.name for field in field_parts),
                )
        else:
            assert self._cells is not None

            for cell in self._cells:
                if not cell.is_excluded:
                    yield cell

    # @classmethod
    # def create_if_needed(cls, model, fields, role=None, disabled=False):
    #     """Create a config item & its fields if one does not already exists.
    #     @param fields: Sequence of strings representing field names.
    #     @param role: UserRole instance; or 'superuser'; or None, for default configuration.
    #     @param disabled: Boolean.
    #     """
    #     warnings.warn('SearchConfigItem.create_if_needed() is deprecated ; '
    #                   'use SearchConfigItem.objects.create_if_needed() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return cls.objects.create_if_needed(
    #         model=model, fields=fields, role=role, disabled=disabled,
    #     )

    # @classmethod
    # def get_4_models(cls, models, user):
    #     "Get the SearchConfigItem instances corresponding to the given models (generator)."
    #     warnings.warn('SearchConfigItem.get_4_models() is deprecated ; '
    #                   'use SearchConfigItem.objects.iter_for_models() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     yield from cls.objects.iter_for_models(models, user)

    def save(self, *args, **kwargs):
        if self.superuser and self.role_id:
            raise ValueError('"role" must be NULL if "superuser" is True')

        super().save(*args, **kwargs)
