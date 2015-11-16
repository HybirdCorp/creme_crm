# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import HeaderFilter

    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation
    from creme.persons.models import Contact, Organisation

    from .base import _PollsTestCase, PollCampaign, PollForm, PollReply
    # from .. import get_pollform_model, get_pollreply_model, get_pollcampaign_model
    from ..blocks import PersonPollRepliesBlock
#    from ..models import PollType, PollForm, PollReply, PollCampaign
    from ..models import PollType
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


# __all__ = ('PollsAppTestCase', )


class PollsAppTestCase(_PollsTestCase):
    def test_portal(self):
        self.login()
        self.assertGET200('/polls/')

    def test_populate(self):
        # PollCampaign = get_pollcampaign_model()
        # PollForm     = get_pollform_model()
        # PollReply    = get_pollreply_model()
        
        get_ct = ContentType.objects.get_for_model
        filter_hf = HeaderFilter.objects.filter
        self.assertTrue(filter_hf(entity_type=get_ct(PollForm)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollReply)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollCampaign)).exists())

        self.assertEqual(3, PollType.objects.count())

    @skipIfCustomContact
    def test_contact_block(self):
        user = self.login()
        leina = Contact.objects.create(user=user, first_name='Leina',
                                       last_name='Vance',
                                      )
        response = self.assertGET200(leina.get_absolute_url())

        self.assertContains(response, 'id="%s"' % PersonPollRepliesBlock.id_)
        self.assertTemplateUsed(response, 'polls/templatetags/block_person_preplies.html')

    @skipIfCustomOrganisation
    def test_orga_block(self):
        user = self.login()
        gaimos = Organisation.objects.create(user=user, name='Gaimos')
        response = self.assertGET200(gaimos.get_absolute_url())

        self.assertContains(response, 'id="%s"' % PersonPollRepliesBlock.id_)
