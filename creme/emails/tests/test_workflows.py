from django.utils.translation import gettext as _

from ..workflows import EmailSendingAction
# from .base import EntityEmail, _EmailsTestCase
from .base import _EmailsTestCase


# class UtilsTestCase(, _DocumentsTestCase):
class WorkflowsTestCase(_EmailsTestCase):
    def test_action__send_email(self):
        # user = self.get_root_user()
        type_id = 'emails-email_sending'
        self.assertEqual(type_id, EmailSendingAction.type_id)
        self.assertEqual(_('Sending an email'), EmailSendingAction.verbose_name)

        # # Instance ---
        # ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        # source = CreatedEntitySource(model=FakeOrganisation)
        # action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        # self.assertEqual(source, action.entity_source)
        #
        # with self.assertNumQueries(1):
        #     self.assertEqual(ptype, action.property_type)
        #
        # with self.assertNumQueries(0):
        #     action.property_type  # NOQA
        #
        # serialized = {
        #     'type': type_id,
        #     'entity': {
        #         'type': CreatedEntitySource.type_id,
        #         'model': 'creme_core-fakeorganisation',
        #     },
        #     'ptype': str(ptype.uuid),
        # }
        # self.assertDictEqual(serialized, action.to_dict())
        # self.assertHTMLEqual(
        #     _('Adding the property «{property}» to: {source}').format(
        #         property=ptype.text,
        #         source=source.render(user=user, mode=source.HTML),
        #     ),
        #     action.render(user=user),
        # )
        #
        # # De-serialisation ---
        # deserialized = PropertyAddingAction.from_dict(
        #     data=serialized, registry=workflow_registry,
        # )
        # self.assertIsInstance(deserialized, PropertyAddingAction)
        # self.assertEqual(ptype, deserialized.property_type)
        # self.assertEqual(
        #     CreatedEntitySource(model=FakeOrganisation),
        #     deserialized.entity_source,
        # )
        #
        # # Execution ---
        # entity = FakeOrganisation.objects.create(user=user, name='Acme')
        # ctxt_key = source.type_id
        # deserialized.execute(context={ctxt_key: entity})
        # self.assertHasProperty(entity=entity, ptype=ptype)
        #
        # # Execute twice => beware of property uniqueness
        # with self.assertNoException():
        #     deserialized.execute(context={ctxt_key: entity})
        #
        # # With empty source
        # with self.assertNoException():
        #     deserialized.execute(context={ctxt_key: None})
        #
        # # Configuration
        # from creme.creme_core.forms.workflows import PropertyAddingActionForm
        # self.assertIs(
        #     PropertyAddingActionForm, PropertyAddingAction.config_form_class(),
        # )
