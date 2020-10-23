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

import logging

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.forms import (
    CreatorEntityField,
    CremeEntityForm,
    GenericEntityField,
)
# from creme.creme_core.models import Relation
# from creme.creme_core.utils import find_first
# from creme.persons import get_address_model
from creme.persons import get_contact_model, get_organisation_model

# from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
# from ..models import PaymentInformation

logger = logging.getLogger(__name__)


# def copy_or_create_address(address, owner, name):
#     if address is None:
#         name = str(name)
#         return get_address_model().objects.create(name=name, owner=owner, address=name)
#
#     return address.clone(owner)


def first_managed_orga_id():
    try:
        return get_organisation_model().objects.filter_managed_by_creme().values_list(
            'id', flat=True,
        )[0]
    except IndexError:
        logger.warning('No managed organisation ?!')


class BaseEditForm(CremeEntityForm):
    source = CreatorEntityField(
        label=pgettext_lazy('billing', 'Source organisation'),
        model=get_organisation_model(),
    )
    target = GenericEntityField(
        label=pgettext_lazy('billing', 'Target'),
        models=[get_organisation_model(), get_contact_model()],
    )

    class Meta(CremeEntityForm.Meta):
        labels = {
            'discount': _('Overall discount (in %)'),
        }

    blocks = CremeEntityForm.blocks.new(
        # TODO: rename (beware to template)
        ('orga_n_address', _('Organisations'), ['source', 'target']),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.issued_relation   = None
        # self.received_relation = None
        instance = self.instance
        self.old_user_id = instance.user_id

        pk = instance.pk

        if pk is not None:  # Edit mode
            # relations = Relation.objects.filter(
            #     subject_entity=pk, type__in=(REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED),
            # )
            #
            # issued_relation = find_first(
            #     relations,
            #     (lambda r: r.type_id == REL_SUB_BILL_ISSUED),
            #     None
            # )
            # received_relation = find_first(
            #     relations,
            #     (lambda r: r.type_id == REL_SUB_BILL_RECEIVED),
            #     None
            # )
            #
            # if issued_relation:
            #     self.issued_relation = issued_relation
            #     self.fields['source'].initial = issued_relation.object_entity_id
            #
            # if received_relation:
            #     self.received_relation = received_relation
            #     self.fields['target'].initial = received_relation.object_entity
            fields = self.fields
            fields['source'].initial = instance.source.id
            fields['target'].initial = instance.target

    # def _manage_relation(self, existing_relation, type_id, related_entity):
    #     if existing_relation:
    #         if related_entity.id != existing_relation.object_entity_id:
    #             existing_relation.delete()
    #             existing_relation = None
    #
    #     if not existing_relation:
    #         instance = self.instance
    #         Relation.objects.safe_create(
    #             subject_entity=instance,
    #             type_id=type_id,
    #             object_entity=related_entity,
    #             user=instance.user,
    #         )

    def clean_source(self):
        self.instance.source = source = self.cleaned_data['source']

        return source

    def clean_target(self):
        self.instance.target = target = self.cleaned_data['target']

        return target

    def save(self, *args, **kwargs):
        # instance = self.instance

        cleaned_data = self.cleaned_data
        # source = cleaned_data['source']
        # target = cleaned_data['target']

        # payment_info = instance.payment_info
        # pinfo_orga_id = payment_info.organisation_id if payment_info else None
        #
        # if source.id != pinfo_orga_id:
        #     instance.payment_info = None
        #
        # if instance.payment_info is None:  # Optimization
        #     source_pis = PaymentInformation.objects.filter(organisation=source.id)[:2]
        #     if len(source_pis) == 1:
        #         instance.payment_info = source_pis[0]

        instance = super().save(*args, **kwargs)

        # self._manage_relation(self.issued_relation, REL_SUB_BILL_ISSUED, source)
        # self._manage_relation(self.received_relation, REL_SUB_BILL_RECEIVED, target)

        # TODO: do this in model/with signal to avoid errors ???
        if self.old_user_id and self.old_user_id != cleaned_data['user'].id:
            # Do not use queryset.update() to call the CremeEntity.save() method
            #  TODO: change with future Credentials system ??
            for line in instance.iter_all_lines():
                line.user = instance.user
                line.save()

        return instance


class BaseCreateForm(BaseEditForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.fields['source'].initial = first_managed_orga_id()
        try:
            managed_orga = get_organisation_model().objects.filter_managed_by_creme()[0]
        except IndexError:
            logger.warning('No managed organisation ?!')
        else:
            fields = self.fields
            fields['source'].initial = managed_orga

            if type(self.instance).generate_number_in_create:
                fields['number'].help_text = _(
                    'If you chose an organisation managed by Creme (like «{}») '
                    'as source organisation, a number will be automatically generated.'
                ).format(managed_orga)

    # def save(self, *args, **kwargs):
    #     instance = self.instance
    #     cleaned_data = self.cleaned_data
    #     target = cleaned_data['target']
    #
    #     if instance.generate_number_in_create:
    #         instance.generate_number(cleaned_data['source'])
    #
    #     super().save(*args, **kwargs)
    #
    #     instance.billing_address = copy_or_create_address(
    #         target.billing_address, owner=instance, name=_('Billing address'),
    #     )
    #     instance.shipping_address = copy_or_create_address(
    #         target.shipping_address, owner=instance, name=_('Shipping address'),
    #     )
    #
    #     instance.save()
    #
    #     return instance
