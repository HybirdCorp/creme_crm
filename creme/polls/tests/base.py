# -*- coding: utf-8 -*-

skip_pollcampaign_tests = False
skip_pollform_tests = False
skip_pollreply_tests = False

try:
    from unittest import skipIf

    from django.core.urlresolvers import reverse

    from creme.creme_core.tests.base import CremeTestCase

    from .. import (pollcampaign_model_is_custom, pollform_model_is_custom,
            pollreply_model_is_custom, get_pollform_model,
            get_pollreply_model, get_pollcampaign_model)
    from ..core import PollLineType
    from ..models import PollFormLine

    skip_pollcampaign_tests = pollcampaign_model_is_custom()
    skip_pollform_tests = pollform_model_is_custom()
    skip_pollreply_tests = pollreply_model_is_custom()

    PollCampaign = get_pollcampaign_model()
    PollForm     = get_pollform_model()
    PollReply    = get_pollreply_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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
    ADD_REPLY_URL = reverse('polls__create_reply')

    def _build_stats_url(self, pform):
        return reverse('polls__form_stats', args=(pform.id,))

    def _get_formline_creator(self, pform):
        get_order = AutoIncr()

        def create_line(question, section=None, qtype=PollLineType.STRING, disabled=False, conds_use_or=None, **type_kwargs):
            return PollFormLine.objects.create(
                            pform=pform, section=section,
                            question=question, type=qtype, order=get_order(),
                            disabled=disabled, conds_use_or=conds_use_or,
                            type_args=PollLineType.build_serialized_args(qtype, **type_kwargs)
                                      if type_kwargs else None,
                           )

        return create_line
