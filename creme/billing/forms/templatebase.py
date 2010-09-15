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

from django.forms import ChoiceField, IntegerField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import HiddenInput

from billing.forms.base import BaseEditForm
from billing.models import TemplateBase


class _TemplateBaseForm(BaseEditForm):
    status = ChoiceField(label=_(u'Status'), choices=())

    class Meta:
        model = TemplateBase
        exclude = BaseEditForm.Meta.exclude + ('number', 'ct', 'status_id')

    def _build_status_field(self, billing_ct):
        meta = billing_ct.model_class()._meta
        status_field = self.fields['status']

        status_field.label    = ugettext(u'Status of %s') % meta.verbose_name
        status_field.choices = [(status.id, unicode(status)) for status in meta.get_field('status').rel.to.objects.all()]

        return status_field

    def save(self):
        self.instance.status_id = self.cleaned_data['status']
        return super(_TemplateBaseForm, self).save()


class TemplateBaseEditForm(_TemplateBaseForm):
    def __init__(self, *args, **kwargs):
        super(TemplateBaseEditForm, self).__init__(*args, **kwargs)

        instance = self.instance

        status_field = self._build_status_field(instance.ct)
        status_field.initial = instance.status_id


class TemplateBaseCreateForm(_TemplateBaseForm):
    ct = IntegerField(widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super(TemplateBaseCreateForm, self).__init__(*args, **kwargs)
        self._build_status_field(ContentType.objects.get_for_id(kwargs['initial']['ct']))

    def save(self):
        self.instance.ct = ContentType.objects.get_for_id(self.cleaned_data['ct'])

        return super(TemplateBaseCreateForm, self).save()
