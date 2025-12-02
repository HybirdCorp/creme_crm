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

from django.contrib.contenttypes.models import ContentType
from django.db.models import signals
from django.db.transaction import atomic
from django.dispatch import receiver

import creme.creme_core.signals as core_signals
from creme import billing, persons
from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.models import Relation
from creme.creme_core.models.utils import assign_2_charfield

from . import constants
from .core.number_generation import number_generator_registry
from .models import Base, NumberGeneratorItem

Organisation = persons.get_organisation_model()

Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()


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


# NB1: we keep the owner of Lines synchronised with the owner of the related
#      Invoice/Quotes/SalesOrder/..., in order to credentials are relatively
#      accurate. It's not perfect, permission management of auxiliary entities
#      is still not correctly designed...
# NB2: <sender=Base> does not work (no signal is emitted).
@receiver(signals.post_save, dispatch_uid='billing-sync_line_user')
def sync_line_user(sender, instance, created, **kwargs):
    if not issubclass(sender, Base):
        # Line are only related to CremeEntities inheriting Base
        return

    if created:
        # No Line exist juste after the creation
        return

    snapshot = Snapshot.get_for_instance(instance)
    if snapshot is None:
        # Instance has been created & modified in the same request;
        # we assume no Line is created in the same request AND needs to update
        # its owner (the user field would have been modified after the
        # Lines have been created => ewwwww...)
        return

    for diff in snapshot.compare(instance):
        if diff.field_name == 'user_id':
            new_user_id = diff.new_value

            # TODO: change with future Credentials system?
            for line in instance.iter_all_lines():
                line.user_id = new_user_id
                # We do not use queryset.update() to call the CremeEntity.save() method
                line.save()

            return


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
        wf_engine = WorkflowEngine.get_current()

        for pk in tpl_mngr.filter(
            status_uuid=sender.uuid,
            ct=ContentType.objects.get_for_model(model),
        ).values_list('pk', flat=True):
            # NB1: we perform a .save(), not an .update() in order to:
            #       - let the model compute it's business logic (if there is one).
            #       - get a HistoryLine for entities.
            # NB2: as in edition view, we perform a select_for_update() to avoid
            #      overriding other fields (if there are concurrent accesses)
            with atomic(), wf_engine.run(user=None):
                tpl = tpl_mngr.select_for_update().filter(pk=pk).first()
                tpl.status_uuid = replacing_instance.uuid
                tpl.save()


@receiver(
    (signals.post_save, signals.post_delete),
    sender=Relation, dispatch_uid='billing-manage_linked_credit_notes',
)
def manage_linked_credit_notes(sender, instance, **kwargs):
    "The calculated totals of Invoices have to be refreshed."
    if (
        instance.type_id == constants.REL_SUB_CREDIT_NOTE_APPLIED
        # NB:
        #  - <created is None> means deletion
        #  - <instance.symmetric_relation is None> means the relation will
        #     be saved again when completed, so we avoid a useless total computing
        and (kwargs.get('created') is None or instance.symmetric_relation is not None)
    ):
        instance.real_object.save()


# TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
@receiver(signals.post_delete, sender=Relation, dispatch_uid='billing-manage_line_deletion')
def manage_line_deletion(sender, instance, **kwargs):
    "The calculated totals (Invoice, Quote...) have to be refreshed."
    if (
        instance.type_id == constants.REL_SUB_HAS_LINE
        # NB: see billing.models.base.Base._pre_delete() for this ugly hack
        and not getattr(instance, '_avoid_billing_total_update', False)
    ):
        instance.subject_entity.get_real_entity().save()
