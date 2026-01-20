from unittest import skipIf

from django.urls import reverse

from creme.creme_core.tests.base import CremeTestCase

from .. import (
    get_pollcampaign_model,
    get_pollform_model,
    get_pollreply_model,
    pollcampaign_model_is_custom,
    pollform_model_is_custom,
    pollreply_model_is_custom,
)
from ..core import PollLineType
from ..models import PollFormLine

skip_pollcampaign_tests = pollcampaign_model_is_custom()
skip_pollform_tests = pollform_model_is_custom()
skip_pollreply_tests = pollreply_model_is_custom()

PollCampaign = get_pollcampaign_model()
PollForm     = get_pollform_model()
PollReply    = get_pollreply_model()


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
    ADD_REPLIES_URL = reverse('polls__create_replies')

    def login_as_polls_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['polls', *allowed_apps],
            **kwargs
        )

    @staticmethod
    def _build_stats_url(pform):
        return reverse('polls__form_stats', args=(pform.id,))

    @staticmethod
    def _get_formline_creator(pform):
        get_order = AutoIncr()

        def create_line(
                question,
                section=None, qtype=PollLineType.STRING, disabled=False, conds_use_or=None,
                **type_kwargs):
            return PollFormLine.objects.create(
                pform=pform, section=section,
                question=question, type=qtype, order=get_order(),
                disabled=disabled, conds_use_or=conds_use_or,
                type_args=(
                    PollLineType.build_serialized_args(qtype, **type_kwargs)
                    if type_kwargs else
                    None
                ),
            )

        return create_line

    @staticmethod
    def _build_preplies_from_pform_url(pform):
        return reverse('polls__create_replies_from_pform', args=(pform.id,))

    @staticmethod
    def _build_fill_url(preply):
        return reverse('polls__fill_reply', args=(preply.id,))

    def _create_pform_with_3_lines_for_conditions(self, user):
        self.pform = pform = PollForm.objects.create(user=user, name='Form#1')
        ENUM = PollLineType.ENUM
        create_l = self._get_formline_creator(pform=pform)
        choices = [[1, 'A little bit'], [2, 'A lot']]

        return (
            create_l('How do you like swallows ?', qtype=ENUM, choices=choices),
            create_l('How do you like parrots ?',  qtype=ENUM, choices=choices),
            create_l('Do you love all birds ?',    qtype=PollLineType.STRING, conds_use_or=False),
        )

    def _create_preply(self, *, user, ptype=None):
        pform = PollForm.objects.create(user=user, name='Form#1', type=ptype)
        return PollReply.objects.create(user=user, pform=pform, name='Reply#1', type=ptype)

    def _create_preply_from_pform(self, pform, name='Reply#1'):
        self.assertNoFormError(self.client.post(
            self._build_preplies_from_pform_url(pform),
            data={
                'user': pform.user.id,   # TODO: "user" argument?
                'name': name,
            },
        ))

        return self.get_object_or_fail(PollReply, name=name)

    def _fill_preply(self, preply, *answers, **kwargs):
        assert answers, 'Give at least one answer dude'
        url = self._build_fill_url(preply)
        response = None
        check_errors = kwargs.get('check_errors', True)
        not_applicable = kwargs.get('not_applicable', False)

        for answer in answers:
            data = {**answer} if isinstance(answer, dict) else {'answer': answer}

            if not_applicable:
                data['not_applicable'] = 'on'

            response = self.assertPOST200(url, follow=True, data=data)

            if check_errors:
                self.assertNoFormError(response)

        return response
