# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme.creme_core.models import Relation, CremeProperty
from creme.creme_core.signals import pre_merge_related

from creme.persons import get_organisation_model

from . import get_invoice_model, get_quote_model, get_sales_order_model
from .constants import REL_SUB_CREDIT_NOTE_APPLIED, REL_OBJ_HAS_LINE
from .models import ConfigBillingAlgo, SimpleBillingAlgo


@receiver(post_save, sender=CremeProperty)
def set_simple_conf_billing(sender, instance, created, **kwargs):
    if not created:
        return

    Invoice      = get_invoice_model()
    Quote        = get_quote_model()
    SalesOrder   = get_sales_order_model()

    get_ct = ContentType.objects.get_for_model

    if instance.type_id == PROP_IS_MANAGED_BY_CREME and \
       instance.creme_entity.entity_type_id == get_ct(get_organisation_model()).id:
        orga = instance.creme_entity.get_real_entity()

        if not ConfigBillingAlgo.objects.filter(organisation=orga):
            for model, prefix in [(Quote,      settings.QUOTE_NUMBER_PREFIX),
                                  (Invoice,    settings.INVOICE_NUMBER_PREFIX),
                                  (SalesOrder, settings.SALESORDER_NUMBER_PREFIX),
                                 ]:
                ct = get_ct(model)
                ConfigBillingAlgo.objects.create(organisation=orga, ct=ct,
                                                 name_algo=SimpleBillingAlgo.ALGO_NAME, 
                                                )
                SimpleBillingAlgo.objects.create(organisation=orga, last_number=0,
                                                 prefix=prefix, ct=ct,
                                                )

@receiver(pre_merge_related)
def handle_merge_organisations(sender, other_entity, **kwargs):
    # NB: we assume that all CTs are covered if at least one CT is covered
    #     because ConfigBillingAlgo/SimpleBillingAlgo instances are only
    #     created in _simple_conf_billing_for_org_managed_by_creme().
    orga_2_clean = None # 'cache'

    def get_orga_2_clean():
        managed_ids = set(CremeProperty.objects
                                       .filter(creme_entity__in=(sender.id, other_entity.id))
                                       .values_list('creme_entity', flat=True)
                         )

        return sender if len(managed_ids) == 1 and sender.id not in managed_ids else other_entity

    for model in (ConfigBillingAlgo, SimpleBillingAlgo):
        model_filter = model.objects.filter
        orga_ids = set(model_filter(organisation__in=(sender, other_entity))
                                    .values_list('organisation', flat=True)
                      )

        if len(orga_ids) == 2:
            orga_2_clean = orga_2_clean or get_orga_2_clean()
            model_filter(organisation=orga_2_clean).delete()
        else:
            return # we avoid the queries for the next model (if it's the first iteration)

@receiver((post_save, post_delete), sender=Relation)
def manage_linked_credit_notes(sender, instance, **kwargs):
    "the calculated totals of Invoices have to be refreshed."
    if instance.type_id == REL_SUB_CREDIT_NOTE_APPLIED:
        instance.object_entity.get_real_entity().save()

#TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
@receiver(post_delete, sender=Relation)
def manage_line_deletion(sender, instance, **kwargs):
    "The calculated totals (Invoice, Quote...) have to be refreshed"
    if instance.type_id == REL_OBJ_HAS_LINE:
        instance.object_entity.get_real_entity().save()
