from django.urls import reverse

from creme.creme_core.models import (
    CremePropertyType,
    FakeOrganisation,
    Workflow,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EntityCreationTrigger,
    PropertyAddingAction,
)

from .base import CremeTestCase


class WorkflowMiddlewareTestCase(CremeTestCase):
    def test_ok(self):
        "No warning."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')

        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype,
            )],
        )

        name = 'NERV'
        # The warning causes an error (see CremeTestCase.setUpClass())
        with self.assertNoException():
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

    def test_remaining_events(self):
        "Some events have not been managed by the engine => warning."
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.create(text='Is cool')
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype,
            )],
        )

        with self.assertWarns(expected_warning=RuntimeWarning) as warn_manager:
            self.assertPOST200(reverse('creme_core__workflow_not_called', args=(orga.id,)))

        self.assertEqual('Engine not called', self.refresh(orga).description)
        self.assertEqual(
            f'Some workflow events have not been managed by the view '
            f'"/tests/organisation/workflow_badly_used/{orga.id}": '
            f'[EntityEdited(entity=<FakeOrganisation: NERV>)].\n'
            f'Hint: use <creme.creme_core.core.workflow.run_workflow_engine()> '
            f'or the view decorator <creme.creme_core.views.decorators.workflow_engine>',
            str(warn_manager.warning),
        )
