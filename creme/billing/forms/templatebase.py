# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms import ModelChoiceField, IntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import HiddenInput

from billing.forms.base import BaseEditForm
from billing.models import TemplateBase, InvoiceStatus

#TODO: factorise these 2 forms...

class TemplateBaseEditForm(BaseEditForm):
    status = ModelChoiceField(queryset=InvoiceStatus.objects.none())

    def __init__(self, *args, **kwargs):
        super(TemplateBaseEditForm, self).__init__(*args, **kwargs)

        # Edit status
        ct = self.instance.ct
        self.fields['status'].label = _(u'Statut %s' % ct.model_class()._meta.verbose_name)
        status_class = ct.model_class()._meta.get_field('status').rel.to
        self.fields['status'].queryset = status_class.objects.all()
        self.fields['status'].initial = status_class.objects.get(pk = self.instance.status_id).id

    class Meta:
        model = TemplateBase
        exclude = BaseEditForm.exclude + ('number', 'ct', 'status_id')


class TemplateBaseCreateForm(BaseEditForm):
    status = ModelChoiceField(queryset=InvoiceStatus.objects.none())
    ct     = IntegerField(widget = HiddenInput())

    class Meta:
        model = TemplateBase
        exclude = BaseEditForm.exclude + ('number', 'status_id', 'ct')

    def __init__(self, *args, **kwargs):
        super(TemplateBaseCreateForm, self).__init__(*args, **kwargs)
        if kwargs['initial']:
            ct = ContentType.objects.get(pk = kwargs['initial']['ct']) #TODO: use get_for_id()
            self.fields['status'].label = _(u'Statut %s' % ct.model_class()._meta.verbose_name)
            status_class = ct.model_class()._meta.get_field('status').rel.to
            self.fields['status'].queryset = status_class.objects.all()

    def save(self):
        cleaned = self.cleaned_data
        self.instance.ct = ContentType.objects.get(pk = cleaned['ct'])
        self.instance.status_id = cleaned['status'].id
        super(TemplateBaseCreateForm, self).save()

