# -*- coding: utf-8 -*-

skip_pollcampaign_tests = False
skip_pollform_tests = False
skip_pollreply_tests = False

try:
    from unittest import skipIf

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import HeaderFilter

    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation
    from creme.persons.models import Contact, Organisation

    from .. import (pollcampaign_model_is_custom, pollform_model_is_custom, pollreply_model_is_custom,
            get_pollform_model, get_pollreply_model, get_pollcampaign_model)
    from ..blocks import PersonPollRepliesBlock
    from ..core import PollLineType
#    from ..models import PollType, PollForm, PollReply, PollFormLine, PollCampaign
    from ..models import PollType, PollFormLine

    skip_pollcampaign_tests = pollcampaign_model_is_custom()
    skip_pollform_tests = pollform_model_is_custom()
    skip_pollreply_tests = pollreply_model_is_custom()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PollsAppTestCase', )


def skipIfCustomPollCampaign(test_func):
    return skipIf(skip_pollcampaign_tests, 'Custom PollCampaign model in use')(test_func)

def skipIfCustomPollForm(test_func):
    return skipIf(skip_pollform_tests, 'Custom PollForm model in use')(test_func)

def skipIfCustomPollReply(test_func):
    return skipIf(skip_pollreply_tests, 'Custom PollReply model in use')(test_func)


class AutoIncr:
    def __init__(self):
        self._order = 0

    def __call__(self):
        self._order += 1
        return self._order


class _PollsTestCase(CremeTestCase):
#    ADD_REPLY_URL = '/polls/poll_reply/add'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('polls')

        cls.ADD_REPLY_URL = reverse('polls__create_reply')

    def _build_stats_url(self, pform):
        return '/polls/poll_form/stats/%s' % pform.id

    def _get_formline_creator(self, pform):
        get_order = AutoIncr()

        def create_line(question, section=None, qtype=PollLineType.STRING, disabled=False, conds_use_or=None, **type_kwargs):
            return  PollFormLine.objects.create(
                            pform=pform, section=section,
                            question=question, type=qtype, order=get_order(),
                            disabled=disabled, conds_use_or=conds_use_or,
                            type_args=PollLineType.build_serialized_args(qtype, **type_kwargs)
                                      if type_kwargs else None,
                           )

        return create_line


class PollsAppTestCase(_PollsTestCase):
    def test_portal(self):
        self.login()
        self.assertGET200('/polls/')

    def test_populate(self):
        PollCampaign = get_pollcampaign_model()
        PollForm     = get_pollform_model()
        PollReply    = get_pollreply_model()
        
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
