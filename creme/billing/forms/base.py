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

import logging

from django.conf import settings
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.forms as core_forms
from creme.billing.models import NumberGeneratorItem
from creme.billing.setting_keys import emitter_edition_key
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import CremeEntity, SettingValue
from creme.persons import get_contact_model, get_organisation_model

logger = logging.getLogger(__name__)


def first_managed_organisation():
    try:
        # NB: we use the cache
        return get_organisation_model().objects.filter_managed_by_creme()[0]
    except IndexError:
        logger.warning('No managed organisation?!')


class BillingSourceSubCell(CustomFormExtraSubCell):
    sub_type_id = 'billing_source'
    verbose_name = pgettext_lazy('billing', 'Source organisation')

    def formfield(self, instance, user, **kwargs):
        if (
            instance.pk
            and instance.number
            and not instance.generate_number_in_create  # Invoice & CreditNote
            and not SettingValue.objects.get_4_key(emitter_edition_key, default=False).value
        ):
            return core_forms.ReadonlyMessageField(
                label=self.verbose_name, return_value=(),
                initial=_('Your configuration forbids you to edit the source Organisation'),
            )

        return core_forms.CreatorEntityField(
            label=self.verbose_name,
            model=get_organisation_model(),
            user=user,
            initial=first_managed_organisation() if not instance.pk else instance.source,
        )


class BillingTargetSubCell(CustomFormExtraSubCell):
    sub_type_id = 'billing_target'
    verbose_name = pgettext_lazy('billing', 'Target')

    def formfield(self, instance, user, **kwargs):
        field = core_forms.GenericEntityField(
            label=self.verbose_name,
            models=[get_organisation_model(), get_contact_model()],
            user=user,
        )

        if instance.pk:
            field.initial = instance.target

        return field


class BaseCustomForm(core_forms.CremeEntityForm):
    class Meta:
        labels = {
            'discount': _('Overall discount (in %)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        # self.old_user_id = instance.user_id
        # TODO: use Snapshot instead?
        self.old_number = instance.number

        get_key = self.subcell_key
        self.source_cell_key = get_key(BillingSourceSubCell)
        self.target_cell_key = get_key(BillingTargetSubCell)

        if (
            not instance.pk
            and type(instance).generate_number_in_create
            and 'number' in self.fields
        ):
            if managed_orga := first_managed_organisation():
                self.fields['number'].help_text = gettext(
                    'If you chose an organisation managed by {software} (like «{organisation}») '
                    'as source organisation, a number will be automatically generated.'
                ).format(software=settings.SOFTWARE_LABEL, organisation=managed_orga)

    def clean(self):
        cdata = super().clean()
        instance = self.instance

        emitter = cdata.get(self.source_cell_key)
        if isinstance(emitter, CremeEntity):  # Do not assign if ReadonlyMessageField
            instance.source = emitter

        instance.target = cdata.get(self.target_cell_key)

        number = self.cleaned_data['number']
        if (not instance.pk and number) or (instance.pk and self.old_number != number):
            item = NumberGeneratorItem.objects.get_for_instance(instance)

            if item and not item.is_edition_allowed:
                self.add_error(
                    field='number',
                    error=_('The number is set as not editable by the configuration.'),
                )

        return cdata

    # def save(self, *args, **kwargs):
    #     instance = self.instance
    #
    #     if self.old_user_id and self.old_user_id != self.cleaned_data['user'].id:
    #         for line in instance.iter_all_lines():
    #             line.user = instance.user
    #             line.save()
    #
    #     return super().save(*args, **kwargs)
