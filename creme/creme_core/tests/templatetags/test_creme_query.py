# -*- coding: utf-8 -*-

from django.db.models.query_utils import Q
from django.template import Context, Template

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operators,
)
from creme.creme_core.models import (
    EntityFilter,
    FakeOrganisation,
    SetCredentials,
)

from ..base import CremeTestCase


class CremeQueryTagsTestCase(CremeTestCase):
    def test_entities_count01(self):
        "Super user."
        user = self.login()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='O-1')
        create_orga(user=user, name='O-2')

        with self.assertNoException():
            template = Template(
                r'{% load creme_query %}'
                r'{% query_entities_count ctype=ct user=user as count %}'
                r'{{count}}'
            )
            render = template.render(Context({
                'user': user,
                'ct': orga1.entity_type,
            }))

        self.assertEqual('2', render.strip())

    def test_entities_count02(self):
        "Regular user."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='O-1')
        create_orga(user=self.other_user, name='O-2')

        with self.assertLogs(level='DEBUG') as logs_manager:
            with self.assertNoException():
                template = Template(
                    r'{% load creme_query %}'
                    r'{% query_entities_count ctype=ct user=user as count %}'
                    r'{{count}}'
                )
                render = template.render(Context({
                    'user': user,
                    'ct': orga1.entity_type,
                }))

        self.assertEqual('1', render.strip())

        for msg in logs_manager.output:
            if msg.startswith(
                r'DEBUG:creme.creme_core.templatetags.creme_query:{% query_entities_count %} : '
                r'fast count is not possible'
            ):
                self.fail(f'Slow count message found in {logs_manager.output}')

    def test_entities_count03(self):
        "Regular user + fast count is not possible."
        user = self.login(is_superuser=False)
        name = 'Acme'

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeOrganisation,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EQUALS,
                    field_name='name', values=[name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_FILTER,
            ctype=FakeOrganisation,
            efilter=efilter,
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name=name)
        create_orga(user=self.other_user, name='Other name')

        with self.assertLogs(level='DEBUG') as logs_manager:
            with self.assertNoException():
                template = Template(
                    r'{% load creme_query %}'
                    r'{% query_entities_count ctype=ct user=user as count %}'
                    r'{{count}}'
                )
                render = template.render(Context({
                    'user': user,
                    'ct': orga1.entity_type,
                }))

        self.assertEqual('1', render.strip())

        for msg in logs_manager.output:
            if msg.startswith(
                r'DEBUG:creme.creme_core.templatetags.creme_query:{% query_entities_count %} : '
                r'fast count is not possible'
            ):
                break
        else:
            self.fail(f'No slow count message found in {logs_manager.output}')

    def test_serialize(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_query %}'
                r'{{query|query_serialize|safe}}'
            )
            render = template.render(Context({'query': Q(name='Foobar')}))

        # self.assertEqual('{"op":"AND","val":[["name","Foobar"]]}', render.strip())
        self.assertIn(
            render.strip(),
            (
                '{"op":"AND","val":[["name","Foobar"]]}',
                '{"val":[["name","Foobar"]],"op":"AND"}'
            )
        )
