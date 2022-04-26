# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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
from django.db.models import signals
from django.db.transaction import atomic
from django.dispatch import receiver

from creme import billing, persons
from creme.creme_core import signals as core_signals
from creme.creme_core.models import Relation
from creme.persons import workflow

from . import constants
from .models import ConfigBillingAlgo, SimpleBillingAlgo

Organisation = persons.get_organisation_model()

Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()


@receiver(signals.post_save, sender=Organisation)
def set_simple_conf_billing(sender, instance, **kwargs):
    if not instance.is_managed:
        return

    if ConfigBillingAlgo.objects.filter(organisation=instance).exists():
        return

    get_ct = ContentType.objects.get_for_model

    for model, prefix in [
        (Quote,                           settings.QUOTE_NUMBER_PREFIX),
        (Invoice,                         settings.INVOICE_NUMBER_PREFIX),
        (billing.get_sales_order_model(), settings.SALESORDER_NUMBER_PREFIX),
    ]:
        ct = get_ct(model)
        ConfigBillingAlgo.objects.create(
            organisation=instance, ct=ct, name_algo=SimpleBillingAlgo.ALGO_NAME,
        )
        SimpleBillingAlgo.objects.create(
            organisation=instance, last_number=0, prefix=prefix, ct=ct,
        )


@receiver(core_signals.pre_merge_related)
def handle_merge_organisations(sender, other_entity, **kwargs):
    # TODO: change 'pre_merge_related' to have sender=Organisation & arguments "entity1/entity2"
    #       (& so write '@receiver(core_signals.pre_merge_related, sender=Organisation)' )
    if not isinstance(sender, Organisation):
        return

    # NB: we assume that all CTs are covered if at least one CT is covered
    #     because ConfigBillingAlgo/SimpleBillingAlgo instances are only
    #     created in _simple_conf_billing_for_org_managed_by_creme().
    orga_2_clean = None  # 'cache'

    def get_orga_2_clean():
        return sender if not sender.is_managed and other_entity.is_managed else other_entity

    for model in (ConfigBillingAlgo, SimpleBillingAlgo):
        model_filter = model.objects.filter
        orga_ids = {
            *model_filter(
                organisation__in=(sender, other_entity),
            ).values_list('organisation', flat=True),
        }

        if len(orga_ids) == 2:
            orga_2_clean = orga_2_clean or get_orga_2_clean()
            model_filter(organisation=orga_2_clean).delete()
        else:
            return  # We avoid the queries for the next model (if it's the first iteration)


STATUSES_REPLACEMENTS = {
    billing.get_credit_note_model(): 'status',
    Invoice:                         'status',
    billing.get_quote_model():       'status',
    billing.get_sales_order_model(): 'status',
}


@receiver(core_signals.pre_replace_and_delete)
def handle_replace_statuses(sender, model_field, replacing_instance, **kwargs):
    model = model_field.model

    if STATUSES_REPLACEMENTS.get(model) == model_field.name:
        tpl_mngr = billing.get_template_base_model().objects

        for pk in tpl_mngr.filter(
            status_id=sender.pk,
            ct=ContentType.objects.get_for_model(model),
        ).values_list('pk', flat=True):
            # NB1: we perform a .save(), not an .update() in order to:
            #       - let the model compute it's business logic (if there is one).
            #       - get an HistoryLine for entities.
            # NB2: as in edition view, we perform a select_for_update() to avoid
            #      overriding other fields (if there are concurrent accesses)
            with atomic():
                tpl = tpl_mngr.select_for_update().filter(pk=pk).first()
                tpl.status_id = replacing_instance.id
                tpl.save()


@receiver((signals.post_save, signals.post_delete), sender=Relation)
def manage_linked_credit_notes(sender, instance, **kwargs):
    "The calculated totals of Invoices have to be refreshed."
    if instance.type_id == constants.REL_SUB_CREDIT_NOTE_APPLIED:
        instance.object_entity.get_real_entity().save()


# TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
@receiver(signals.post_delete, sender=Relation)
def manage_line_deletion(sender, instance, **kwargs):
    "The calculated totals (Invoice, Quote...) have to be refreshed."
    if instance.type_id == constants.REL_OBJ_HAS_LINE:
        instance.object_entity.get_real_entity().save()


_WORKFLOWS = {
    Invoice: workflow.transform_target_into_customer,
    Quote: workflow.transform_target_into_prospect,
}


# NB: in Base.save(), target relationship is created after source relationships
#     so we trigger this code target relationship creation, as the source should be OK too.
@receiver(signals.post_save, sender=Relation)
def manage_creation_workflows(sender, instance, **kwargs):
    if instance.type_id == constants.REL_SUB_BILL_RECEIVED:
        billing_doc = instance.subject_entity
        workflow_func = _WORKFLOWS.get(type(billing_doc))

        if workflow_func:
            workflow_func(
                source=billing_doc.source,
                target=instance.object_entity,
                user=instance.user,
            )
