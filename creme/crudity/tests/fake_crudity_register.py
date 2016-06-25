# -*- coding: utf-8 -*-

from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeDocument

from ..backends.models import CrudityBackend
from ..fetchers.base import CrudityFetcher
from ..inputs.base import CrudityInput


class Swallow(object):
    def __init__(self, title, content):
        self.title = title
        self.content = content


class SwallowFetcher(CrudityFetcher):
    user_id   = 0
    last_name = ''

    def fetch(self, *args, **kwargs):
        return [Swallow('create contact',
                        'user_id=%s\n'
                        'last_name=%s' % (
                                self.user_id,
                                self.last_name,
                            )
                       ),
               ]


class SwallowInput(CrudityInput):
    name = 'swallow'
    method = 'create'
    force_not_handle = False

    def create(self, swallow):
        if self.force_not_handle:
            return False

        backend = self.get_backend(CrudityBackend.normalize_subject(swallow.title))
        if backend is None:
            return False

        data = {}

        for line in swallow.content.split('\n'):
            attr, value = line.split('=', 1)
            data[attr] = value

        backend._create_instance_n_history(data, source='Swallow mail')

        return True


class FakeContactBackend(CrudityBackend):
    model = FakeContact
    calls_args = []

    def fetcher_fallback(self, swallow, current_user):
        self.calls_args.append((swallow, current_user))


class FakeOrganisationBackend(CrudityBackend):
    model = FakeOrganisation


class FakeDocumentBackend(CrudityBackend):
    model = FakeDocument


mock_fetcher = SwallowFetcher()
mock_input = SwallowInput()

fetchers = {'swallow': [mock_fetcher]}
inputs = {'swallow': [mock_input]}
backends = [FakeContactBackend, FakeOrganisationBackend]
