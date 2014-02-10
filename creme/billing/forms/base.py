# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import Relation # Currency
from creme.creme_core.forms import (CremeEntityForm, CremeDateField,
                                    GenericEntityField, CreatorEntityField)
from creme.creme_core.forms.validators import validate_linkable_entity
from creme.creme_core.utils import find_first
#from creme.creme_core.constants import DEFAULT_CURRENCY_PK

#from creme.creme_config.forms.fields import CreatorModelChoiceField

from creme.persons.models import Organisation, Address, Contact

from ..models import Line # AdditionalInformation, PaymentTerms
from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


logger = logging.getLogger(__name__)


#TODO: move to persons ??
def copy_or_create_address(address, owner, name):
    if address is None:
        name = unicode(name)
        return Address.objects.create(name=name, owner=owner, address=name)

    return address.clone(owner)


class BaseEditForm(CremeEntityForm):
    #currency = CreatorModelChoiceField(label=_(u'Currency'), queryset=Currency.objects.all(), initial=DEFAULT_CURRENCY_PK)

    #additional_info  = CreatorModelChoiceField(label=_(u'Additional Information'), queryset=AdditionalInformation.objects.all(), required=False, initial=None)
    #payment_terms    = CreatorModelChoiceField(label=_(u'Payment Terms'), queryset=PaymentTerms.objects.all(), required=False, initial=None)

    source = CreatorEntityField(label=_(u"Source organisation"), model=Organisation)
    target = GenericEntityField(label=_(u"Target"), models=[Organisation, Contact]) #, required=True

    issuing_date    = CremeDateField(label=_(u"Issuing date"), required=False)
    expiration_date = CremeDateField(label=_(u"Expiration date"), required=False)

    blocks = CremeEntityForm.blocks.new(
                ('orga_n_address', _(u'Organisations'), ['source', 'target']),
            )

    class Meta:
        exclude = CremeEntityForm.Meta.exclude + ('billing_address', 'shipping_address')

    def __init__(self, *args, **kwargs):
        super(BaseEditForm, self).__init__(*args, **kwargs)
        self.issued_relation   = None
        self.received_relation = None
        self.old_user_id = self.instance.user_id

        #user = self.user
        #self.fields['currency'].user = user
        #self.fields['additional_info'].user = user
        #self.fields['payment_terms'].user = user
        #self.fields['source'].user = user

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
        cleaned_data = super(BaseEditForm, self).clean()

        if cleaned_data.get('discount') > 100:
            raise ValidationError(ugettext(u"Your discount is a %. It must be between 1 and 100%"))

        return cleaned_data

    def _manage_relation(self, existing_relation, type_id, related_entity):
        if existing_relation:
            if related_entity.id != existing_relation.object_entity_id:
                existing_relation.delete()
                existing_relation = None

        if not existing_relation:
            instance = self.instance
            Relation.objects.create(subject_entity=instance,
                                    type_id=type_id,
                                    object_entity=related_entity,
                                    user=instance.user,
                                   )

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

        #if self.issued_relation:
            #self.issued_relation.update_links(object_entity=source, save=True)
        #else:
            #Relation.objects.create(subject_entity=instance,
                                    #type_id=REL_SUB_BILL_ISSUED,
                                    #object_entity=source,
                                    #user=user
                                   #)
        self._manage_relation(self.issued_relation, REL_SUB_BILL_ISSUED, source) #TODO: move this intelligence in models.Base.save()

        #if self.received_relation:
            #self.received_relation.update_links(object_entity=target, save=True)
        #else:
            #Relation.objects.create(subject_entity=instance,
                                    #type_id=REL_SUB_BILL_RECEIVED,
                                    #object_entity=target,
                                    #user=user
                                   #)
        self._manage_relation(self.received_relation, REL_SUB_BILL_RECEIVED, target)

        #TODO: do this in model/with signal to avoid errors ???
        if self.old_user_id and self.old_user_id != user.id:
            #do not use queryset.update() to call the CremeEntity.save() method TODO: change with future Credentials system ??
            for line in instance.get_lines(Line):
                line.user = instance.user
                line.save()

        return instance


class BaseCreateForm(BaseEditForm):
    #class Meta:
        #exclude = BaseEditForm.Meta.exclude

    def __init__(self, *args, **kwargs):
        super(BaseCreateForm, self).__init__(*args, **kwargs)

        try:
            self.fields['source'].initial = Organisation.get_all_managed_by_creme().values_list('id', flat=True)[0] #[:1][0] ??
        except IndexError as e:
            logger.debug('Exception in %s.__init__: %s', self.__class__, e)

    def save(self, *args, **kwargs):
        instance = self.instance
        cleaned_data = self.cleaned_data
        target = cleaned_data['target']

        if instance.generate_number_in_create:
            instance.generate_number(cleaned_data['source'])

        super(BaseCreateForm, self).save(*args, **kwargs)

        instance.billing_address  = copy_or_create_address(target.billing_address,  instance, _(u'Billing address'))
        instance.shipping_address = copy_or_create_address(target.shipping_address, instance, _(u'Shipping address'))

        instance.save()

        return instance
