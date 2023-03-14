from functools import partial
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import EntityJobErrorsBrick, TrashBrick
from creme.creme_core.creme_jobs import reminder_type, trash_cleaner_type
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    EntityJobResult,
    FakeContact,
    FakeImage,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    HistoryLine,
    Job,
    Relation,
    RelationType,
    Sandbox,
    SetCredentials,
    TrashCleaningCommand,
    history,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin, ViewsTestCase


class EntityViewsTestCase(BrickTestCaseMixin, ViewsTestCase):
    CLONE_URL        = reverse('creme_core__clone_entity')
    DEL_ENTITIES_URL = reverse('creme_core__delete_entities')
    EMPTY_TRASH_URL  = reverse('creme_core__empty_trash')
    SEARCHNVIEW_URL  = reverse('creme_core__search_n_view_entities')
    RESTRICT_URL     = reverse('creme_core__restrict_entity_2_superusers')

    @staticmethod
    def _build_delete_url(entity):
        return reverse('creme_core__delete_entity', args=(entity.id,))

    @staticmethod
    def _build_restore_url(entity):
        return reverse('creme_core__restore_entity', args=(entity.id,))

    def test_json_entity_get01(self):
        user = self.login()
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        url = reverse('creme_core__entity_as_json', args=(rei.id,))
        self.assertGET(400, url)

        response = self.assertGET200(url, data={'fields': ['id']})
        self.assertEqual([[rei.id]], response.json())

        response = self.assertGET200(url, data={'fields': ['unicode']})
        self.assertListEqual([[str(rei)]], response.json())

        response = self.assertGET200(
            reverse('creme_core__entity_as_json', args=(nerv.id,)),
            data={'fields': ['id', 'unicode']},
        )
        self.assertEqual([[nerv.id, str(nerv)]], response.json())

        self.assertGET(400, reverse('creme_core__entity_as_json', args=(self.UNUSED_PK,)))
        self.assertGET403(url, data={'fields': ['id', 'unknown']})

    def test_json_entity_get02(self):
        self.login(is_superuser=False)

        nerv = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        self.assertGET(400, reverse('creme_core__entity_as_json', args=(nerv.id,)))

    def test_json_entity_get03(self):
        "No credentials for the basic CremeEntity, but real entity is viewable."
        user = self.login(
            is_superuser=False, allowed_apps=['creme_config'],  # Not 'creme_core'
            creatable_models=[FakeConfigEntity],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        e = FakeConfigEntity.objects.create(user=user, name='Nerv')
        response = self.assertGET200(
            reverse('creme_core__entity_as_json', args=(e.id,)),
            data={'fields': ['unicode']},
        )
        self.assertListEqual([[str(e)]], response.json())

    def test_get_creme_entities_repr01(self):
        user = self.login()

        with self.assertNoException():
            entity = CremeEntity.objects.create(user=user)

        response = self.assertGET200(
            reverse('creme_core__entities_summaries', args=(entity.id,)),
        )
        self.assertEqual('application/json', response['Content-Type'])

        self.assertListEqual(
            [{
                'id':   entity.id,
                'text': f'Creme entity: {entity.id}',
            }],
            response.json(),
        )

    def test_get_creme_entities_repr02(self):
        "Several entities, several ContentTypes, credentials."
        user = self.login(is_superuser=False)

        create_c = FakeContact.objects.create
        rei   = create_c(user=user,            first_name='Rei',   last_name='Ayanami')
        asuka = create_c(user=user,            first_name='Asuka', last_name='Langley')
        mari  = create_c(user=self.other_user, first_name='Mari',  last_name='Makinami')

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertTrue(user.has_perm_to_view(rei))
        self.assertFalse(user.has_perm_to_view(mari))

        unknown_id = self.UNUSED_PK
        self.assertFalse(CremeEntity.objects.filter(id=unknown_id))

        response = self.assertGET200(reverse(
            'creme_core__entities_summaries',
            args=(f'{mari.id},{rei.id},{nerv.id},{unknown_id},{asuka.id}',),
        ))

        self.assertListEqual(
            [
                {'id': mari.id,  'text': _('Entity #{id} (not viewable)').format(id=mari.id)},
                {'id': rei.id,   'text': str(rei)},
                {'id': nerv.id,  'text': str(nerv)},
                {'id': asuka.id, 'text': str(asuka)},
            ],
            response.json(),
        )

    def test_get_sanitized_html_field(self):
        user = self.login()
        entity = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertGET409(
            reverse('creme_core__sanitized_html_field', args=(entity.id, 'unknown')),
        )

        # Not an UnsafeHTMLField
        self.assertGET409(
            reverse('creme_core__sanitized_html_field', args=(entity.id, 'name')),
        )

        # NB: test with valid field in 'emails' app.

    def test_delete_dependencies_to_str(self):
        from creme.creme_core.views.entity import EntityDeletionMixin

        self.assertEqual(3, EntityDeletionMixin.dependencies_limit)

        class TestMixin(EntityDeletionMixin):
            dependencies_limit = 4

        dep_2_str = TestMixin().dependencies_to_str

        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity01 = create_orga(name='Nerv')
        entity01_msg = _('«{object}» ({model})').format(
            object=entity01.name,
            model=FakeOrganisation._meta.verbose_name,
        )
        self.assertEqual(
            entity01_msg,
            dep_2_str(dependencies=[entity01], user=user),
        )

        entity02 = create_orga(name='Seele')
        entity02_msg = _('«{object}» ({model})').format(
            object=entity02.name,
            model=FakeOrganisation._meta.verbose_name,
        )
        self.assertEqual(
            f'{entity01_msg}, {entity02_msg}',
            dep_2_str(dependencies=[entity01, entity02], user=user),
        )

        entity03 = create_orga(user=self.other_user, name='Acme#1')
        self.assertEqual(
            ', '.join([
                entity01_msg, entity02_msg,
                ngettext(
                    '{count} not viewable entity',
                    '{count} not viewable entities',
                    1
                ).format(count=1),
            ]),
            dep_2_str(dependencies=[entity01, entity03, entity02], user=user),
        )

        entity04 = create_orga(user=self.other_user, name='Acme#2')
        self.assertEqual(
            ', '.join([
                entity01_msg, entity02_msg,
                ngettext(
                    '{count} not viewable entity',
                    '{count} not viewable entities',
                    2
                ).format(count=2),
            ]),
            dep_2_str(dependencies=[entity01, entity03, entity02, entity04], user=user),
        )

        # rtype = RelationType.objects.first()
        rtype = RelationType.objects.filter(id__contains='-subject_').first()
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        rel01 = create_rel(subject_entity=entity01, object_entity=entity02)
        self.assertEqual(
            f'{rtype.predicate} «{entity02.name}»',
            dep_2_str(dependencies=[rel01], user=user),
        )
        self.assertEqual(
            '',
            dep_2_str(dependencies=[rel01.symmetric_relation], user=user),
        )
        self.assertEqual(
            f'{rtype.predicate} «{entity02.name}»',
            dep_2_str(dependencies=[rel01, rel01.symmetric_relation], user=user),
        )

        rel02 = create_rel(subject_entity=entity01, object_entity=entity03)
        self.assertEqual(
            f'{rtype.predicate} «{entity02.name}», '
            f'{rtype.predicate} «{settings.HIDDEN_VALUE}»',
            dep_2_str(dependencies=[rel02, rel01], user=user),
        )

        sector1, sector2 = FakeSector.objects.all()[:2]
        self.assertEqual(
            f'{sector1}, {sector2}',
            dep_2_str(dependencies=[sector1, sector2], user=user),
        )

        TestMixin.dependencies_limit = 2
        self.assertEqual(
            f'{entity01_msg}, {entity02_msg}…',
            dep_2_str(dependencies=[entity01, entity03, entity02], user=user),
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity01(self):
        "is_deleted=False -> trash."
        user = self.login()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        self.assertTrue(hasattr(entity, 'is_deleted'))
        self.assertIs(entity.is_deleted, False)
        self.assertGET200(entity.get_edit_absolute_url())

        absolute_url = entity.get_absolute_url()
        edit_url = entity.get_edit_absolute_url()

        response = self.assertGET200(absolute_url)
        self.assertContains(response, str(entity))
        self.assertContains(response, edit_url)

        url = self._build_delete_url(entity)
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

        self.assertGET403(edit_url)

        response = self.assertGET200(absolute_url)
        self.assertContains(response, str(entity))
        self.assertNotContains(response, edit_url)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity02(self):
        "is_deleted=True -> real deletion."
        user = self.login()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertDoesNotExist(entity)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity03(self):
        "No DELETE credentials."
        self.login(is_superuser=False)

        entity = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        self.assertPOST403(self._build_delete_url(entity))
        entity = self.assertStillExists(entity)
        self.assertFalse(entity.is_deleted)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entity_disabled01(self):
        "Deletion is disabled in settings."
        self.login()

        entity = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        url = self._build_delete_url(entity)

        self.assertPOST200(url, follow=True)
        entity = self.assertStillExists(entity)
        self.assertTrue(entity.is_deleted)

        response = self.client.post(url)
        self.assertStillExists(entity)
        self.assertContains(
            response,
            _(
                '«{entity}» can not be deleted because the deletion has '
                'been disabled by the administrator.'
            ).format(entity=entity),
            status_code=409,
            html=True,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entity_disabled02(self):
        "Logged as staff."
        self.login(is_staff=True)

        entity = FakeOrganisation.objects.create(
            user=self.other_user, name='Nerv', is_deleted=True,
        )

        self.assertPOST200(self._build_delete_url(entity), follow=True)
        self.assertDoesNotExist(entity)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity_dependencies01(self):
        "Relations (not internal ones) & properties are deleted correctly."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity01 = create_orga(name='Nerv', is_deleted=True)
        entity02 = create_orga(name='Seele')
        entity03 = create_orga(name='Neo tokyo')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_linked', 'is linked to'),
            ('test-object_linked',  'is linked to'),
            is_custom=True,
        )[0]
        rtype2 = create_rtype(
            ('test-subject_provides', 'provides'),
            ('test-object_provides',  'provided by'),
            is_custom=False,
        )[0]
        create_rel = partial(Relation.objects.create, user=user, subject_entity=entity01)
        rel1 = create_rel(type=rtype1, object_entity=entity02)
        rel2 = create_rel(type=rtype2, object_entity=entity03)
        rel3 = create_rel(type=rtype2, object_entity=entity03, subject_entity=entity02)

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_eva', text='has eva',
        )
        create_prop = partial(CremeProperty.objects.create, type=ptype)
        prop1 = create_prop(creme_entity=entity01)
        prop2 = create_prop(creme_entity=entity02)

        hlines_ids = [*HistoryLine.objects.values_list('id', flat=True)]
        self.assertPOST200(self._build_delete_url(entity01), follow=True)

        self.assertDoesNotExist(entity01)
        self.assertStillExists(entity02)
        self.assertStillExists(entity03)

        self.assertDoesNotExist(rel1)
        self.assertDoesNotExist(rel2)
        self.assertStillExists(rel3)

        self.assertDoesNotExist(prop1)
        self.assertStillExists(prop2)

        self.assertSetEqual(
            {
                history.TYPE_RELATION_DEL,
                history.TYPE_SYM_REL_DEL,
                history.TYPE_PROP_DEL,
                history.TYPE_DELETION,
            },
            {
                *HistoryLine.objects
                            .exclude(id__in=hlines_ids)
                            .values_list('type', flat=True),
            },
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity_dependencies02(self):  # TODO: detect dependencies when trashing ??
        "Dependencies problem (with internal Relations)."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity01 = create_orga(name='Nerv', is_deleted=True)
        entity02 = create_orga(name='Seele')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_daughter', 'is a daughter of'),
            ('test-object_daughter',  'has a daughter'),
            is_internal=True,
        )[0]
        Relation.objects.create(
            user=user, type=rtype, subject_entity=entity01, object_entity=entity02,
        )

        response = self.assertPOST409(self._build_delete_url(entity01), follow=True)
        self.assertTemplateUsed(response, 'creme_core/conflict_error.html')
        self.assertStillExists(entity01)
        self.assertStillExists(entity02)

        with self.assertNoException():
            msg = response.context['error_message']

        self.assertEqual(
            _(
                '«{entity}» can not be deleted because of its '
                'dependencies ({dependencies}).'
            ).format(
                entity=entity01.name,
                dependencies=f'is a daughter of «{entity02.name}»',
            ),
            msg,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity_ajax01(self):
        "is_deleted=False -> trash (AJAX version)."
        user = self.login()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        response = self.assertPOST200(
            self._build_delete_url(entity),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        with self.assertNoException():
            entity = self.refresh(entity)

        self.assertIs(entity.is_deleted, True)

        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            FakeOrganisation.get_lv_absolute_url().encode(),
            response.content,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity_ajax02(self):
        "is_deleted=True -> real deletion(AJAX version)."
        user = self.login()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        response = self.assertPOST200(
            self._build_delete_url(entity),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertDoesNotExist(entity)

        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            FakeOrganisation.get_lv_absolute_url().encode(),
            response.content,
        )

    @parameterized.expand([
        (True, ),
        (False, ),
    ])
    def test_delete_entity_auxiliary(self, deletion_allowed):
        with override_settings(ENTITIES_DELETION_ALLOWED=deletion_allowed):
            user = self.login()
            invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
            line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice)

            self.assertPOST200(self._build_delete_url(line), follow=True)
            self.assertDoesNotExist(line)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entities(self):
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for __ in range(2))
        entity03, entity04 = (create_entity(is_deleted=True) for __ in range(2))

        url = self.DEL_ENTITIES_URL
        self.assertPOST404(url)
        self.assertPOST(400, url, data={'ids': ''})
        self.assertPOST(400, url, data={'ids': 'notanint'})

        data = {'ids': f'{entity01.id},{entity02.id},{entity03.id}'}
        self.assertGET405(url, data=data)

        response = self.assertPOST200(url, data=data)
        self.assertEqual(response.content.decode(), _('Operation successfully completed'))

        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        entity02 = self.get_object_or_fail(CremeEntity, pk=entity02.id)
        self.assertTrue(entity02.is_deleted)

        self.assertDoesNotExist(entity03)
        self.assertStillExists(entity04)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entities_missing(self):
        "Some entities do not exist."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for __ in range(2))

        response = self.assertPOST404(
            self.DEL_ENTITIES_URL,
            data={'ids': f'{entity01.id},{entity02.id + 1},'},
        )

        self.assertDictEqual(
            {
                'count': 2,
                'errors': [
                    ngettext(
                        "{count} entity doesn't exist or has been removed.",
                        "{count} entities don't exist or have been removed.",
                        1
                    ).format(count=1),
                ],
            },
            response.json(),
        )

        entity01 = self.get_object_or_fail(CremeEntity, pk=entity01.id)
        self.assertTrue(entity01.is_deleted)

        self.get_object_or_fail(CremeEntity, pk=entity02.id)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entities_not_allowed(self):
        "Some entities deletion is not allowed."
        user = self.login(is_superuser=False)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed   = CremeEntity.objects.create(user=user)

        response = self.assertPOST403(
            self.DEL_ENTITIES_URL,
            data={'ids': f'{forbidden.id},{allowed.id},'},
        )

        self.assertDictEqual(
            {
                'count': 2,
                'errors': [
                    _('{entity} : <b>Permission denied</b>').format(
                        entity=forbidden.allowed_str(user),
                    ),
                ],
            },
            response.json(),
        )

        allowed = self.get_object_or_fail(CremeEntity, pk=allowed.id)
        self.assertTrue(allowed.is_deleted)

        self.get_object_or_fail(CremeEntity, pk=forbidden.id)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entities_disabled01(self):
        "Deletion is disabled in settings."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for __ in range(2))

        url = self.DEL_ENTITIES_URL
        data = {'ids': f'{entity01.id},{entity02.id}'}
        response1 = self.assertPOST200(url, data=data)
        self.assertEqual(response1.content.decode(), _('Operation successfully completed'))

        entity01 = self.assertStillExists(entity01)
        self.assertTrue(entity01.is_deleted)

        self.assertStillExists(entity02)

        # ---
        response2 = self.assertPOST409(url, data=data)
        msg = _(
            '«{entity}» can not be deleted because the deletion has been '
            'disabled by the administrator.'
        )
        self.assertDictEqual(
            {
                'count': 2,
                'errors': [
                    msg.format(entity=entity01),
                    msg.format(entity=entity02),
                ],
            },
            response2.json(),
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entities_disabled02(self):
        "Logged as staff."
        user = self.login(is_staff=True)

        create_entity = partial(CremeEntity.objects.create, user=user, is_deleted=True)
        entity01, entity02 = (create_entity() for __ in range(2))

        response = self.assertPOST200(
            self.DEL_ENTITIES_URL, data={'ids': f'{entity01.id},{entity02.id}'},
        )
        self.assertEqual(response.content.decode(), _('Operation successfully completed'))
        self.assertDoesNotExist(entity01)
        self.assertDoesNotExist(entity02)

    # TODO ??
    # def test_delete_entities_dependencies(self):
    #     self.login()
    #
    #     create_entity = partial(CremeEntity.objects.create, user=self.user)
    #     entity01 = create_entity()
    #     entity02 = create_entity()
    #     entity03 = create_entity() #not linked => can be deleted
    #
    #     rtype, srtype = RelationType.create(('test-subject_linked', 'is linked to'),
    #                                         ('test-object_linked',  'is linked to')
    #                                        )
    #     Relation.objects.create(
    #           user=self.user, type=rtype, subject_entity=entity01, object_entity=entity02,
    #     )
    #
    #     self.assertPOST(400, self.DEL_ENTITIES_URL,
    #                     data={'ids': '%s,%s,%s,' % (entity01.id, entity02.id, entity03.id)}
    #                    )
    #     self.assertEqual(
    #           2, CremeEntity.objects.filter(pk__in=[entity01.id, entity02.id]).count()
    #     )
    #     self.assertFalse(CremeEntity.objects.filter(pk=entity03.id))

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_trash_view01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        response = self.assertGET200(reverse('creme_core__trash'))
        self.assertTemplateUsed(response, 'creme_core/trash.html')

        doc = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(doc, brick=TrashBrick)
        self.assertInstanceLink(brick_node, entity1)
        self.assertNoInstanceLink(brick_node, entity2)
        self.assertBrickHasAction(
            brick_node, url=self._build_delete_url(entity1), action_type='delete',
        )

        self.assertNotContains(
            response,
            _('The definitive deletion has been disabled by the administrator.'),
            html=True,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_trash_view02(self):
        "Definitive deletion is disabled."
        user = self.login()
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        response = self.assertGET200(reverse('creme_core__trash'))
        doc = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(doc, brick=TrashBrick)
        self.assertInstanceLink(brick_node, entity)
        self.assertBrickHasNoAction(
            brick_node, url=self._build_delete_url(entity),
        )

        self.assertContains(
            response,
            _('The definitive deletion has been disabled by the administrator.'),
            html=True,
        )

    def test_restore_entity01(self):
        "No trashed."
        user = self.login()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        url = self._build_restore_url(entity)
        self.assertGET405(url)
        self.assertPOST404(url)

    def test_restore_entity02(self):
        user = self.login()

        entity = FakeOrganisation.objects.create(
            user=user, name='Nerv', is_deleted=True,
        )
        url = self._build_restore_url(entity)

        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_absolute_url())

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity03(self):
        user = self.login()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)
        self.assertPOST200(
            self._build_restore_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash01(self):
        user = self.login(is_superuser=False, allowed_apps=('creme_core',))  # 'persons'

        create_contact = partial(FakeContact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf')
        contact3 = create_contact(first_name='Nora',     last_name='Alend', user=self.other_user)

        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_delete(contact3))

        url = self.EMPTY_TRASH_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/forms/confirmation.html')

        ctxt = response.context
        self.assertEqual(_('Empty the trash'), ctxt.get('title'))
        self.assertEqual(
            _(
                'Are you sure you want to delete definitely '
                'all the entities in the trash?'
            ),
            ctxt.get('message'),
        )

        response = self.assertPOST200(url)
        self.assertTemplateUsed(response, 'creme_core/job/trash-cleaning-popup.html')

        jobs = Job.objects.filter(type_id=trash_cleaner_type.id)
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        self.assertEqual(self.user, job.user)
        self.assertEqual(Job.STATUS_WAIT, job.status)
        self.assertIsNone(job.error)
        self.assertIsNone(job.last_run)

        command = self.get_object_or_fail(TrashCleaningCommand, job=job)
        self.assertEqual(user, command.user)
        self.assertEqual(0, command.deleted_count)
        self.assertListEqual([], trash_cleaner_type.get_stats(job))

        progress1 = trash_cleaner_type.progress(job)
        self.assertIsNone(progress1.percentage)
        self.assertEqual(
            ngettext(
                '{count} entity deleted.', '{count} entities deleted.', 0,
            ).format(count=0),
            progress1.label,
        )

        trash_cleaner_type.execute(job)
        self.assertFalse(FakeContact.objects.filter(id__in=[contact1.id, contact2.id]))
        self.assertStillExists(contact3)
        self.assertFalse(EntityJobResult.objects.filter(job=job))
        self.assertEqual(2, self.refresh(command).deleted_count)

        job = self.refresh(job)
        self.assertListEqual(
            [
                ngettext(
                    '{count} entity deleted.', '{count} entities deleted.', 2,
                ).format(count=2),
            ],
            trash_cleaner_type.get_stats(job),
        )

        progress2 = trash_cleaner_type.progress(job)
        self.assertIsNone(progress2.percentage)
        self.assertEqual(
            ngettext(
                '{count} entity deleted.',
                '{count} entities deleted.',
                2
            ).format(count=2),
            progress2.label,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash02(self):
        "Dependencies problem."
        user = self.login()

        create_contact = partial(
            FakeContact.objects.create,
            user=user, last_name='Doe', is_deleted=True,
        )
        entity01 = create_contact(first_name='#1')
        entity02 = create_contact(first_name='#2')
        entity03 = create_contact(first_name='#3')  # Not linked => can be deleted
        entity04 = create_contact(first_name='#4', is_deleted=False)
        entity05 = FakeOrganisation.objects.create(
            user=user, name='Acme', is_deleted=True,
        )  # Not linked => can be deleted

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_linked', 'is linked to'),
            ('test-object_linked',  'is linked to'),
            is_internal=True,
        )[0]
        Relation.objects.create(
            user=user, type=rtype, subject_entity=entity01, object_entity=entity02,
        )

        self.assertPOST200(self.EMPTY_TRASH_URL)

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertStillExists(entity01)
        self.assertStillExists(entity02)
        self.assertDoesNotExist(entity03)
        self.assertStillExists(entity04)
        self.assertDoesNotExist(entity05)

        jresults = {jr.entity_id: jr for jr in EntityJobResult.objects.filter(job=job)}
        self.assertEqual(2, len(jresults), jresults)

        jresult1 = jresults.get(entity01.id)
        self.assertIsNotNone(jresult1)
        self.assertEqual(entity01.entity_type, jresult1.entity_ctype)
        self.assertListEqual(
            [_('Can not be deleted because of its dependencies.')],
            jresult1.messages,
        )

        self.assertIn(entity02.id, jresults)

        result_bricks = trash_cleaner_type.results_bricks
        self.assertEqual(1, len(result_bricks))
        self.assertIsInstance(result_bricks[0], EntityJobErrorsBrick)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash03(self):
        "Credentials on specific ContentType."
        # NB: can delete ESET_OWN
        user = self.login(is_superuser=False, allowed_apps=('creme_core',))
        other_user = self.other_user

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
            ctype=FakeOrganisation,
        )

        create_contact = partial(FakeContact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf', user=other_user)
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_delete(contact2))

        create_orga = partial(FakeOrganisation.objects.create, user=user, is_deleted=True)
        orga1 = create_orga(name='Nerv')
        orga2 = create_orga(name='Seele', is_deleted=False)
        orga3 = create_orga(name='Neo tokyo', user=other_user)
        self.assertTrue(user.has_perm_to_delete(orga1))
        self.assertTrue(user.has_perm_to_delete(orga2))  # But not deleted
        self.assertTrue(user.has_perm_to_delete(orga3))

        self.assertPOST200(self.EMPTY_TRASH_URL)
        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)

        trash_cleaner_type.execute(job)
        self.assertDoesNotExist(contact1)
        self.assertStillExists(contact2)

        self.assertStillExists(orga2)
        self.assertDoesNotExist(orga1)
        self.assertDoesNotExist(orga3)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash04(self):
        "Existing job."
        user = self.login()
        job1 = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_WAIT,
        )
        TrashCleaningCommand.objects.create(user=user, job=job1)
        self.assertContains(
            self.client.post(self.EMPTY_TRASH_URL),
            _('A job is already cleaning the trash.'),
            status_code=409,
        )

        # Finished job
        job1.status = Job.STATUS_OK
        job1.save()
        self.assertPOST200(self.EMPTY_TRASH_URL)
        self.assertDoesNotExist(job1)

        command = self.get_object_or_fail(TrashCleaningCommand, user=user)
        job2 = command.job
        self.assertNotEqual(job1, job2)
        self.assertEqual(Job.STATUS_WAIT, job2.status)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_empty_trash_deletion_disabled(self):
        "Deletion is disabled."
        self.login()
        self.assertContains(
            self.client.post(self.EMPTY_TRASH_URL),
            _('The definitive deletion has been disabled by the administrator.'),
            status_code=409,
            html=True,
        )

    @staticmethod
    def _build_finish_cleaner_url(job):
        return reverse('creme_core__finish_trash_cleaner', args=(job.id,))

    def test_finish_cleaner01(self):
        user = self.login()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        com = TrashCleaningCommand.objects.create(user=user, job=job)

        url = self._build_finish_cleaner_url(job)
        self.assertGET405(url)
        self.assertPOST200(url)

        self.assertDoesNotExist(job)
        self.assertDoesNotExist(com)

    def test_finish_cleaner02(self):
        "Other user's job."
        self.login()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=self.other_user,
            status=Job.STATUS_OK,
        )

        self.assertPOST403(self._build_finish_cleaner_url(job))

    def test_finish_cleaner03(self):
        "Job not finished."
        user = self.login()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_WAIT,
        )

        self.assertPOST409(self._build_finish_cleaner_url(job))

    def test_finish_cleaner04(self):
        "Not cleaner job."
        user = self.login()
        job = Job.objects.create(
            type_id=reminder_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        self.assertPOST404(self._build_finish_cleaner_url(job))

    def test_finish_cleaner05(self):
        "Job with errors."
        user = self.login()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        # EntityJobResult.objects.create(job=job, entity=nerv)
        EntityJobResult.objects.create(job=job, real_entity=nerv)

        url = self._build_finish_cleaner_url(job)
        redir_url = job.get_absolute_url()
        response1 = self.client.post(url)
        self.assertRedirects(response1, redir_url)
        self.assertStillExists(job)

        # AJAX version
        response2 = self.assertPOST200(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(redir_url, response2.content.decode())

    @staticmethod
    def _build_test_get_info_fields_url(model):
        ct = ContentType.objects.get_for_model(model)

        return reverse('creme_core__entity_info_fields', args=(ct.id,))

    def test_get_info_fields01(self):
        self.login()

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeContact))
        json_data = response.json()
        self.assertIsList(json_data)
        self.assertTrue(all(isinstance(elt, list) for elt in json_data))
        self.assertTrue(all(len(elt) == 2 for elt in json_data))

        names = [
            'created', 'modified', 'first_name', 'last_name', 'description',
            'phone', 'mobile', 'email', 'birthday', 'url_site',
            'is_a_nerd', 'loves_comics',
        ]
        self.assertFalse({*names}.symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_('First name'), json_dict['first_name'])
        self.assertEqual(
            _('{field} [CREATION]').format(field=_('Last name')),
            json_dict['last_name'],
        )

    def test_get_info_fields02(self):
        self.login()

        response = self.client.get(self._build_test_get_info_fields_url(FakeOrganisation))
        json_data = response.json()

        names = [
            'created', 'modified', 'name', 'description', 'url_site',
            'phone', 'email', 'creation_date',  'subject_to_vat', 'capital',
        ]
        self.assertFalse({*names}.symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

        json_dict = dict(json_data)
        self.assertEqual(_('Description'), json_dict['description'])
        self.assertEqual(
            _('{field} [CREATION]').format(field=_('Name')),
            json_dict['name'],
        )

    def test_get_info_fields03(self):
        "With FieldsConfig"
        self.login()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('birthday', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(self._build_test_get_info_fields_url(FakeContact))
        json_data = response.json()
        names = [
            'created', 'modified', 'first_name', 'last_name', 'description',
            'phone', 'mobile', 'email', 'url_site', 'is_a_nerd', 'loves_comics',
            # 'birthday', #<===
        ]
        self.assertFalse({*names}.symmetric_difference({name for name, vname in json_data}))
        self.assertEqual(len(names), len(json_data))

    def test_clone01(self):
        user = self.login()
        url = self.CLONE_URL

        first_name = 'Mario'
        mario = FakeContact.objects.create(user=user, first_name=first_name, last_name='Bros')
        count = FakeContact.objects.count()

        self.assertPOST404(url, data={})
        self.assertPOST404(url, data={'id': 0})
        self.assertEqual(count, FakeContact.objects.count())

        # ---
        response = self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertEqual(count + 1, FakeContact.objects.count())

        with self.assertNoException():
            mario, oiram = FakeContact.objects.filter(first_name=first_name).order_by('created')

        self.assertEqual(mario.last_name, oiram.last_name)
        self.assertRedirects(response, oiram.get_absolute_url())

    def test_clone02(self):
        "Not logged."
        url = self.CLONE_URL

        mario = FakeContact.objects.create(
            user=get_user_model().objects.first(),
            first_name='Mario', last_name='Bros',
        )

        response = self.assertPOST200(url, data={'id': mario.id}, follow=True)
        self.assertRedirects(
            response,
            '{login_url}?next={clone_url}'.format(
                login_url=reverse(settings.LOGIN_URL),
                clone_url=url,
            )
        )

    def test_clone03(self):
        "Not superuser with right credentials."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])
        self._set_all_creds_except_one(None)

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertPOST200(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone04(self):
        "Not superuser without creation credentials => error."
        self.login(is_superuser=False)
        self._set_all_creds_except_one(None)

        mario = FakeContact.objects.create(
            user=self.other_user, first_name='Mario', last_name='Bros',
        )
        count = FakeContact.objects.count()
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count, FakeContact.objects.count())

    def test_clone05(self):
        "Not superuser without VIEW credentials => error."
        self.login(is_superuser=False, creatable_models=[FakeContact])
        self._set_all_creds_except_one(EntityCredentials.VIEW)

        mario = FakeContact.objects.create(
            user=self.other_user, first_name='Mario', last_name='Bros',
        )
        count = FakeContact.objects.count()
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count, FakeContact.objects.count())

    def test_clone06(self):
        """Not clonable entity type."""
        user = self.login()

        image = FakeImage.objects.create(user=user, name='Img1')
        count = FakeImage.objects.count()
        self.assertPOST404(self.CLONE_URL, data={'id': image.id}, follow=True)
        self.assertEqual(count, FakeImage.objects.count())

    def test_clone07(self):
        "Ajax query."
        user = self.login()

        first_name = 'Mario'
        mario = FakeContact.objects.create(
            user=user, first_name=first_name, last_name='Bros',
        )
        count = FakeContact.objects.count()

        response = self.assertPOST200(
            self.CLONE_URL,
            data={'id': mario.id}, follow=True,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(count + 1, FakeContact.objects.count())

        with self.assertNoException():
            mario, oiram = FakeContact.objects.filter(
                first_name=first_name,
            ).order_by('created')

        self.assertEqual(mario.last_name, oiram.last_name)
        self.assertEqual(oiram.get_absolute_url(), response.content.decode())

    def _assert_detailview(self, response, entity):
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, entity.get_absolute_url())

    def test_search_and_view01(self):
        user = self.login()

        phone = '123456789'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone',
            'value':  phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654', mobile=phone)
        self.assertGET404(url, data=data)

        onizuka.phone = phone
        onizuka.save()
        self.assertPOST405(url, data=data)
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view02(self):
        user = self.login()

        phone = '999999999'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone,mobile',
            'value':  phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka  = create_contact(first_name='Eikichi', last_name='Onizuka', mobile=phone)
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view03(self):
        user = self.login()

        phone = '696969'
        url = self.SEARCHNVIEW_URL
        data = {
            'models':  'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'phone,mobile',
            'value': phone,
        }
        self.assertGET404(url, data=data)

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji', last_name='Danma', phone='987654')

        onibaku = FakeOrganisation.objects.create(user=user, name='Onibaku', phone=phone)
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

        onizuka.mobile = phone
        onizuka.save()
        self._assert_detailview(self.client.get(url, data=data, follow=True), onizuka)

    def test_search_and_view04(self):
        "Errors."
        user = self.login()

        url = self.SEARCHNVIEW_URL
        base_data = {
            'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'mobile,phone',
            'value':  '696969',
        }
        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Eikichi', last_name='Onizuka', mobile='55555')
        create_contact(first_name='Ryuji',   last_name='Danma', phone='987654')
        FakeOrganisation.objects.create(user=user, name='Onibaku', phone='54631357')

        self.assertGET404(url, data={**base_data, 'models': 'foo-bar'})
        self.assertGET404(url, data={**base_data, 'models': 'foobar'})
        self.assertGET404(url, data={**base_data, 'values': ''})
        self.assertGET404(url, data={**base_data, 'models': ''})
        self.assertGET404(url, data={**base_data, 'fields': ''})
        # Not CremeEntity
        self.assertGET404(url, data={**base_data, 'models': 'persons-civility'})

    def test_search_and_view05(self):
        "Credentials."
        user = self.login(is_superuser=False)

        phone = '44444'
        url = self.SEARCHNVIEW_URL
        data = {
            'models': 'creme_core-fakecontact,creme_core-fakeorganisation',
            'fields': 'phone,mobile',
            'value':  phone,
        }

        create_contact = FakeContact.objects.create
        # Phone is OK but not readable
        onizuka = create_contact(
            user=self.other_user, first_name='Eikichi', last_name='Onizuka', mobile=phone,
        )
        # Phone is KO
        ryuji = create_contact(
            user=user, first_name='Ryuji', last_name='Danma', phone='987654',
        )

        onibaku = FakeOrganisation.objects.create(
            user=user, name='Onibaku', phone=phone,
        )  # Phone OK and readable

        has_perm = user.has_perm_to_view
        self.assertFalse(has_perm(onizuka))
        self.assertTrue(has_perm(ryuji))
        self.assertTrue(has_perm(onibaku))
        self._assert_detailview(self.client.get(url, data=data, follow=True), onibaku)

    def test_search_and_view06(self):
        "App credentials."
        user = self.login(is_superuser=False, allowed_apps=['documents'])  # Not 'creme_core'

        phone = '31337'
        data = {
            'models': 'creme_core-fakecontact',
            'fields': 'phone',
            'value':  phone,
        }
        # Would match if apps was allowed
        FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka', phone=phone,
        )
        self.assertGET403(self.SEARCHNVIEW_URL, data=data)

    def test_search_and_view07(self):
        "FieldsConfig."
        self.login()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone',  {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(
            self.SEARCHNVIEW_URL,
            data={
                'models': 'creme_core-fakecontact',
                'fields': 'phone',
                'value':  '123456789',
            },
        )

    def test_search_and_view08(self):
        "Not logged."
        url = self.SEARCHNVIEW_URL
        models = 'creme_core-fakecontact'
        fields = 'phone'
        value = '123456789'
        response = self.assertGET200(
            url, follow=True,
            data={
                'models': models,
                'fields': fields,
                'value':  value,
            },
        )
        # NB: problem with order (only python3.5- ?)
        # self.assertRedirects(
        #     response,
        #     '{login_url}?next={search_url}'
        #     '%3Fmodels%3Dcreme_core-fakecontact'
        #     '%26fields%3Dphone'
        #     '%26value%3D123456789'.format(
        #         login_url=reverse(settings.LOGIN_URL),
        #         search_url=url,
        #     )
        # )
        self.assertEqual(1, len(response.redirect_chain))

        parsed_url = urlparse(response.redirect_chain[0][0])
        self.assertEqual(reverse(settings.LOGIN_URL), parsed_url.path)

        next_param = parsed_url.query
        self.assertStartsWith(next_param, 'next=')
        self.assertURLEqual(
            f'{url}?models={models}&fields={fields}&value={value}',
            unquote(next_param[len('next='):]),
        )

    def test_restrict_entity_2_superusers01(self):
        user = self.login()
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )

        url = self.RESTRICT_URL
        data = {'id': contact.id}
        self.assertGET405(url, data=data)
        self.assertPOST200(url, data=data)

        sandbox = self.refresh(contact).sandbox
        self.assertIsNotNone(sandbox)
        self.assertEqual(constants.UUID_SANDBOX_SUPERUSERS, str(sandbox.uuid))

        # Unset
        self.assertPOST200(url, data={**data, 'set': 'false'})
        self.assertIsNone(self.refresh(contact).sandbox)

    def test_restrict_entity_2_superusers02(self):
        "Entity already in a sandbox."
        user = self.login()
        sandbox = Sandbox.objects.create(type_id='creme_core-dont_care', user=user)
        contact = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Eikichi', last_name='Onizuka',
        )

        data = {'id': contact.id}
        self.assertPOST409(self.RESTRICT_URL, data=data)
        self.assertPOST409(self.RESTRICT_URL, data={**data, 'set': 'false'})

        self.assertEqual(sandbox, self.refresh(contact).sandbox)

    def test_restrict_entity_2_superusers03(self):
        "Unset entity with no sandbox."
        user = self.login()
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )
        self.assertPOST409(self.RESTRICT_URL, data={'id': contact.id, 'set': 'false'})

    def test_restrict_entity_2_superusers04(self):
        "Not super-user"
        user = self.login(is_superuser=False)
        contact = FakeContact.objects.create(
            user=user, first_name='Eikichi', last_name='Onizuka',
        )
        self.assertPOST403(self.RESTRICT_URL, data={'id': contact.id})
