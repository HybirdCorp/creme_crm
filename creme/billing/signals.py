################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from collections import defaultdict

# from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import signals
from django.db.transaction import atomic
from django.dispatch import receiver

import creme.creme_core.signals as core_signals
from creme import billing, persons
# from creme.persons import workflow
from creme.creme_core.models import Relation
from creme.creme_core.models.utils import assign_2_charfield

from . import constants
from .core.number_generation import number_generator_registry
# from .models import ConfigBillingAlgo, SimpleBillingAlgo
from .models import Base, NumberGeneratorItem

Organisation = persons.get_organisation_model()

Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()


# @receiver(signals.post_save, sender=Organisation)
# def set_simple_conf_billing(sender, instance, **kwargs):
#     if not instance.is_managed:
#         return
#
#     if ConfigBillingAlgo.objects.filter(organisation=instance).exists():
#         return
#
#     get_ct = ContentType.objects.get_for_model
#     for model, prefix in [
#         (Quote,                           settings.QUOTE_NUMBER_PREFIX),
#         (Invoice,                         settings.INVOICE_NUMBER_PREFIX),
#         (billing.get_sales_order_model(), settings.SALESORDER_NUMBER_PREFIX),
#     ]:
#         ct = get_ct(model)
#         ConfigBillingAlgo.objects.create(
#             organisation=instance, ct=ct, name_algo=SimpleBillingAlgo.ALGO_NAME,
#         )
#         SimpleBillingAlgo.objects.create(
#             organisation=instance, last_number=0, prefix=prefix, ct=ct,
#         )
@receiver(
    signals.post_save,
    sender=Organisation, dispatch_uid='billing-init_number_generation_config',
)
def init_number_generation_config(sender, instance, **kwargs):
    if not instance.is_managed:
        return

    # TODO: regroup queries?
    for model, generator_cls in number_generator_registry.registered_items():
        generator_cls.create_default_item(organisation=instance, model=model)


# NB: <sender=Base> does not work (no signal is emitted).
@receiver(signals.pre_save, dispatch_uid='billing-generate_number')
def generate_number(sender, instance, **kwargs):
    if (
        instance.pk is None
        and isinstance(instance, Base)
        and instance.generate_number_in_create
        and not instance.number
    ):
        if item := NumberGeneratorItem.objects.get_for_instance(instance):
            if gen := number_generator_registry.get(item):
                # TODO: log if too long?
                assign_2_charfield(instance, field_name='number', value=gen.perform())


@receiver(core_signals.pre_merge_related, dispatch_uid='billing-merge_number_configuration')
def handle_merge_organisations(sender, other_entity, **kwargs):
    # TODO: change 'pre_merge_related' to have sender=Organisation & arguments "entity1/entity2"
    #       (& so write '@receiver(core_signals.pre_merge_related, sender=Organisation)' )
    if not isinstance(sender, Organisation):
        return

    # orga_2_clean = None  # 'cache'
    #
    # def get_orga_2_clean():
    #     return sender if not sender.is_managed and other_entity.is_managed else other_entity
    #
    # for model in (ConfigBillingAlgo, SimpleBillingAlgo):
    #     model_filter = model.objects.filter
    #     orga_ids = {
    #         *model_filter(
    #             organisation__in=(sender, other_entity),
    #         ).values_list('organisation', flat=True),
    #     }
    #
    #     if len(orga_ids) == 2:
    #         orga_2_clean = orga_2_clean or get_orga_2_clean()
    #         model_filter(organisation=orga_2_clean).delete()
    #     else:
    #         return  # We avoid the queries for the next model (if it's the first iteration)
    gen_items = defaultdict(list)
    for gen_item in NumberGeneratorItem.objects.filter(
        organisation__in=[sender, other_entity],
    ):
        gen_items[gen_item.numbered_type_id].append(gen_item)

    ids_2_del = []
    for ct_items in gen_items.values():
        if len(ct_items) == 2:
            ids_2_del.extend(
                gen_item.id
                for gen_item in ct_items
                if gen_item.organisation_id == other_entity.id
            )

    if ids_2_del:
        NumberGeneratorItem.objects.filter(id__in=ids_2_del).delete()


STATUSES_REPLACEMENTS = {
    billing.get_credit_note_model(): 'status',
    Invoice:                         'status',
    Quote:                           'status',
    billing.get_sales_order_model(): 'status',
}


@receiver(core_signals.pre_replace_and_delete, dispatch_uid='billing-replace_template_status')
def handle_replace_statuses(sender, model_field, replacing_instance, **kwargs):
    model = model_field.model

    if STATUSES_REPLACEMENTS.get(model) == model_field.name:
        tpl_mngr = billing.get_template_base_model().objects

        for pk in tpl_mngr.filter(
            # status_id=sender.pk,
            status_uuid=sender.uuid,
            ct=ContentType.objects.get_for_model(model),
        ).values_list('pk', flat=True):
            # NB1: we perform a .save(), not an .update() in order to:
            #       - let the model compute it's business logic (if there is one).
            #       - get a HistoryLine for entities.
            # NB2: as in edition view, we perform a select_for_update() to avoid
            #      overriding other fields (if there are concurrent accesses)
            with atomic():
                tpl = tpl_mngr.select_for_update().filter(pk=pk).first()
                # tpl.status_id = replacing_instance.id
                tpl.status_uuid = replacing_instance.uuid
                tpl.save()


@receiver(
    (signals.post_save, signals.post_delete),
    sender=Relation, dispatch_uid='billing-manage_linked_credit_notes',
)
def manage_linked_credit_notes(sender, instance, **kwargs):
    "The calculated totals of Invoices have to be refreshed."
    if instance.type_id == constants.REL_SUB_CREDIT_NOTE_APPLIED:
        instance.real_object.save()


# TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
@receiver(signals.post_delete, sender=Relation, dispatch_uid='billing-manage_line_deletion')
def manage_line_deletion(sender, instance, **kwargs):
    "The calculated totals (Invoice, Quote...) have to be refreshed."
    # if instance.type_id == constants.REL_OBJ_HAS_LINE:
    #     instance.real_object.save()
    if (
        instance.type_id == constants.REL_SUB_HAS_LINE
        # NB: see billing.models.base.Base._pre_delete() for this ugly hack
        and not getattr(instance, '_avoid_billing_total_update', False)
    ):
        instance.subject_entity.get_real_entity().save()


# _WORKFLOWS = {
#     Invoice: workflow.transform_target_into_customer,
#     Quote:   workflow.transform_target_into_prospect,
# }
#
#
# # NB: in Base.save(), target relationship is created after source relationships,
# #     so we trigger this code target relationship creation, as the source should be OK too.
# @receiver(signals.post_save, sender=Relation, dispatch_uid='billing-manage_workflows')
# def manage_creation_workflows(sender, instance, **kwargs):
#     if instance.type_id == constants.REL_SUB_BILL_RECEIVED:
#         billing_doc = instance.subject_entity
#         workflow_func = _WORKFLOWS.get(type(billing_doc))
#
#         if workflow_func:
#             workflow_func(
#                 source=billing_doc.source,
#                 target=instance.object_entity,
#                 user=instance.user,
#             )
