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
from functools import partial
#import warnings

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.transaction import commit_on_success
from django.db.models import (CharField, TextField, ForeignKey, PositiveIntegerField,
                              DateField, PROTECT, SET_NULL, Sum, BooleanField)
from django.utils.translation import ugettext_lazy as _, ugettext
#from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CremeEntity, CremeModel, Relation, Currency, Vat
from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.core.function_field import FunctionField

from creme.persons.models import Contact, Organisation
from creme.persons.workflow import transform_target_into_prospect

from creme.products.models import Product, Service

#from creme.billing.models import Invoice, SalesOrder, Quote

from ..constants import *


logger = logging.getLogger(__name__)


class _TurnoverField(FunctionField):
    name         = "get_weighted_sales"
    verbose_name = _(u"Weighted sales")


class SalesPhase(CremeModel):
    name  = CharField(_(u"Name"), max_length=100, blank=False, null=False)
    order = PositiveIntegerField(_(u"Order"), default=1, editable=False).set_tags(viewable=False)
    won   = BooleanField(_(u'Won'), default=False)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Sale phase")
        verbose_name_plural = _(u'Sale phases')
        ordering = ('order',)


class Origin(CremeModel):
    name        = CharField(_(u'Origin'), max_length=100, blank=False, null=False)
    #description = TextField(_(u"Description"))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Origin of opportunity")
        verbose_name_plural = _(u"Origins of opportunity")


class Opportunity(CremeEntity):
    name                  = CharField(_(u"Name of the opportunity"), max_length=100)
    reference             = CharField(_(u"Reference"), max_length=100, blank=True, null=True)
    estimated_sales       = PositiveIntegerField(_(u'Estimated sales'), blank=True, null=True)
    made_sales            = PositiveIntegerField(_(u'Made sales'), blank=True, null=True)
    currency              = ForeignKey(Currency, verbose_name=_(u'Currency'), default=DEFAULT_CURRENCY_PK, on_delete=PROTECT)
    sales_phase           = ForeignKey(SalesPhase, verbose_name=_(u'Sales phase'), on_delete=PROTECT)
    chance_to_win         = PositiveIntegerField(_(ur"% of chance to win"), blank=True, null=True)
    expected_closing_date = DateField(_(u'Expected closing date'), blank=True, null=True)
    closing_date          = DateField(_(u'Actual closing date'), blank=True, null=True)
    origin                = ForeignKey(Origin, verbose_name=_(u'Origin'), blank=True, null=True, on_delete=SET_NULL)
    description           = TextField(_(u'Description'), blank=True, null=True)
    first_action_date     = DateField(_(u'Date of the first action'), blank=True, null=True)

    function_fields = CremeEntity.function_fields.new(_TurnoverField())
    creation_label = _('Add an opportunity')

    _opp_emitter = None
    _opp_target  = None
    _opp_target_rel = None

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u'Opportunity')
        verbose_name_plural = _(u'Opportunities')

    #def __init__(self, *args, **kwargs):
        #super(Opportunity, self).__init__(*args, **kwargs)

        #self._linked_activities = None

    def __unicode__(self):
        return self.name

    def _clean_emitter_n_target(self):
        if not self.pk: #creation
            if not self._opp_emitter:
                raise ValidationError(ugettext('Emitter is required.'))

            if not self._opp_target:
                raise ValidationError(ugettext('Target is required.'))

    def _pre_delete(self):
        for relation in Relation.objects.filter(type__in=[REL_SUB_TARGETS, REL_OBJ_EMIT_ORGA],
                                                subject_entity=self):
            relation._delete_without_transaction()

    def _pre_save_clone(self, source):
        self.emitter = source.emitter
        self.target  = source.target

    def clean(self):
        self._clean_emitter_n_target()
        super(Opportunity, self).clean()

    def get_absolute_url(self):
        return "/opportunities/opportunity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/opportunities/opportunity/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/opportunities/opportunities"

    def get_weighted_sales(self):
        return (self.estimated_sales or 0) * (self.chance_to_win or 0) / 100.0

    #@staticmethod
    #def use_current_quote():
        #try:
            #use_current_quote = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE).value
        #except SettingValue.DoesNotExist:
            #logger.debug("Populate opportunities is not loaded")
            #use_current_quote = False

        #return use_current_quote

    def get_total(self):
        if self.made_sales:
            return self.made_sales
        else:
            return (self.estimated_sales or 0)

    def get_total_with_tax(self):
        tax = 1 + Vat.get_default_vat().value / 100

        if self.made_sales:
            return self.made_sales * tax
        else:
            return (self.estimated_sales or 0) * tax

    #def get_target(self):
        ##NB: this one generates 2 queries instead of one Organisation.objects.get(relations__object_entity=SELF, ...) !!
        #warnings.warn("Opportunity.get_target() method is deprecated; use Opportunity.target instead",
                      #DeprecationWarning
                     #)
        #return CremeEntity.objects.get(relations__object_entity=self.id, relations__type=REL_OBJ_TARGETS).get_real_entity()

    #def get_source(self):
        #warnings.warn("Opportunity.get_source() method is deprecated; use Opportunity.emitter instead",
                      #DeprecationWarning
                     #)
        #return Organisation.objects.get(relations__object_entity=self.id, relations__type=REL_SUB_EMIT_ORGA)

    #TODO: test
    def get_products(self):
        return Product.objects.filter(is_deleted=False,
                                      relations__object_entity=self.id,
                                      relations__type=REL_SUB_LINKED_PRODUCT,
                                     )

    #TODO: test
    def get_services(self):
        return Service.objects.filter(is_deleted=False,
                                      relations__object_entity=self.id,
                                      relations__type=REL_SUB_LINKED_SERVICE,
                                     )

    #TODO: test
    def get_contacts(self):
        return Contact.objects.filter(is_deleted=False,
                                      relations__object_entity=self.id,
                                      relations__type=REL_SUB_LINKED_CONTACT,
                                     )

    #TODO: test
    def get_responsibles(self):
        return Contact.objects.filter(is_deleted=False,
                                      relations__object_entity=self.id,
                                      relations__type=REL_SUB_RESPONSIBLE,
                                     )

    ##todo: test
    #def get_quotes(self):
        ##todo: filter deleted ?? what about current quote behaviour ??
        #return Quote.objects.filter(relations__object_entity=self.id,
                                    #relations__type=REL_SUB_LINKED_QUOTE,
                                   #)

    #def get_current_quote_ids(self):
        #ct        = ContentType.objects.get_for_model(Quote)
        #return Relation.objects.filter(object_entity=self.id,
                                       #type=REL_SUB_CURRENT_DOC,
                                       #subject_entity__entity_type=ct,
                                      #) \
                               #.values_list('subject_entity_id', flat=True)

    ##todo: test
    #def get_salesorder(self):
        #return SalesOrder.objects.filter(is_deleted=False,
                                         #relations__object_entity=self.id,
                                         #relations__type=REL_SUB_LINKED_SALESORDER,
                                        #)

    ##todo: test
    #def get_invoices(self):
        #return Invoice.objects.filter(is_deleted=False,
                                      #relations__object_entity=self.id,
                                      #relations__type=REL_SUB_LINKED_INVOICE,
                                     #)

    @property
    def emitter(self):
        if not self._opp_emitter:
            self._opp_emitter = Organisation.objects.get(relations__type=REL_SUB_EMIT_ORGA,
                                                         relations__object_entity=self.id,
                                                        )

        return self._opp_emitter

    @emitter.setter
    def emitter(self, organisation):
        assert self.pk is None, 'Opportunity.emitter(setter): emitter is already saved (can not change any more).'
        self._opp_emitter = organisation

    @property
    def target(self):
        if not self._opp_target:
            self._opp_target_rel = rel = self.relations.get(type=REL_SUB_TARGETS)
            self._opp_target = rel.object_entity.get_real_entity()

        return self._opp_target

    @target.setter
    def target(self, organisation):
        if self.pk: #edition:
            old_target = self.target
            if old_target != organisation:
                self._opp_target = organisation
        else:
            self._opp_target = organisation

    #def update_sales(self):
        #quotes = Quote.objects.filter(id__in=self.get_current_quote_ids,
                                      #total_no_vat__isnull=False)
        #self.estimated_sales = quotes.aggregate(Sum('total_no_vat'))['total_no_vat__sum'] or 0
        #self.made_sales = quotes.filter(status__won=True).aggregate(Sum('total_no_vat'))['total_no_vat__sum'] or 0
        #self.save()

    @commit_on_success
    def save(self, *args, **kwargs):
        create_relation = partial(Relation.objects.create, object_entity=self, user=self.user)
        target = self._opp_target

        if not self.pk: #creation
            self._clean_emitter_n_target()

            super(Opportunity, self).save(*args, **kwargs)

            create_relation(subject_entity=self._opp_emitter, type_id=REL_SUB_EMIT_ORGA)
            create_relation(subject_entity=target,            type_id=REL_OBJ_TARGETS)

            transform_target_into_prospect(self._opp_emitter, target, self.user)
        else:
            super(Opportunity, self).save(*args, **kwargs)

            old_relation = self._opp_target_rel

            if old_relation and old_relation.object_entity_id != target.id:
                old_relation.delete()
                create_relation(subject_entity=self._opp_target, type_id=REL_OBJ_TARGETS)
                transform_target_into_prospect(self.emitter, target, self.user)


