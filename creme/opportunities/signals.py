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

from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from creme.creme_core.models import Relation

from . import constants

if apps.is_installed('creme.billing'):
    from django.db.models import Sum

    from creme.billing import get_quote_model
    from creme.creme_core.models import SettingValue

    from .setting_keys import quote_key

    Quote = get_quote_model()

    def update_sales(opp):
        quotes = Quote.objects.filter(
            id__in=opp.get_current_quote_ids(), total_no_vat__isnull=False,
        )
        opp.estimated_sales = quotes.aggregate(
            Sum('total_no_vat'),
        )['total_no_vat__sum'] or 0
        opp.made_sales = quotes.filter(
            status__won=True,
        ).aggregate(
            Sum('total_no_vat'),
        )['total_no_vat__sum'] or 0
        opp.save()

    def use_current_quote():
        return SettingValue.objects.get_4_key(quote_key, default=False).value

    # Adding "current" feature to other billing document (sales order, invoice)
    # does not really make sense.
    # If one day it does, we will only have to add senders to the signal.
    @receiver(post_save, sender=Quote, dispatch_uid='opportunities-manage_current_quote_edition')
    def _handle_current_quote_change(sender, instance, created, **kwargs):
        # NB: at creation Quote double-save() for its address;
        #     the second save() uses the argument <update_fields>.
        if not created and not kwargs.get('update_fields') and use_current_quote():
            for r in instance.get_relations(constants.REL_SUB_CURRENT_DOC, real_obj_entities=True):
                update_sales(r.real_object)

    @receiver(
        post_save, sender=Relation, dispatch_uid='opportunities-manage_current_quote_adding',
    )
    @receiver(
        post_delete, sender=Relation, dispatch_uid='opportunities-manage_current_quote_removing',
    )
    def _handle_current_quote_set(sender, instance, **kwargs):
        if (
            instance.type_id == constants.REL_SUB_CURRENT_DOC
            # NB:
            #  - <created is None> means deletion
            #  - <instance.symmetric_relation is None> means the relation will
            #     be saved again when completed, so we avoid a useless sales computing
            and (kwargs.get('created') is None or instance.symmetric_relation is not None)
        ):
            doc = instance.subject_entity.get_real_entity()

            if isinstance(doc, Quote) and use_current_quote():
                update_sales(instance.real_object)

    @receiver(
        post_delete, sender=Relation, dispatch_uid='opportunities-manage_related_quote_deletion',
    )
    def _handle_linked_quote_deletion(sender, instance, **kwargs):
        if instance.type_id == constants.REL_SUB_LINKED_QUOTE:
            for relation in Relation.objects.filter(
                subject_entity=instance.subject_entity_id,
                type_id=constants.REL_SUB_CURRENT_DOC,
                object_entity=instance.object_entity_id,
            ):
                relation.delete()
