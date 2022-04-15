from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import (
    WorkflowBrokenData,
    WorkflowConditions,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Workflow,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EntityCreationTrigger,
    PropertyAddingAction,
    model_as_key,
    model_from_key,
)

from ..base import CremeTestCase


class UtilsTestCase(CremeTestCase):
    def test_model_to_key(self):
        self.assertEqual('creme_core.fakecontact', model_as_key(FakeContact))
        self.assertEqual('creme_core.fakeorganisation', model_as_key(FakeOrganisation))

    def test_key_to_model(self):
        self.assertEqual(FakeContact, model_from_key('creme_core.fakecontact'))
        self.assertEqual(FakeOrganisation, model_from_key('creme_core.fakeorganisation'))

    def test_key_to_model__error(self):
        key = 'uninstalled_app.model'
        with self.assertRaises(WorkflowBrokenData) as cm:
            model_from_key(key)
        self.assertEqual(
            _('The model «{key}» is invalid').format(key=key), str(cm.exception)
        )

        self.assertRaises(WorkflowBrokenData, model_from_key, '')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core.fakecontact.suffix')


class MiddlewareTestCase(CremeTestCase):
    def test_simple(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
            ],
        )

        name = 'NERV'
        self.assertNoFormError(
            self.client.post(
                FakeOrganisation.get_create_absolute_url(),
                data={'user': user.id, 'name': name},
                # follow=True, we check that middleware has been executed with the POST request
            ),
            status=302,
        )
        orga = self.get_object_or_fail(FakeOrganisation, name=name)
        self.assertHasProperty(entity=orga, ptype=ptype)

    def test_disabled(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.create(
            title='Created Organisations are cool',
            enabled=False,
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
            ],
        )

        name = 'NERV'
        self.assertNoFormError(
            self.client.post(
                FakeOrganisation.get_create_absolute_url(),
                data={'user': user.id, 'name': name},
                # follow=True, we check that middleware has been executed with the POST request
            ),
            status=302,
        )
        orga = self.get_object_or_fail(FakeOrganisation, name=name)
        self.assertHasNoProperty(entity=orga, ptype=ptype)

    def test_conditions(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        source = CreatedEntitySource(model=FakeOrganisation)
        Workflow.objects.create(
            title='Created Corporations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().build(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ENDSWITH, field_name='name', values=[' Corp'],
                )],
            ).do(),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        def create_orga(name):
            self.assertNoFormError(
                self.client.post(
                    FakeOrganisation.get_create_absolute_url(),
                    data={'user': user.id, 'name': name},
                    # NB: we check that middleware has been executed with the POST request
                    # follow=True,
                ),
                status=302,
            )
            return self.get_object_or_fail(FakeOrganisation, name=name)

        self.assertHasNoProperty(entity=create_orga('NERV'), ptype=ptype)
        self.assertHasProperty(entity=create_orga('Seele Corp'), ptype=ptype)
