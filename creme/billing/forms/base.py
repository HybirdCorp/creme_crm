# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm, CremeEntityField, CremeDateField, GenericEntityField
from creme_core.forms.validators import validate_linkable_entity
from creme_core.utils import find_first

from persons.models import Organisation, Address, Contact

from billing.models import Line
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


class BaseEditForm(CremeEntityForm):
    source = CremeEntityField(label=_(u"Source organisation"), model=Organisation)
    target = GenericEntityField(label=_(u"Target organisation"), models=[Organisation, Contact]) #, required=True

    issuing_date    = CremeDateField(label=_(u"Issuing date"), required=False)
    expiration_date = CremeDateField(label=_(u"Expiration date"))

    blocks = CremeEntityForm.blocks.new(
                ('orga_n_address', _(u'Organisation'), ['source', 'target']),
            )

    class Meta:
        exclude = CremeEntityForm.Meta.exclude + ('billing_address', 'shipping_address')

    def __init__(self, *args, **kwargs):
        super(BaseEditForm, self).__init__(*args, **kwargs)
        self.issued_relation   = None
        self.received_relation = None
        self.old_user_id = self.instance.user_id

        pk = self.instance.pk

        if pk is not None: #edit mode
            relations = Relation.objects.filter(subject_entity=pk, type__in=(REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED))

            issued_relation   = find_first(relations, (lambda r: r.type_id == REL_SUB_BILL_ISSUED), None)
            received_relation = find_first(relations, (lambda r: r.type_id == REL_SUB_BILL_RECEIVED), None)

            if issued_relation:
                self.issued_relation = issued_relation
                self.fields['source'].initial = issued_relation.object_entity_id

            if received_relation:
                self.received_relation = received_relation
                self.fields['target'].initial = received_relation.object_entity

    def clean_source(self):
        return validate_linkable_entity(self.cleaned_data['source'], self.user)

    def clean_target(self):
        return validate_linkable_entity(self.cleaned_data['target'], self.user)

    def clean(self):
        cleaned_data = self.cleaned_data

        if cleaned_data.get('discount') > 100:
            raise ValidationError(ugettext(u"Your discount is a %. It must be between 1 and 100%"))

        return cleaned_data

    def save(self):
        instance = self.instance

        cleaned_data = self.cleaned_data
        source = cleaned_data['source']
        target = cleaned_data['target']
        user   = cleaned_data['user']

        payment_info = instance.payment_info
        org_payment_info = payment_info.get_related_entity() if payment_info else None

        if source != org_payment_info:
            instance.payment_info = None

        instance = super(BaseEditForm, self).save()

        if self.issued_relation:
            self.issued_relation.update_links(object_entity=source, save=True)
        else:
            Relation.objects.create(subject_entity=instance,
                                    type_id=REL_SUB_BILL_ISSUED,
                                    object_entity=source,
                                    user=user
                                   )

        if self.received_relation:
            self.received_relation.update_links(object_entity=target, save=True)
        else:
            Relation.objects.create(subject_entity=instance,
                                    type_id=REL_SUB_BILL_RECEIVED,
                                    object_entity=target,
                                    user=user
                                   )

        #TODO: do this in model/with signal to avoid errors ???
        if self.old_user_id and self.old_user_id != user.id:
            #do not use queryset.update() to call the CremeEntity.save() method TODO: change with future Credentials system ??
            for line in instance.get_lines(Line):
                line.user = instance.user
                line.save()

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
        instance = self.instance
        cleaned_data = self.cleaned_data
        source = cleaned_data['source']
        target = cleaned_data['target']
        save_target = False

        if not target.shipping_address:
            name = ugettext(u'Shipping address')
            target.shipping_address = Address.objects.create(name=name, owner=target, address=name)
            save_target = True

        if not target.billing_address:
            name = ugettext(u'Billing address')
            target.billing_address = Address.objects.create(name=name, owner=target, address=name)
            save_target = True

        if save_target:
            target.save()

        instance.billing_address  = target.billing_address
        instance.shipping_address = target.shipping_address

        if instance.generate_number_in_create:
            instance.generate_number(source)

        return super(BaseCreateForm, self).save()
