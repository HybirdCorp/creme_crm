################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CustomEntitiesConfig(CremeAppConfig):
    default = True
    name = 'creme.custom_entities'
    verbose_name = _('Custom entities')

    def all_apps_ready(self):
        super().all_apps_ready()

        from . import signals  # NOQA

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        for descriptor in custom_forms.creation_descriptors.values():
            cform_registry.register(descriptor)

        for descriptor in custom_forms.edition_descriptors.values():
            cform_registry.register(descriptor)

    def register_icons(self, icon_registry):
        from .models import all_custom_models

        register = icon_registry.register
        for model in all_custom_models:
            register(model, 'images/wall_%(size)s.png')

    def register_menu_entries(self, menu_registry):
        from creme.creme_core.gui import menu
        from creme.creme_core.models import CustomEntityType

        from .models import all_custom_models

        class CustomListviewEntryBase(menu.ListviewEntry):
            custom_id = 0

            def __init__(this, **kwargs):
                super().__init__(**kwargs)
                ce_type = CustomEntityType.objects.get_for_id(this.custom_id)
                if not ce_type.enabled:
                    this.label = ''  # Means the entry should be ignored
                elif ce_type.deleted:
                    this.label = gettext('{model} [deleted]').format(model=ce_type.plural_name)
                else:
                    this.label = ce_type.plural_name

        class CustomCreationEntryBase(menu.CreationEntry):
            custom_id = 0

            def __init__(this, **kwargs):
                super().__init__(**kwargs)
                ce_type = CustomEntityType.objects.get_for_id(this.custom_id)
                if not ce_type.enabled:
                    this.label = ''  # Means the entry should be ignored
                elif ce_type.deleted:
                    this.label = gettext('Create a entity «{model}» [deleted]').format(
                        model=ce_type.name,
                    )
                else:
                    this.label = gettext('Create a entity «{model}»').format(model=ce_type.name)

        for model in all_custom_models:
            menu_registry.register(
                type(
                    f'CustomEntitiesEntry{model.custom_id}',
                    (CustomListviewEntryBase,),  # Parent classes
                    {
                        'id': f'custom_entities-list{model.custom_id}',
                        'model': model,
                        'custom_id': model.custom_id,
                    },  # Attributes
                ),
                type(
                    f'CustomEntityCreationEntry{model.custom_id}',
                    (CustomCreationEntryBase,),  # Parent classes
                    {
                        'id': f'custom_entities-create{model.custom_id}',
                        'model': model,
                        'custom_id': model.custom_id,
                    },  # Attributes
                ),
            )
