################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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

from django import forms
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.base import CremeModelForm

from ..models import PaymentInformation


class _PaymentInformationForm(CremeModelForm):
    class Meta:
        model = PaymentInformation
        exclude = ('organisation', )

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity = entity


class PaymentInformationEditionForm(_PaymentInformationForm):
    is_archived = forms.BooleanField(
        label=_('Is archived'), required=False,
        help_text=_(
            'An archived account can not be selected anymore to be the account '
            'used by billing documents (it does not affect documents which already use it)'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_default:
            fields = self.fields
            del fields['is_default']
            del fields['is_archived']

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            if cdata.get('is_archived') and (
                cdata.get('is_default') or self.instance.is_default
            ):
                self.add_error(
                    field='is_archived',
                    error=gettext('You cannot archive the default account'),
                )

        return cdata

    def save(self, *args, **kwargs):
        self.instance.archived = now() if self.cleaned_data.get('is_archived') else None

        return super().save(*args, **kwargs)


class PaymentInformationCreationForm(_PaymentInformationForm):
    def save(self, *args, **kwargs):
        self.instance.organisation = self.entity
        return super().save(*args, **kwargs)
