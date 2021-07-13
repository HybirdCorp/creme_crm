# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django import forms
from django.db.models.aggregates import Max
from django.utils.translation import gettext_lazy as _

from creme.creme_config.forms.fields import MenuEntriesField
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.models import MenuConfigItem

logger = logging.getLogger(__name__)


class ContainerForm(CremeModelForm):
    # TODO: factorise with MenuEntryForm
    label = forms.CharField(label=_('Label'), max_length=50)
    entries = MenuEntriesField(label=_('Entries'))

    menu_registry = menu_registry

    class Meta(CremeModelForm.Meta):
        model = MenuConfigItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        self._children = children = [*instance.children.all()] if instance.pk else []

        fields = self.fields
        fields['label'].initial = instance.entry_data.get('label')

        entries_f = fields['entries']

        registry = self.menu_registry
        entries_f.menu_registry = registry
        entries_f.excluded_entry_ids = MenuConfigItem.objects.exclude(
            id__in=[child.id for child in children],
        ).values_list('entry_id', flat=True)

        initial_entries = []
        for child in children:
            entry_class = registry.get_class(child.entry_id)
            if entry_class is None:
                logger.warning(
                    '%s: Invalid class with id="%s"',
                    type(self).__name__, child.entry_id,
                )
            else:
                initial_entries.append(
                    entry_class(
                        # config_item_id=item.id,
                        data=child.entry_data,
                    )
                )

        entries_f.initial = initial_entries

    def save(self, *args, **kwargs):
        instance = self.instance
        cdata = self.cleaned_data
        instance.entry_data['label'] = cdata['label']

        if instance.pk is None:
            instance.entry_id = ContainerEntry.id

            max_order = MenuConfigItem.objects.filter(
                entry_id__in=[
                    entry_class.id
                    for entry_class in self.menu_registry.entry_classes
                    if entry_class.level == 0
                ],
            ).aggregate(Max('order')).get('order__max')
            instance.order = 0 if max_order is None else max_order + 1

        # TODO: use 'commit' parameter ??
        super().save(*args, **kwargs)

        item_model = type(instance)
        entries = cdata['entries']
        children = self._children
        needed = len(entries)
        diff_length = needed - len(children)

        if diff_length < 0:
            items_store = children[:needed]
            item_model._default_manager.filter(
                pk__in=[child.id for child in children[needed:]],
            ).delete()
        else:
            items_store = [*children]

            if diff_length > 0:
                items_store.extend(item_model(parent=instance) for __ in range(diff_length))

        store_it = iter(items_store)

        # TODO: bulk_create/update
        for order, entry in enumerate(entries):
            item = next(store_it)
            item.entry_id = entry.id
            item.order = order
            item.entry_data = entry.data

            item.save()

        return instance


# TODO: factorise
class SpecialContainerAddingForm(CremeModelForm):
    entry_id = forms.ChoiceField(label=_('Type of container'))

    class Meta(CremeModelForm.Meta):
        model = MenuConfigItem

    excluded_entry_ids = {ContainerEntry.id}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        excluded_entry_ids = self.excluded_entry_ids
        used_entry_ids = {
            *MenuConfigItem.objects.values_list('entry_id', flat=True),
        }
        self.fields['entry_id'].choices = [
            (entry_class.id, entry_class.label)
            for entry_class in menu_registry.entry_classes
            if (
                entry_class.level == 0
                and entry_class.id not in excluded_entry_ids
                and (
                    entry_class.id not in used_entry_ids
                    or not entry_class.single_instance
                )
            )
        ]

    def save(self, *args, **kwargs):
        max_order = MenuConfigItem.objects.filter(
            entry_id__in=[
                entry_class.id
                for entry_class in menu_registry.entry_classes
                if entry_class.level == 0
            ],
        ).aggregate(Max('order')).get('order__max')

        instance = self.instance
        instance.order = 0 if max_order is None else max_order + 1
        instance.entry_id = self.cleaned_data['entry_id']

        return super().save(*args, **kwargs)
