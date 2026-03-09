from functools import partial
from uuid import uuid4

from django.utils.safestring import SafeString
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_OBJ_HAS
from creme.creme_core.core.notification import (
    OUTPUT_WEB,
    OneEntityTemplateStringContent,
)
from creme.creme_core.core.workflow import (
    WorkflowBrokenData,
    workflow_registry,
)
from creme.creme_core.forms.workflows import NotificationSendingActionForm
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    FakeProduct,
    Notification,
    NotificationChannel,
    RelationType,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    FixedEntitySource,
    FixedUserSource,
    NotificationSendingAction,
    ObjectEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
    SubjectEntitySource,
    UserFKSource,
)

from ..base import CremeTestCase


class PropertyAddingActionTestCase(CremeTestCase):
    def test_str_uuid(self):
        user = self.get_root_user()
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        source = CreatedEntitySource(model=FakeOrganisation)
        action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        self.assertEqual(_('Adding a property'), str(action))
        self.assertEqual(source, action.entity_source)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        with self.assertNumQueries(0):
            action.property_type  # NOQA

        serialized = {
            'type': type_id,
            'entity': {
                'type': CreatedEntitySource.type_id,
                'model': 'creme_core.fakeorganisation',
            },
            'ptype': str(ptype.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            _('Adding the property «{property}» to: {source}').format(
                property=ptype.text,
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            action.render(user=user),
        )

        self.assertEqual(
            'PropertyAddingAction('
            'entity_source=CreatedEntitySource(model=FakeOrganisation), '
            'ptype=CremePropertyType(text="Is kawaiiii"))',
            repr(action),
        )

        # De-serialisation ---
        deserialized = PropertyAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, PropertyAddingAction)
        self.assertEqual(ptype, deserialized.property_type)
        self.assertEqual(
            CreatedEntitySource(model=FakeOrganisation),
            deserialized.entity_source,
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        ctxt_key = source.type_id
        deserialized.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: entity})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: None})

    def test_ptype_instance(self):
        user = self.get_root_user()
        ptype = CremePropertyType.objects.create(text='Is swag')
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(entity=entity)
        action = PropertyAddingAction(entity_source=source, ptype=ptype)

        action.execute(context={}, user=user)
        self.assertHasProperty(entity=entity, ptype=ptype)

        with self.assertNumQueries(0):
            self.assertEqual(ptype, action.property_type)

        # Render ---
        output = action.render(user=user)
        self.assertHTMLEqual(
            _('Adding the property «{property}» to: {source}').format(
                property=ptype.text,
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            output,
        )
        self.assertIsInstance(output, SafeString)

    def test_config_form_class(self):
        from creme.creme_core.forms.workflows import PropertyAddingActionForm
        self.assertIs(
            PropertyAddingActionForm, PropertyAddingAction.config_form_class(),
        )

    def test_eq(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is kawaiiii')

        action1 = PropertyAddingAction(
            entity_source=CreatedEntitySource(model=FakeOrganisation),
            ptype=str(ptype1.uuid),
        )
        self.assertEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=str(ptype1.uuid),
            ),
            action1,
        )
        self.assertEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype1,
            ),
            action1,
        )
        self.assertNotEqual(None, action1)
        self.assertNotEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeContact),
                ptype=ptype1,
            ),
            action1,
        )

        ptype2 = create_ptype(text='Is cool')
        self.assertNotEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype2,
            ),
            action1,
        )

    def test_broken_ptype(self):
        action = PropertyAddingAction.from_dict(
            data={
                'type': PropertyAddingAction.type_id,
                'entity': {
                    'type': CreatedEntitySource.type_id,
                    'model': 'creme_core.fakeorganisation',
                },
                'ptype': str(uuid4()),
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                action.property_type  # NOQA
        err_msg = _('The property type does not exist anymore')
        self.assertEqual(err_msg, str(cm.exception))

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                action.property_type  # NOQA

        # Render ---
        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Adding a property'), error=err_msg,
            ),
            action.render(user=self.get_root_user()),
        )

        # Execute ---
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        with self.assertNoException():
            with self.assertLogs(level='ERROR'):
                action.execute(context={CreatedEntitySource.type_id: orga})

    def test_ctype_constraint(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        source = CreatedEntitySource(model=FakeOrganisation)
        action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        ptype.set_subject_ctypes(FakeContact)

        # Render ---
        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Adding the property «{property}» to: {source}').format(
                    property=ptype.text,
                    source=source.render(user=user, mode=source.RenderMode.HTML),
                ),
                error=_('The source type is not compatible with this property type'),
            ),
            action.render(user=user),
        )

        # Execute ---
        with self.assertLogs(level='WARNING'):
            action.execute(context={source.type_id: orga})

        self.assertHasNoProperty(entity=orga, ptype=ptype)


