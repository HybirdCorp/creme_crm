################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.forms import ChoiceField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.custom_form import CustomFormExtraSubCell

from . import base


class BillingTemplateStatusSubCell(CustomFormExtraSubCell):
    sub_type_id = 'billing_template_status'
    verbose_name = _('Status')

    def formfield(self, instance, user, **kwargs):
        if instance.ct:
            meta = instance.ct.model_class()._meta
            field = ChoiceField(
                label=gettext('Status of {}').format(meta.verbose_name),
                choices=[
                    (status.id, str(status))
                    for status in meta.get_field('status').remote_field.model.objects.all()
                ],
                **kwargs
            )

            status_id = instance.status_id
            if status_id:
                field.initial = status_id
        else:  # In creme config
            field = ChoiceField(label='Status')

        return field


# TODO: rename (remove "Creation") ?
class BaseTemplateCreationCustomForm(base.BaseCustomForm):
    class Meta(base.BaseCustomForm.Meta):
        help_texts = {
            'number': _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
        }

    def __init__(self, ct=None, *args, **kwargs):  # 'ct' arg => see RecurrentGeneratorWizard
        super().__init__(*args, **kwargs)
        if ct:
            assert self.instance.pk is None
            self.instance.ct = ct

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.status_id = self.cleaned_data[self.subcell_key(BillingTemplateStatusSubCell)]

        return super().save(*args, **kwargs)
