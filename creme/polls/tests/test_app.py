# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import HeaderFilter
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.models import Contact, Organisation
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import PersonPollRepliesBrick
from ..models import PollType
from .base import PollCampaign, PollForm, PollReply, _PollsTestCase


class PollsAppTestCase(_PollsTestCase, BrickTestCaseMixin):
    def test_populate(self):
        get_ct = ContentType.objects.get_for_model
        filter_hf = HeaderFilter.objects.filter
        self.assertTrue(filter_hf(entity_type=get_ct(PollForm)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollReply)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollCampaign)).exists())

        self.assertEqual(3, PollType.objects.count())

    @skipIfCustomContact
    def test_contact_block(self):
        user = self.login()
        leina = Contact.objects.create(
            user=user, first_name='Leina', last_name='Vance',
        )
        response = self.assertGET200(leina.get_absolute_url())
        self.assertTemplateUsed(response, 'polls/bricks/person-preplies.html')

        self.get_brick_node(
            self.get_html_tree(response.content), PersonPollRepliesBrick.id_,
        )

    @skipIfCustomOrganisation
    def test_orga_block(self):
        user = self.login()
        gaimos = Organisation.objects.create(user=user, name='Gaimos')
        response = self.assertGET200(gaimos.get_absolute_url())

        self.get_brick_node(
            self.get_html_tree(response.content), PersonPollRepliesBrick.id_,
        )
