# -*- coding: utf-8 -*-

skip_opportunity_tests = False

try:
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons import get_contact_model, get_organisation_model

    from creme import opportunities
    from creme.opportunities.models import SalesPhase

    Opportunity = opportunities.get_opportunity_model()
    skip_opportunity_tests = opportunities.opportunity_model_is_custom()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))

Organisation = get_organisation_model()
Contact = get_contact_model()


def skipIfCustomOpportunity(test_func):
    return skipIf(skip_opportunity_tests, 'Custom opportunity model in use')(test_func)


class OpportunitiesBaseTestCase(CremeTestCase):
    def _create_target_n_emitter(self, managed=True, contact=False):
        user = self.user
        create_orga = Organisation.objects.create
        emitter = create_orga(user=user, name='My society', is_managed=managed)
        target  = create_orga(user=user, name='Target renegade') if not contact else \
                  Contact.objects.create(user=user, first_name='Target', last_name='Renegade')

        return target, emitter

    def _create_opportunity_n_organisations(self, name='Opp', managed=True, contact=False):
        target, emitter = self._create_target_n_emitter(managed=managed, contact=contact)
        opp = Opportunity.objects.create(user=self.user, name=name,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=emitter, target=target,
                                        )

        return opp, target, emitter
