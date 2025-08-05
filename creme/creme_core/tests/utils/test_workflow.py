from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ngettext

from creme.creme_core.models import FakeContact, FakeOrganisation, Workflow
from creme.creme_core.utils.workflow import form_help_message
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    EntityEditionTrigger,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_form_help_message__empty(self):
        Workflow.objects.update(enabled=False)
        self.assertEqual(
            '', form_help_message(model=FakeOrganisation),
        )

    def test_form_help_message__singular(self):
        Workflow.objects.update(enabled=False)

        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(Workflow.objects.filter(content_type=ct))

        wf = Workflow.objects.create(
            title='My awesome workflow',
            content_type=FakeContact,
            trigger=EntityCreationTrigger(model=FakeContact),
        )

        self.assertEqual(
            ngettext(
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form (there is {count} enabled Workflow).',
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form (there are {count} enabled Workflows).',
                1,
            ).format(count=1),
            form_help_message(model=FakeOrganisation),
        )

        self.maxDiff = None
        self.assertEqual(
            ngettext(
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form. For example, this Workflow is '
                'directly related to «{models}»: {workflows}',
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form. For example, these Workflows are '
                'directly related to «{models}»: {workflows}',
                1,
            ).format(
                models='Test Contacts',
                workflows=wf.title,
            ),
            form_help_message(model=FakeContact),
        )

    def test_form_help_message__plural(self):
        Workflow.objects.update(enabled=False)

        self.assertFalse(Workflow.objects.filter(
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        ))

        wf1 = Workflow.objects.create(
            title='My awesome workflow #1',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
        )
        wf2 = Workflow.objects.create(
            title='My awesome workflow #2',
            content_type=FakeOrganisation,
            trigger=EntityEditionTrigger(model=FakeOrganisation),
        )
        Workflow.objects.create(
            title='My disabled workflow',
            content_type=FakeOrganisation,
            trigger=EntityEditionTrigger(model=FakeOrganisation),
            enabled=False,
        )

        self.assertEqual(
            ngettext(
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form (there is {count} enabled Workflow).',
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form (there are {count} enabled Workflows).',
                2,
            ).format(count=2),
            form_help_message(model=FakeContact),
        )
        self.assertEqual(
            ngettext(
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form. For example, this Workflow is '
                'directly related to «{models}»: {workflows}',
                'Do not forget that Workflows can be triggered by the actions '
                'performed by this form. For example, these Workflows are '
                'directly related to «{models}»: {workflows}',
                2,
            ).format(
                models='Test Organisations',
                workflows=f'{wf1.title}, {wf2.title}',
            ),
            form_help_message(model=FakeOrganisation),
        )
