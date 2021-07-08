# -*- coding: utf-8 -*-

from typing import Any, List, Tuple

from creme.creme_core.tests.fake_models import (
    FakeContact,
    FakeDocument,
    FakeOrganisation,
)

from ..backends.models import CrudityBackend
from ..fetchers.base import CrudityFetcher
from ..inputs.base import CrudityInput


class Swallow:
    def __init__(self, title, content):
        self.title = title
        self.content = content


class SwallowFetcher(CrudityFetcher):
    user_id = 0
    last_name = ''

    def fetch(self, *args, **kwargs):
        return [
            Swallow(
                'create contact',
                f'user_id={self.user_id}\n'
                f'last_name={self.last_name}',
            ),
        ]


class SwallowInput(CrudityInput):
    name = 'swallow'
    method = 'create'
    force_not_handle = False

    def create(self, swallow):
        if self.force_not_handle:
            return None

        backend = self.get_backend(CrudityBackend.normalize_subject(swallow.title))
        if backend is None:
            return None

        data = {}

        for line in swallow.content.split('\n'):
            attr, value = line.split('=', 1)
            data[attr] = value

        backend._create_instance_n_history(data, source='Swallow mail')

        return backend


class FakeContactBackend(CrudityBackend):
    model = FakeContact
    calls_args: List[Tuple[Any, Any]] = []

    def fetcher_fallback(self, swallow, current_user):
        self.calls_args.append((swallow, current_user))


class FakeOrganisationBackend(CrudityBackend):
    model = FakeOrganisation


class FakeDocumentBackend(CrudityBackend):
    model = FakeDocument


fetchers = {'swallow': [SwallowFetcher]}
inputs = {'swallow': [SwallowInput]}
backends = [FakeContactBackend, FakeOrganisationBackend]
