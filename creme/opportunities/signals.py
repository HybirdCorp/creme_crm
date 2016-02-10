# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from django.apps import apps


logger = logging.getLogger(__name__)


if apps.is_installed('creme.billing'):
    from django.db.models import Sum
    from django.db.models.signals import post_save, post_delete
    from django.dispatch import receiver

    from creme.creme_core.models import SettingValue, Relation

    from creme.billing import get_quote_model

    from .constants import SETTING_USE_CURRENT_QUOTE, REL_SUB_CURRENT_DOC

    Quote = get_quote_model()

    def update_sales(opp):
        quotes = Quote.objects.filter(id__in=opp.get_current_quote_ids(),
                                      total_no_vat__isnull=False,
                                     )
        opp.estimated_sales = quotes.aggregate(Sum('total_no_vat'))['total_no_vat__sum'] or 0
        opp.made_sales      = quotes.filter(status__won=True) \
                                    .aggregate(Sum('total_no_vat'))['total_no_vat__sum'] or 0
        opp.save()

    def use_current_quote():
        try:
            use_current_quote = SettingValue.objects.get(key_id=SETTING_USE_CURRENT_QUOTE).value
        except SettingValue.DoesNotExist:
            logger.critical("Populate for opportunities has not been run !")
            use_current_quote = False

        return use_current_quote

    # Adding "current" feature to other billing document (sales order, invoice) does not really make sense.
    # If one day it does we will only have to add senders to the signal
    @receiver(post_save, sender=Quote)
    def _handle_current_quote_change(sender, instance, created, **kwargs):
        if not created and use_current_quote():
            relations = instance.get_relations(REL_SUB_CURRENT_DOC, real_obj_entities=True)

            if relations:  # TODO: useless
                for r in relations:
                    update_sales(r.object_entity.get_real_entity())

    @receiver((post_save, post_delete), sender=Relation)
    def _handle_current_quote_set(sender, instance, **kwargs):
        if instance.type_id == REL_SUB_CURRENT_DOC:
            doc = instance.subject_entity.get_real_entity()

            if isinstance(doc, Quote) and use_current_quote():
                update_sales(instance.object_entity.get_real_entity())