class RelationAddingActionTestCase(CremeTestCase):
    def test_str_id(self):
        user = self.get_root_user()
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(_('Adding a relationship'), RelationAddingAction.verbose_name)

        # Instance ---
        rtype = RelationType.objects.builder(
            id='test-subject_bought', predicate='is bought by',
        ).symmetric(id='test-object_bought', predicate='buys').get_or_create()[0]

        source1 = SubjectEntitySource(model=FakeContact)
        source2 = ObjectEntitySource(model=FakeOrganisation)
        action = RelationAddingAction(
            subject_source=source1, rtype=rtype.id, object_source=source2,
        )
        self.assertEqual(_('Adding a relationship'), str(action))
        self.assertEqual(source1, action.subject_source)
        self.assertEqual(source2, action.object_source)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, action.relation_type)

        with self.assertNumQueries(0):
            action.relation_type  # NOQA

        serialized = {
            'type': type_id,
            'subject': source1.to_dict(),
            'rtype': rtype.id,
            'object': source2.to_dict(),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}</li>'
            '  <li>{object}</li>'
            ' </ul>'
            '</div>'.format(
                label=_('Adding the relationship «{predicate}» between:').format(
                    predicate=rtype.predicate,
                ),
                subject=source1.render(user=user, mode=source1.RenderMode.HTML),
                object=source2.render(user=user, mode=source2.RenderMode.HTML),
            ),
            action.render(user=user),
        )

        self.assertEqual(
            'RelationAddingAction('
            'subject_source=SubjectEntitySource(model=FakeContact), '
            'rtype=RelationType(predicate="is bought by"), '
            'object_source=ObjectEntitySource(model=FakeOrganisation))',
            repr(action),
        )

        # De-serialisation ---
        deserialized = RelationAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, RelationAddingAction)
        self.assertEqual(rtype,   deserialized.relation_type)
        self.assertEqual(source1, deserialized.subject_source)
        self.assertEqual(source2, deserialized.object_source)

        # Execution ---
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')
        ctxt_key1 = source1.type_id
        ctxt_key2 = source2.type_id
        deserialized.execute({ctxt_key1: entity1, ctxt_key2: entity2})
        rel = self.assertHaveRelation(subject=entity1, type=rtype, object=entity2)
        self.assertEqual(user, rel.user)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: entity2})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: None,    ctxt_key2: entity2})
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: None})

    def test_rtype_instance(self):
        user1 = self.get_root_user()
        rtype = RelationType.objects.builder(
            id='test-subject_lead', predicate='leads', models=[FakeContact],
        ).symmetric(
            id='test-object_lead', predicate='is lead by', models=[FakeOrganisation],
        ).get_or_create()[0]

        orga = FakeOrganisation.objects.create(user=user1, name='Acme')

        source1 = CreatedEntitySource(model=FakeContact)
        source2 = FixedEntitySource(entity=orga)
        action = RelationAddingAction(
            subject_source=source1, rtype=rtype, object_source=source2,
        )

        with self.assertNumQueries(0):
            self.assertEqual(rtype, action.relation_type)

        # execute ---
        contact = FakeContact.objects.create(user=user1, first_name='John', last_name='Doe')
        user2 = self.create_user()

        action.execute(
            context={source1.type_id: contact, source2.type_id: orga},
            user=user2,
        )
        rel = self.assertHaveRelation(subject=contact, type=rtype, object=orga)
        self.assertEqual(user2, rel.user)

    def test_config_form_class(self):
        from creme.creme_core.forms.workflows import RelationAddingActionForm

        self.assertIs(
            RelationAddingActionForm, RelationAddingAction.config_form_class(),
        )

    def test_eq(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        action1 = RelationAddingAction(
            subject_source=SubjectEntitySource(model=FakeContact),
            rtype=rtype,
            object_source=ObjectEntitySource(model=FakeOrganisation),
        )

        self.assertEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype.id,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )

        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeProduct),  # <==
                rtype=rtype.id,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype.symmetric_type,  # <==
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype,
                object_source=ObjectEntitySource(model=FakeProduct),  # <==
            ),
            action1,
        )
        self.assertNotEqual(None, action1)

    def test_broken_rtype(self):
        action = RelationAddingAction.from_dict(
            data={
                'type': RelationAddingAction.type_id,
                'subject': {
                    'type': SubjectEntitySource.type_id,
                    'model': 'creme_core.fakeorganisation',
                },
                'object': {
                    'type': ObjectEntitySource.type_id,
                    'model': 'creme_core.fakecontact',
                },
                'rtype': 'uninstalled_app-subject_predicate',
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                action.relation_type  # NOQA
        err_msg = _('The relationship type does not exist anymore')
        self.assertEqual(err_msg, str(cm.exception))

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                action.relation_type  # NOQA

        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Adding a relationship'), error=err_msg,
            ),
            action.render(user=self.get_root_user()),
        )

        # Execute ---
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        contact = FakeContact.objects.create(user=user, last_name='Doe')

        with self.assertNoException():
            with self.assertLogs(level='ERROR'):
                action.execute(context={
                    SubjectEntitySource.type_id: orga,
                    ObjectEntitySource.type_id: contact,
                })

    def test_ctype_constraints(self):
        user = self.get_root_user()

        rtype1 = RelationType.objects.builder(
            id='test-subject_bought', predicate='is bought by',
        ).symmetric(
            id='test-object_bought', predicate='buys',
        ).get_or_create()[0]
        rtype2 = rtype1.symmetric_type

        source1 = SubjectEntitySource(model=FakeContact)
        source2 = ObjectEntitySource(model=FakeOrganisation)
        action1 = RelationAddingAction(
            subject_source=source1, rtype=rtype1.id, object_source=source2,
        )
        action2 = RelationAddingAction(
            subject_source=source1, rtype=rtype2.id, object_source=source2,
        )

        rtype1.add_subject_ctypes(FakeProduct)

        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        contact = FakeContact.objects.create(user=user, last_name='Doe')
        ctxt = {source1.type_id: orga, source2.type_id: contact}

        # Subject constraint ---
        # Execute
        with self.assertLogs(level='WARNING') as log_cm1:
            action1.execute(context=ctxt)

        self.assertHaveNoRelation(subject=orga, type=rtype1, object=contact)
        err_fmt = _(
            'The entity «%(entity)s» is a «%(model)s» which is not '
            'allowed by the relationship «%(predicate)s».'
        )
        self.assertIn(
            err_fmt % {
                'entity': orga,
                'model': orga.entity_type,
                'predicate': rtype1.predicate,
            },
            self.get_alone_element(log_cm1.output),
        )

        # Render
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}<p class="errorlist">{error}</p></li>'
            '  <li>{object}</li>'
            ' </ul>'
            '</div>'.format(
                label=_('Adding the relationship «{predicate}» between:').format(
                    predicate=rtype1.predicate,
                ),
                subject=source1.render(user=user, mode=source1.RenderMode.HTML),
                object=source2.render(user=user, mode=source2.RenderMode.HTML),
                error=_('The source type is not compatible with this relationship type'),
            ),
            action1.render(user=user),
        )

        # Object constraint ---
        # Execute
        with self.assertLogs(level='WARNING') as log_cm2:
            action2.execute(context=ctxt)

        self.assertHaveNoRelation(subject=orga, type=rtype2, object=contact)
        self.assertIn(
            err_fmt % {
                'entity': contact,
                'model': contact.entity_type,
                'predicate': rtype1.predicate,
            },
            self.get_alone_element(log_cm2.output),
        )

        # Render
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}</li>'
            '  <li>{object}<p class="errorlist">{error}</p></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Adding the relationship «{predicate}» between:').format(
                    predicate=rtype2.predicate,
                ),
                subject=source1.render(user=user, mode=source1.RenderMode.HTML),
                object=source2.render(user=user, mode=source2.RenderMode.HTML),
                error=_('The source type is not compatible with this relationship type'),
            ),
            action2.render(user=user),
        )

    def test_properties_constraints(self):
        user = self.get_root_user()

        rtype1 = RelationType.objects.builder(
            id='test-subject_bought', predicate='is drawing the logo of', models=[FakeContact],
        ).symmetric(
            id='test-object_bought', predicate='has artist', models=[FakeOrganisation],
        ).get_or_create()[0]
        rtype2 = rtype1.symmetric_type

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is an artist')
        ptype2 = create_ptype(text='likes artist')

        source1 = SubjectEntitySource(model=FakeContact)
        source2 = ObjectEntitySource(model=FakeOrganisation)
        action = RelationAddingAction(
            subject_source=source1, rtype=rtype1.id, object_source=source2,
        )

        rtype1.subject_properties.add(ptype1)
        rtype2.subject_properties.add(ptype2)

        contact = FakeContact.objects.create(
            user=user, first_name='Jheronimus', last_name='Bosch',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        # Subject constraint ---
        with self.assertLogs(level='WARNING') as log_cm1:
            action.execute(context={source1.type_id: contact, source2.type_id: orga})

        self.assertHaveNoRelation(subject=contact, type=rtype1, object=orga)
        err_fmt = _(
            'The entity «%(entity)s» has no property «%(property)s» '
            'which is required by the relationship «%(predicate)s».'
        )
        self.assertIn(
            err_fmt % {
                'entity': contact,
                'property': ptype1,
                'predicate': rtype1.predicate,
            },
            self.get_alone_element(log_cm1.output),
        )

        # Object constraint ---
        CremeProperty.objects.create(creme_entity=contact, type=ptype1)

        with self.assertLogs(level='WARNING') as log_cm2:
            action.execute(context={
                source1.type_id: self.refresh(contact),
                source2.type_id: orga,
            })

        self.assertHaveNoRelation(subject=contact, type=rtype1, object=orga)
        self.assertIn(
            err_fmt % {
                'entity': orga,
                'property': ptype2,
                'predicate': rtype2.predicate,
            },
            self.get_alone_element(log_cm2.output),
        )


class NotificationSendingActionTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = NotificationChannel.objects.create(
            name='Workflow', default_outputs=[OUTPUT_WEB],
            description='Notification for Workflow',
        )

    def test_fixed_user(self):
        "One user, no template for subject/body."
        user = self.get_root_user()

        type_id = 'creme_core-notification_sending'
        self.assertEqual(type_id, NotificationSendingAction.type_id)
        self.assertEqual(
            _('Sending a notification'), NotificationSendingAction.verbose_name,
        )

        # Instance ---
        channel = self.channel
        user_source = FixedUserSource(user=user)
        subject = 'This is important'
        body = 'A Contact has been created.'
        source = CreatedEntitySource(model=FakeContact)
        action = NotificationSendingAction(
            channel=channel,
            user_source=user_source,
            entity_source=source,
            subject=subject, body=body,
        )
        self.assertEqual(channel,     action.channel)
        self.assertEqual(user_source, action.user_source)
        self.assertEqual(subject,     action.subject)
        self.assertEqual(body,        action.body)
        self.assertEqual(source,      action.entity_source)

        self.maxDiff = None
        self.assertEqual(
            f'NotificationSendingAction('
            f'channel=NotificationChannel(uuid="{channel.uuid}", name="Workflow", type_id=""), '
            f'user_source=FixedUserSource(user=CremeUser(username="root")), '
            f'entity_source=CreatedEntitySource(model=FakeContact), '
            f'subject="{subject}", body="{body}"'
            f')',
            repr(action),
        )

        serialized = {
            'type': type_id,
            'channel': str(self.channel.uuid),
            'user': user_source.to_dict(),
            'entity': source.to_dict(),
            'subject': subject,
            'body': body,
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{channel}</li>'
            '  <li>{user}</li>'
            '  <li>{subject}</li>'
            '  <li>{body_label}<br><p>{body}</p></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending a notification:'),
                channel=_('On channel: {channel}').format(channel=self.channel),
                user=user_source.render(user=user),
                subject=_('Subject: {subject}').format(subject=subject),
                body_label=_('Body:'), body=body,
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = NotificationSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, NotificationSendingAction)
        self.assertEqual(user_source, deserialized.user_source)
        self.assertEqual(source,      deserialized.entity_source)
        self.assertEqual(subject,     deserialized.subject)
        self.assertEqual(body,        deserialized.body)

        # Execution ---
        notif_old_count = Notification.objects.count()
        entity = FakeContact.objects.create(user=user, last_name='Spiegel')
        deserialized.execute(context={CreatedEntitySource.type_id: entity})
        self.assertEqual(notif_old_count + 1, Notification.objects.count())

        notif = self.get_object_or_fail(
            Notification, user=user, channel__uuid=self.channel.uuid,
        )
        self.assertEqual(OneEntityTemplateStringContent.id, notif.content_id)
        exp_data = {
            'subject': subject, 'body': body,
            'ctype': entity.entity_type_id, 'entity': entity.id,
        }
        self.assertDictEqual(exp_data, notif.content_data)
        self.assertIsNone(notif.discarded)
        self.assertEqual(Notification.Level.NORMAL, notif.level)
        self.assertEqual(OUTPUT_WEB,                notif.output)
        self.assertDictEqual({}, notif.extra_data)
        self.assertEqual(body, notif.content.get_body(user))

        # Configuration ---
        self.assertEqual(
            NotificationSendingAction.config_form_class(),
            NotificationSendingActionForm,
        )

    def test_user_fk(self):
        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        )
        user_source = UserFKSource(
            entity_source=EditedEntitySource(model=FakeContact),
            field_name='user',
        )
        action = NotificationSendingAction(
            channel=self.channel,
            user_source=user_source,
            entity_source=EditedEntitySource(model=FakeContact),
            subject='Modification!!',
            body='A Contact has been modified: {{entity}}',
        )
        action.execute(context={EditedEntitySource.type_id: contact})

        notif = Notification.objects.order_by('-id')[0]
        self.assertEqual(self.channel, notif.channel)
        self.assertEqual(user,         notif.user)
        self.assertEqual(
            f'A Contact has been modified: {contact}',
            notif.content.get_body(user),
        )

    def test_no_user(self):
        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='John', last_name='Doe',
        )
        user_source = UserFKSource(
            entity_source=EditedEntitySource(model=FakeContact),
            field_name='is_user',
        )
        action = NotificationSendingAction(
            channel=self.channel,
            user_source=user_source,
            entity_source=EditedEntitySource(model=FakeContact),
            subject='Modification!!',
            body='A Contact has been modified: {{entity}}',
        )

        # <is_user==None> => No notification sent
        action.execute(context={EditedEntitySource.type_id: contact})
        self.assertFalse(Notification.objects.all())

    def test_empty_source(self):
        action = NotificationSendingAction(
            channel=self.channel,
            user_source=FixedUserSource(user=self.get_root_user()),
            entity_source=EditedEntitySource(model=FakeContact),
            subject='Modification!!',
            body='A Contact has been modified: {{entity}}',
        )

        action.execute(context={EditedEntitySource.type_id: None})
        self.assertFalse(Notification.objects.all())

    def test_eq(self):
        user = self.get_root_user()
        subject = 'Modification!!'
        body = 'A Contact has been modified: {{entity}}'
        channel = self.channel
        action1 = NotificationSendingAction(
            channel=channel,
            user_source=FixedUserSource(user=user),
            entity_source=EditedEntitySource(model=FakeContact),
            subject=subject, body=body,
        )
        self.assertEqual(
            NotificationSendingAction(
                channel=channel,
                user_source=FixedUserSource(user=user),
                entity_source=EditedEntitySource(model=FakeContact),
                subject=subject, body=body,
            ),
            action1,
        )
        self.assertNotEqual(None, action1)
        self.assertNotEqual(
            NotificationSendingAction(
                channel=NotificationChannel.objects.create(
                    name='Other channel', default_outputs=[OUTPUT_WEB],
                ),  # <==
                user_source=FixedUserSource(user=user),
                entity_source=EditedEntitySource(model=FakeContact),
                subject=subject, body=body,
            ),
            action1,
        )
        self.assertNotEqual(
            NotificationSendingAction(
                channel=channel,
                user_source=FixedUserSource(user=self.create_user()),  # <==
                entity_source=EditedEntitySource(model=FakeContact),
                subject=subject, body=body,
            ),
            action1,
        )
        self.assertNotEqual(
            NotificationSendingAction(
                channel=channel,
                user_source=FixedUserSource(user=user),
                entity_source=EditedEntitySource(model=FakeOrganisation),  # <==
                subject=subject, body=body,
            ),
            action1,
        )
        self.assertNotEqual(
            NotificationSendingAction(
                channel=channel,
                user_source=FixedUserSource(user=user),
                entity_source=EditedEntitySource(model=FakeContact),
                subject='Other subject',
                body=body,
            ),
            action1,
        )
        self.assertNotEqual(
            NotificationSendingAction(
                channel=channel,
                user_source=FixedUserSource(user=user),
                entity_source=EditedEntitySource(model=FakeContact),
                subject=subject,
                body='Other body',
            ),
            action1,
        )

    def test_registry__global(self):
        self.assertIn(NotificationSendingAction, workflow_registry.action_classes)
