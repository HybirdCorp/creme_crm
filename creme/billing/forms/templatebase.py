# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from .. import get_template_base_model
# from .base import copy_or_create_address
from .base import BaseEditForm, first_managed_orga_id


class _TemplateBaseForm(BaseEditForm):
    status = ChoiceField(label=_('Status'), choices=())

    # class Meta:
    class Meta(BaseEditForm.Meta):
        model = get_template_base_model()
        # exclude = (*BaseEditForm.Meta.exclude, 'ct', 'status_id')
        help_texts = {
            'number': _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
        }

    def _build_status_field(self, billing_ct):
        meta = billing_ct.model_class()._meta
        status_field = self.fields['status']

        status_field.label = gettext('Status of {}').format(meta.verbose_name)
        status_field.choices = [
            (status.id, str(status))
            for status in meta.get_field('status').remote_field.model.objects.all()
        ]

        return status_field

    def save(self, *args, **kwargs):
        self.instance.status_id = self.cleaned_data['status']
        return super().save(*args, **kwargs)


class TemplateBaseEditForm(_TemplateBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance

        status_field = self._build_status_field(instance.ct)
        status_field.initial = instance.status_id


class TemplateBaseCreateForm(_TemplateBaseForm):
    def __init__(self, ct, *args, **kwargs):  # 'ct' arg => see RecurrentGeneratorWizard
        super().__init__(*args, **kwargs)
        self._build_status_field(ct)
        self.instance.ct = ct
        self.fields['source'].initial = first_managed_orga_id()

    # def save(self, *args, **kwargs):
    #     instance = super().save(*args, **kwargs)
    #
    #     target = self.cleaned_data['target']
    #     instance.billing_address = copy_or_create_address(
    #         target.billing_address,  owner=instance, name=_('Billing address'),
    #     )
    #     instance.shipping_address = copy_or_create_address(
    #         target.shipping_address, owner=instance, name=_('Shipping address'),
    #     )
    #
    #     instance.save()
    #
    #     return instance
