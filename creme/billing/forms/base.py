################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from creme.creme_core.forms import (
    CreatorEntityField,
    CremeEntityForm,
    GenericEntityField,
)
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.persons import get_contact_model, get_organisation_model

logger = logging.getLogger(__name__)


def first_managed_organisation():
    try:
        # NB: we use the cache
        return get_organisation_model().objects.filter_managed_by_creme()[0]
    except IndexError:
        logger.warning('No managed organisation ?!')


class BillingSourceSubCell(CustomFormExtraSubCell):
    sub_type_id = 'billing_source'
    verbose_name = pgettext_lazy('billing', 'Source organisation')

    def formfield(self, instance, user, **kwargs):
        return CreatorEntityField(
            label=self.verbose_name,
            model=get_organisation_model(),
            user=user,
            initial=first_managed_organisation() if not instance.pk else instance.source,
        )


class BillingTargetSubCell(CustomFormExtraSubCell):
    sub_type_id = 'billing_target'
    verbose_name = pgettext_lazy('billing', 'Target')

    def formfield(self, instance, user, **kwargs):
        field = GenericEntityField(
            label=self.verbose_name,
            models=[get_organisation_model(), get_contact_model()],
            user=user,
        )

        if instance.pk:
            field.initial = instance.target

        return field


class BaseCustomForm(CremeEntityForm):
    class Meta:
        labels = {
            'discount': _('Overall discount (in %)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        self.old_user_id = instance.user_id

        get_key = self.subcell_key
        self.source_cell_key = get_key(BillingSourceSubCell)
        self.target_cell_key = get_key(BillingTargetSubCell)

        if (
            not instance.pk
            and type(instance).generate_number_in_create
            and 'number' in self.fields
        ):
            managed_orga = first_managed_organisation()
            if managed_orga:
                self.fields['number'].help_text = gettext(
                    'If you chose an organisation managed by {software} (like «{organisation}») '
                    'as source organisation, a number will be automatically generated.'
                ).format(software=settings.SOFTWARE_LABEL, organisation=managed_orga)

    def clean(self):
        cdata = super().clean()
        instance = self.instance

        instance.source = cdata.get(self.source_cell_key)
        instance.target = cdata.get(self.target_cell_key)

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance

        # TODO: do this in model/with signal to avoid errors ???
        if self.old_user_id and self.old_user_id != self.cleaned_data['user'].id:
            # Do not use queryset.update() to call the CremeEntity.save() method
            # TODO: change with future Credentials system ??
            for line in instance.iter_all_lines():
                line.user = instance.user
                line.save()

        return super().save(*args, **kwargs)
