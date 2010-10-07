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

from logging import debug

from django.forms import DateField, CharField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm, CremeEntityField, CremeDateField

from persons.models.organisation import Organisation, Address

from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


class BaseEditForm(CremeEntityForm):
    source = CremeEntityField(label=_(u"Source organisation"), model=Organisation)
    target = CremeEntityField(label=_(u"Target organisation"), model=Organisation)

    issuing_date    = CremeDateField(label=_(u"Issuing date"), required=False)
    expiration_date = CremeDateField(label=_(u"Expiration date"))

    blocks = CremeEntityForm.blocks.new(
                ('orga_n_address', _(u'Organisation'), ['source', 'target']),
            )

    class Meta:
        exclude = CremeEntityForm.Meta.exclude + ('billing_address', 'shipping_address')

    def __init__(self, *args, **kwargs):
        super(BaseEditForm, self).__init__(*args, **kwargs)

        pk = self.instance.pk

        if pk is not None: #edit mode
            #TODO: regroup queries ??
            get_relation = Relation.objects.get
            fields = self.fields
            fields['source'].initial = get_relation(subject_entity=pk, type=REL_SUB_BILL_ISSUED).object_entity_id #value_list(object_entity_id) ???
            fields['target'].initial = get_relation(subject_entity=pk, type=REL_SUB_BILL_RECEIVED).object_entity_id

    def save(self):
        instance = super(BaseEditForm, self).save()

        cleaned_data = self.cleaned_data
        create_relation = Relation.create
        source = cleaned_data['source']
        target = cleaned_data['target']

        Relation.objects.filter(subject_entity=instance, type__in=(REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED)).delete()
        create_relation(instance, REL_SUB_BILL_ISSUED,   source)
        create_relation(instance, REL_SUB_BILL_RECEIVED, target)

        return instance


class BaseCreateForm(BaseEditForm):
    class Meta:
        exclude = BaseEditForm.Meta.exclude

    def __init__(self, *args, **kwargs):
        super(BaseCreateForm, self).__init__(*args, **kwargs)

        try:
            self.fields['source'].initial = Organisation.get_all_managed_by_creme().values_list('id', flat=True)[0] #[:1][0] ??
        except IndexError, e:
            debug('Exception in %s.__init__: %s', self.__class__, e)

    def save(self):
        instance = super(BaseCreateForm, self).save() #TODO: force_insert ??? (avoid saving twice)

        cleaned_data  = self.cleaned_data
        source = cleaned_data['source']
        target = cleaned_data['target']

        if not target.shipping_address :
            name = ugettext(u'Shipping address')
            target.shipping_address = Address.objects.create(name=name, owner=target, address=name)
            target.save()

        if not target.billing_address:
            name = ugettext(u'Billing address')
            target.billing_address = Address.objects.create(name=name, owner=target, address=name)
            target.save()

        instance.billing_address  = target.billing_address
        instance.shipping_address = target.shipping_address

        if instance.generate_number_in_create:
            instance.generate_number()

        instance.save()

        return instance
