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

from django.db.models import Q
from django.dispatch import receiver

from creme.creme_config.signals import disable_custom_entity_type
from creme.creme_core.gui.custom_form import FieldGroupList
from creme.creme_core.models import CustomFormConfigItem, MenuConfigItem

from . import custom_forms


@receiver(disable_custom_entity_type, dispatch_uid='custom_entities-reset_customforms')
def delete_customtype_customforms(sender, entity_ctype, **kwargs):
    descriptors = [
        custom_forms.creation_descriptors.get(sender.id),
        custom_forms.edition_descriptors.get(sender.id),
    ]

    for descriptor in descriptors:
        for cfci in CustomFormConfigItem.objects.filter(
            descriptor_id=descriptor.id,
            role=None, superuser=False,
        ):
            cfci.store_groups(FieldGroupList.from_cells(
                model=descriptor.model,
                data=descriptor.default_groups_desc,
                cell_registry=descriptor.build_cell_registry(),
                # NB: not useful in vanilla code
                # TODO: test
                allowed_extra_group_classes=(*descriptor.extra_group_classes,),
            ))
            cfci.save()

    CustomFormConfigItem.objects.filter(
        descriptor_id__in=[desc.id for desc in descriptors],
    ).filter(
        Q(superuser=True) | Q(role__isnull=False),
    ).delete()


@receiver(disable_custom_entity_type, dispatch_uid='custom_entities-delete_menu')
def delete_custom_entities_menu(sender, entity_ctype, **kwargs):
    MenuConfigItem.objects.filter(entry_id__in=[
        f'custom_entities-list{sender.id}',
        f'custom_entities-create{sender.id}',
    ]).delete()
