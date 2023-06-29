from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

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
    def test_contact_brick(self):
        user = self.login_as_root_and_get()
        leina = Contact.objects.create(
            user=user, first_name='Leina', last_name='Vance',
        )
        response = self.assertGET200(leina.get_absolute_url())
        self.assertTemplateUsed(response, 'polls/bricks/person-preplies.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=PersonPollRepliesBrick,
        )
        self.assertEqual(_('Filled form replies'), self.get_brick_title(brick_node))

    @skipIfCustomOrganisation
    def test_orga_brick(self):
        user = self.login_as_root_and_get()
        gaimos = Organisation.objects.create(user=user, name='Gaimos')

        pform = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(
            user=user, pform=pform, name='Reply#1', person=gaimos,
        )

        response = self.assertGET200(gaimos.get_absolute_url())

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=PersonPollRepliesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Filled form reply',
            plural_title='{count} Filled form replies',
        )
        self.assertInstanceLink(brick_node, entity=preply)
