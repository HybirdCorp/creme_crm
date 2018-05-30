# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import logging
from functools import partial

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.db.models import (CharField, TextField, ForeignKey, PositiveIntegerField,
        DateField, PROTECT, SET_NULL,  BooleanField)
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.core.function_field import FunctionField, FunctionFieldDecimal
from creme.creme_core.models import (CremeEntity, CremeModel, Relation,
        FieldsConfig, Currency, Vat)
from creme.creme_core.models.fields import BasicAutoField

from creme.persons import get_contact_model, get_organisation_model
from creme.persons.workflow import transform_target_into_prospect

from creme.products import get_product_model, get_service_model

from .. import constants


# logger = logging.getLogger(__name__)


class _TurnoverField(FunctionField):
    name         = 'get_weighted_sales'
    verbose_name = _(u'Weighted sales')
    result_type  = FunctionFieldDecimal

    # @classmethod
    # def populate_entities(cls, entities):
    #     fc = FieldsConfig.get_4_model(entities[0].__class__)
    #
    #     for entity in entities:
    #         entity._fconfig_cache = fc


class SalesPhase(CremeModel):
    name  = CharField(_(u'Name'), max_length=100, blank=False, null=False)
    order = BasicAutoField(_('Order'))
    won   = BooleanField(pgettext_lazy('opportunities-sales_phase', u'Won'), default=False)
    lost  = BooleanField(pgettext_lazy('opportunities-sales_phase', u'Lost'), default=False)

    creation_label = pgettext_lazy('opportunities-sales_phase', 'Create a phase')

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'opportunities'
        verbose_name = _(u'Sale phase')
        verbose_name_plural = _(u'Sale phases')
        ordering = ('order',)

    def clean(self):
        super(SalesPhase, self).clean()

        if self.won and self.lost:
            raise ValidationError(ugettext('A phase can not be won and lost at the same time.'))


class Origin(CremeModel):
    name = CharField(_(u'Origin'), max_length=100, blank=False, null=False)

    creation_label = pgettext_lazy('opportunities-origin', 'Create an origin')

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'opportunities'
        verbose_name = _(u'Origin of opportunity')
        verbose_name_plural = _(u'Origins of opportunity')
        ordering = ('name',)


