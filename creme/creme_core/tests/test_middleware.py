from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.constants import UUID_CHANNEL_ADMIN
from creme.creme_core.models import (
    CremePropertyType,
    FakeOrganisation,
    Notification,
    Workflow,
)
from creme.creme_core.utils.media import get_creme_media_url
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EntityCreationTrigger,
    PropertyAddingAction,
)

from .base import CremeTestCase


class RoleMiddlewareTestCase(CremeTestCase):
    def test_not_logged(self):
        self.assertGET200(reverse('creme_login'))

    def test_super_user(self):
        self.login_as_root()
        self.assertGET200(reverse('creme_core__home'))

    def test_role_enabled(self):
        self.login_as_standard()
        self.assertGET200(reverse('creme_core__home'))

    def test_role_disabled(self):
        role = self.create_role(
            name='Disabled', allowed_apps=['creme_core'], deactivated_on=now(),
        )
        user = self.create_user(role=role, password='123', roles=[role])
        self.client._login(user)

        url = reverse('creme_core__home')
        label = _('All your roles are deactivated; please contact your administrator.')
        response = self.client.get(url)
        self.assertContains(response=response, text=label, status_code=403)
        self.assertIn(
            '<button type="submit">{}</button>'.format(_('Log out')),
            response.text,
        )

        # AJAX ---
        self.assertContains(
            response=self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest'),
            text=label,
            status_code=403,
        )

        # Excluded views ---
        self.assertGET200(
            get_creme_media_url(theme='icecream', url='images/meeting_48.png'),
        )
        self.assertPOST200(reverse('creme_logout'), follow=True)

    def test_forced_role_switch(self):
        deact_role = self.create_role(
            name='Disabled', allowed_apps=['creme_core'], deactivated_on=now(),
        )
        ok_role = self.create_role(name='OK', allowed_apps=['creme_core'])
        user = self.create_user(
            index=0, role=deact_role, password='123', roles=[deact_role, ok_role]
        )
        self.client._login(user)

        self.assertGET200(reverse('creme_core__home'))
        self.assertEqual(ok_role, self.refresh(user).role)

        notif = self.get_object_or_fail(
            Notification, user=user, channel__uuid=UUID_CHANNEL_ADMIN,
        )
        self.assertEqual('creme_config-role_switch', notif.content_id)
        self.assertDictEqual({}, notif.content_data)


class WorkflowMiddlewareTestCase(CremeTestCase):
    def test_ok(self):
        """No warning."""
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
        """Some events have not been managed by the engine => warning."""
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
        self.maxDiff = None
        self.assertEqual(
            f'Some workflow events have not been managed by the view '
            f'"/tests/organisation/workflow_badly_used/{orga.id}": '
            f'[EntityEdited(entity=FakeOrganisation(id={orga.id}))].\n'
            f'Hint: use <creme.creme_core.core.workflow.run_workflow_engine()> '
            f'or the view decorator <creme.creme_core.views.decorators.workflow_engine>',
            str(warn_manager.warning),
        )