if 'creme.billing' in settings.INSTALLED_APPS:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.signals import post_save, post_delete
    from django.dispatch import receiver

    from creme.creme_config.models import SettingValue

    from creme.billing.models import Quote


    def _get_current_quote_ids(self):
        ct = ContentType.objects.get_for_model(Quote)
        return Relation.objects.filter(object_entity=self.id,
                                       type=REL_SUB_CURRENT_DOC,
                                       subject_entity__entity_type=ct,
                                      ) \
                               .values_list('subject_entity_id', flat=True)

    Opportunity.get_current_quote_ids = _get_current_quote_ids

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
            use_current_quote = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE).value
        except SettingValue.DoesNotExist:
            logger.critical("Populate for opportunities has not been run !")
            use_current_quote = False

        return use_current_quote

    # Adding "current" feature to other billing document (sales order, invoice) does not really make sense.
    # If one day it does we will only have to add senders to the signal
    @receiver(post_save, sender=Quote)
    def _handle_current_quote_change(sender, instance, **kwargs):
        if use_current_quote():
            relations = instance.get_relations(REL_SUB_CURRENT_DOC, real_obj_entities=True)

            if relations: #TODO: useless
                for r in relations:
                    update_sales(r.object_entity.get_real_entity())

    @receiver(post_delete, sender=Relation)
    @receiver(post_save, sender=Relation)
    def _handle_current_quote_set(sender, instance, **kwargs):
        if instance.type_id == REL_SUB_CURRENT_DOC:
            doc = instance.subject_entity.get_real_entity()

            if isinstance(doc, Quote) and use_current_quote():
                update_sales(instance.object_entity.get_real_entity())