class AbstractOpportunity(CremeEntity):
    name                  = CharField(_(u'Name of the opportunity'), max_length=100)
    reference             = CharField(_(u'Reference'), max_length=100, blank=True)\
                                     .set_tags(optional=True)
    estimated_sales       = PositiveIntegerField(_(u'Estimated sales'),
                                                 blank=True, null=True,
                                                ).set_tags(optional=True)
    made_sales            = PositiveIntegerField(_(u'Made sales'), blank=True, null=True)\
                                                .set_tags(optional=True)
    currency              = ForeignKey(Currency, verbose_name=_(u'Currency'),
                                       default=DEFAULT_CURRENCY_PK, on_delete=PROTECT,
                                      )
    sales_phase           = ForeignKey(SalesPhase, verbose_name=_(u'Sales phase'),
                                       on_delete=PROTECT,
                                      )
    chance_to_win         = PositiveIntegerField(_(ur'% of chance to win'),
                                                 blank=True, null=True,
                                                ).set_tags(optional=True)
    expected_closing_date = DateField(_(u'Expected closing date'), blank=True, null=True)\
                                     .set_tags(optional=True)
    closing_date          = DateField(_(u'Actual closing date'), blank=True, null=True)\
                                     .set_tags(optional=True)
    origin                = ForeignKey(Origin, verbose_name=_(u'Origin'),
                                       blank=True, null=True, on_delete=SET_NULL,
                                      ).set_tags(optional=True)
    description           = TextField(_(u'Description'), blank=True).set_tags(optional=True)
    first_action_date     = DateField(_(u'Date of the first action'), blank=True, null=True)\
                                     .set_tags(optional=True)

    function_fields = CremeEntity.function_fields.new(_TurnoverField())

    creation_label = _(u'Create an opportunity')
    submit_label   = _(u'Save the opportunity')

    search_score = 100

    _opp_emitter = None
    _opp_target  = None
    _opp_target_rel = None

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'opportunities'
        verbose_name = _(u'Opportunity')
        verbose_name_plural = _(u'Opportunities')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def _clean_emitter_n_target(self):
        if not self.pk:  # Creation
            if not self._opp_emitter:
                raise ValidationError(ugettext('Emitter is required.'))

            if not self._opp_target:
                raise ValidationError(ugettext('Target is required.'))

    def _pre_delete(self):
        for relation in self.relations.filter(type__in=(constants.REL_SUB_TARGETS, constants.REL_OBJ_EMIT_ORGA)):
            relation._delete_without_transaction()

    def _pre_save_clone(self, source):
        self.emitter = source.emitter
        self.target  = source.target

    def clean(self):
        self._clean_emitter_n_target()
        super(AbstractOpportunity, self).clean()

    def get_absolute_url(self):
        return reverse('opportunities__view_opportunity', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('opportunities__create_opportunity')

    def get_edit_absolute_url(self):
        return reverse('opportunities__edit_opportunity', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('opportunities__list_opportunities')

    def get_weighted_sales(self):
        is_hidden = FieldsConfig.get_4_model(self.__class__).is_fieldname_hidden

        if is_hidden('estimated_sales'):
            return ugettext(u'Error: «Estimated sales» is hidden')

        if is_hidden('chance_to_win'):
            return ugettext(ur'Error: «% of chance to win» is hidden')

        return (self.estimated_sales or 0) * (self.chance_to_win or 0) / 100.0

    def get_total(self):
        if self.made_sales:
            return self.made_sales
        else:
            return self.estimated_sales or 0

    def get_total_with_tax(self):
        tax = 1 + Vat.get_default_vat().value / 100

        if self.made_sales:
            return self.made_sales * tax
        else:
            return (self.estimated_sales or 0) * tax

    # TODO: test
    def get_products(self):
        return get_product_model()\
                    .objects\
                    .filter(is_deleted=False,
                            relations__object_entity=self.id,
                            relations__type=constants.REL_SUB_LINKED_PRODUCT,
                           )

    # TODO: test
    def get_services(self):
        return get_service_model()\
                    .objects\
                    .filter(is_deleted=False,
                            relations__object_entity=self.id,
                            relations__type=constants.REL_SUB_LINKED_SERVICE,
                           )

    # TODO: test
    def get_contacts(self):
        return get_contact_model()\
                    .objects\
                    .filter(is_deleted=False,
                            relations__object_entity=self.id,
                            relations__type=constants.REL_SUB_LINKED_CONTACT,
                           )

    # TODO: test
    def get_responsibles(self):
        return get_contact_model()\
                    .objects\
                    .filter(is_deleted=False,
                            relations__object_entity=self.id,
                            relations__type=constants.REL_SUB_RESPONSIBLE,
                           )

    @property
    def emitter(self):
        if not self._opp_emitter:
            self._opp_emitter = get_organisation_model()\
                                    .objects\
                                    .get(relations__type=constants.REL_SUB_EMIT_ORGA,
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
            self._opp_target_rel = rel = self.relations.get(type=constants.REL_SUB_TARGETS)
            self._opp_target = rel.object_entity.get_real_entity()

        return self._opp_target

    @target.setter
    def target(self, organisation):
        if self.pk:  # Edition:
            old_target = self.target
            if old_target != organisation:
                self._opp_target = organisation
        else:
            self._opp_target = organisation

    @atomic
    def save(self, *args, **kwargs):
        create_relation = partial(Relation.objects.create, object_entity=self, user=self.user)
        target = self._opp_target

        if not self.pk:  # Creation
            self._clean_emitter_n_target()

            super(AbstractOpportunity, self).save(*args, **kwargs)

            create_relation(subject_entity=self._opp_emitter, type_id=constants.REL_SUB_EMIT_ORGA)
            create_relation(subject_entity=target,            type_id=constants.REL_OBJ_TARGETS)

            transform_target_into_prospect(self._opp_emitter, target, self.user)
        else:
            super(AbstractOpportunity, self).save(*args, **kwargs)

            old_relation = self._opp_target_rel

            if old_relation and old_relation.object_entity_id != target.id:
                old_relation.delete()
                create_relation(subject_entity=self._opp_target, type_id=constants.REL_OBJ_TARGETS)
                transform_target_into_prospect(self.emitter, target, self.user)

    if apps.is_installed('creme.billing'):
        def get_current_quote_ids(self):
            from django.contrib.contenttypes.models import ContentType

            from creme.billing import get_quote_model

            ct = ContentType.objects.get_for_model(get_quote_model())

            return Relation.objects.filter(object_entity=self.id,
                                           type=constants.REL_SUB_CURRENT_DOC,
                                           subject_entity__entity_type=ct,
                                          ) \
                                   .values_list('subject_entity_id', flat=True)


class Opportunity(AbstractOpportunity):
    class Meta(AbstractOpportunity.Meta):
        swappable = 'OPPORTUNITIES_OPPORTUNITY_MODEL'
