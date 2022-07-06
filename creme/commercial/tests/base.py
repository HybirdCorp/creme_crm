from unittest import skipIf

from django.urls import reverse

from creme import activities, commercial, opportunities, persons, products
from creme.creme_core.tests.base import CremeTestCase

from ..models import MarketSegment

skip_act_tests      = commercial.act_model_is_custom()
skip_pattern_tests  = commercial.pattern_model_is_custom()
skip_strategy_tests = commercial.strategy_model_is_custom()

Act = commercial.get_act_model()
ActObjectivePattern = commercial.get_pattern_model()
Strategy = commercial.get_strategy_model()

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()

Activity = activities.get_activity_model()

Product = products.get_product_model()
Service = products.get_service_model()

Opportunity = opportunities.get_opportunity_model()


def skipIfCustomAct(test_func):
    return skipIf(skip_act_tests, 'Custom Act model in use')(test_func)


def skipIfCustomPattern(test_func):
    return skipIf(skip_pattern_tests, 'Custom ActObjectivePattern model in use')(test_func)


def skipIfCustomStrategy(test_func):
    return skipIf(skip_strategy_tests, 'Custom Strategy model in use')(test_func)


class CommercialBaseTestCase(CremeTestCase):
    ADD_SEGMENT_URL = reverse('commercial__create_segment')

    @staticmethod
    def _build_add_segmentdesc_url(strategy):
        return reverse('commercial__create_segment_desc', args=(strategy.id,))

    def _create_segment(self, name='Segment#1'):
        self.assertNoFormError(self.client.post(self.ADD_SEGMENT_URL, data={'name': name}))

        return self.get_object_or_fail(MarketSegment, name=name)

    def _create_segment_desc(self, strategy, name, product='', place='', price='', promotion=''):
        response = self.client.post(
            self._build_add_segmentdesc_url(strategy),
            data={
                'name': name,
                'product': product,
                'place': place,
                'price': price,
                'promotion': promotion,
            },
        )
        self.assertNoFormError(response)

        return strategy.segment_info.get(segment__name=name)

    def _set_asset_score(self, strategy, orga, asset, segment_desc, score):
        self.assertPOST200(
            reverse('commercial__set_asset_score', args=(strategy.id,)),
            data={
                'model_id':        asset.id,
                'segment_desc_id': segment_desc.id,
                'orga_id':         orga.id,
                'score':           score,
            },
        )

    def _set_charm_score(self, strategy, orga, charm, segment_desc, score):
        self.assertPOST200(
            reverse('commercial__set_charm_score', args=(strategy.id,)),
            data={
                'model_id':        charm.id,
                'segment_desc_id': segment_desc.id,
                'orga_id':         orga.id,
                'score':           score,
            },
        )
