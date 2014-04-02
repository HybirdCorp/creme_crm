# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import HeaderFilter

    from creme.persons.models import Contact, Organisation

    from ..blocks import PersonPollRepliesBlock
    from ..core import PollLineType
    from ..models import PollType, PollForm, PollReply, PollFormLine, PollCampaign
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PollsAppTestCase', )


class AutoIncr:
    def __init__(self):
        self._order = 0

    def __call__(self):
        self._order += 1
        return self._order


class _PollsTestCase(CremeTestCase):
    ADD_REPLY_URL = '/polls/poll_reply/add'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'polls')

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
        get_ct = ContentType.objects.get_for_model
        filter_hf = HeaderFilter.objects.filter
        self.assertTrue(filter_hf(entity_type=get_ct(PollForm)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollReply)).exists())
        self.assertTrue(filter_hf(entity_type=get_ct(PollCampaign)).exists())

        self.assertEqual(3, PollType.objects.count())

    def test_contact_block(self):
        self.login()
        leina = Contact.objects.create(user=self.user, first_name='Leina',
                                       last_name='Vance',
                                      )
        response = self.assertGET200(leina.get_absolute_url())

        self.assertContains(response, 'id="%s"' % PersonPollRepliesBlock.id_)
        self.assertTemplateUsed(response, 'polls/templatetags/block_person_preplies.html')

    def test_orga_block(self):
        self.login()
        gaimos = Organisation.objects.create(user=self.user, name='Gaimos')
        response = self.assertGET200(gaimos.get_absolute_url())

        self.assertContains(response, 'id="%s"' % PersonPollRepliesBlock.id_)
