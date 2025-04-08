################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from typing import TYPE_CHECKING, Literal

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from .auth import CremeUser, UserRole

if TYPE_CHECKING:
    from ..gui.custom_form import CustomFormDescriptor, FieldGroupList


class CustomFormConfigItemManager(models.Manager):
    def create_if_needed(self, *,
                         descriptor: CustomFormDescriptor,
                         groups_desc=None,
                         role: Literal['superuser'] | UserRole | None = None,
                         ) -> CustomFormConfigItem:
        """Creation helper (for "populate" scripts mainly).
        Create an instance of CustomFormConfigItem, related to a
        CustomFormDescriptor, if there is no one.
        """
        from ..gui.custom_form import FieldGroupList

        desc_id = descriptor.id

        match role:
            case None:
                role_kwargs = {}
            case 'superuser':
                role_kwargs = {'superuser': True}
            case _:
                assert isinstance(role, UserRole)
                role_kwargs = {'role': role}

        item = self.filter(descriptor_id=desc_id, **role_kwargs).first()

        if item is None:
            item = self.model(descriptor_id=desc_id, **role_kwargs)
            item.store_groups(FieldGroupList.from_cells(
                model=descriptor.model,
                data=groups_desc or descriptor.default_groups_desc,
                cell_registry=descriptor.build_cell_registry(),
                allowed_extra_group_classes=(*descriptor.extra_group_classes,),
            ))
            item.save()

        return item

    create_if_needed.alters_data = True

    def get_for_user(self, *,
                     descriptor: str | CustomFormDescriptor,
                     user: CremeUser,
                     ) -> CustomFormConfigItem:
        descriptor_id = descriptor if isinstance(descriptor, str) else descriptor.id
        no_user_qs = self.filter(descriptor_id=descriptor_id)

        # NB: we use order_by() + first() to retrieve with a higher priority the
        #     instance corresponding to the role, and fallback to the default config.
        qs = (
            no_user_qs.filter(role=None).order_by('-superuser')
            if user.is_superuser else
            no_user_qs.filter(superuser=False)
                      .filter(Q(role=user.role_id) | Q(role=None))
                      .order_by(F('role').desc(nulls_last=True))
        )
        cfci = qs.first()

        if cfci is None:
            raise self.model.DoesNotExist(
                f'No <{self.model.__name__}> found for '
                f'descriptor="{descriptor_id}" & user="{user.username}".'
            )

        return cfci


class CustomFormConfigItem(models.Model):
    """Store the fields/groups of fields in the custom-form system.
    See also: <creme_core.gui.custom_form>.
    """
    descriptor_id = models.CharField(
        verbose_name=_('Type of form'), max_length=100, editable=False,
    )
    json_groups = models.JSONField(editable=False, default=list)

    role = models.ForeignKey(
        UserRole, verbose_name=_('Related role'),
        null=True, blank=True, default=None, on_delete=models.CASCADE,
    )  # TODO: editable=False?
    # TODO: a UserRole for superusers instead ??
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    objects = CustomFormConfigItemManager()

    creation_label = _('Create a custom form')
    save_label = _('Save the custom form')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Custom form')
        verbose_name_plural = _('Custom forms')
        # ordering = ('id',)
        # NB:
        #  unique_together = ('descriptor_id', 'role', 'superuser')
        #  =>  does not work because None values for role cause skipping
        #      (see  django.db.models.base.Model._perform_unique_checks() )
        #  => TODO: role for superuser?
        #  => TODO: temporary system to delete duplicates?
        unique_together = ('descriptor_id', 'role')

    def __str__(self):
        return (
            f'{type(self).__name__}('
            f'descriptor_id="{self.descriptor_id}", '
            f'role={self.role!r}, '
            f'superuser={self.superuser}'
            f')'
        )

    def groups_as_dicts(self) -> list[dict]:
        return self.json_groups

    def store_groups(self, groups: FieldGroupList) -> None:
        # TODO: specific encoder?
        self.json_groups = [group.as_dict() for group in groups]
