################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.utils.translation import gettext as _

from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.core.copying import PostSaveCopier
from creme.creme_core.core.exceptions import ConflictError


class AddressesCopier(PostSaveCopier):
    def copy_to(self, target):
        source = self._source
        save = False

        # TODO: Address.clone() => Copier too?
        if source.billing_address is not None:
            target.billing_address = source.billing_address.clone(target)
            save = True

        if source.shipping_address is not None:
            target.shipping_address = source.shipping_address.clone(target)
            save = True

        for address in source.other_addresses:
            address.clone(target)

        return save


class ContactCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        AddressesCopier,
    ]


class OrganisationCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        AddressesCopier,
    ]

    def check_permissions(self, *, user, entity):
        super().check_permissions(user=user, entity=entity)

        if entity.is_managed:
            raise ConflictError(_('a managed organisation cannot be cloned'))
