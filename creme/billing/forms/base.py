# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from itertools import chain
import logging

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import (CremeEntityForm,
        GenericEntityField, CreatorEntityField)
from creme.creme_core.forms.validators import validate_linkable_entity
from creme.creme_core.models import Relation
from creme.creme_core.utils import find_first

from creme.persons import get_contact_model, get_organisation_model, get_address_model

from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED


logger = logging.getLogger(__name__)


# TODO: move to persons ??
def copy_or_create_address(address, owner, name):
    if address is None:
        name = unicode(name)
        return get_address_model().objects.create(name=name, owner=owner, address=name)

    return address.clone(owner)


def first_managed_orga_id():
    try:
        return get_organisation_model().get_all_managed_by_creme().values_list('id', flat=True)[0]
    except IndexError:
        logger.warn('No managed organisation ?!')


class BaseEditForm(CremeEntityForm):
    source = CreatorEntityField(label=_(u"Source organisation"), model=get_organisation_model())
    target = GenericEntityField(label=_(u"Target"),
                                models=[get_organisation_model(), get_contact_model()],
                               )

#    issuing_date    = CremeDateField(label=_(u"Issuing date"), required=False)
#    expiration_date = CremeDateField(label=_(u"Expiration date"), required=False)

    class Meta(CremeEntityForm.Meta):
        labels = {
                'discount': _(u'Overall discount (in %)'),
            }

    blocks = CremeEntityForm.blocks.new(
                ('orga_n_address', _(u'Organisations'), ['source', 'target']), #TODO: rename
            )

    def __init__(self, *args, **kwargs):
        super(BaseEditForm, self).__init__(*args, **kwargs)
        self.issued_relation   = None
        self.received_relation = None
        self.old_user_id = self.instance.user_id

        pk = self.instance.pk

        if pk is not None:  # Edit mode
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

    def save(self, *args, **kwargs):
        instance = self.instance

        cleaned_data = self.cleaned_data
        source = cleaned_data['source']
        target = cleaned_data['target']
        user   = cleaned_data['user']

        payment_info = instance.payment_info
        org_payment_info = payment_info.get_related_entity() if payment_info else None

        if source != org_payment_info:
            instance.payment_info = None

        instance = super(BaseEditForm, self).save(*args, **kwargs)

        self._manage_relation(self.issued_relation, REL_SUB_BILL_ISSUED, source)  # TODO: move this intelligence in models.Base.save()
        self._manage_relation(self.received_relation, REL_SUB_BILL_RECEIVED, target)

        # TODO: do this in model/with signal to avoid errors ???
        if self.old_user_id and self.old_user_id != user.id:
            # Do not use queryset.update() to call the CremeEntity.save() method TODO: change with future Credentials system ??
            # TODO: we need a way to retrieve all lines with potential other types...
            for line in chain(instance.product_lines, instance.service_lines):
                line.user = instance.user
                line.save()

        return instance


class BaseCreateForm(BaseEditForm):
    def __init__(self, *args, **kwargs):
        super(BaseCreateForm, self).__init__(*args, **kwargs)

        self.fields['source'].initial = first_managed_orga_id()

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
