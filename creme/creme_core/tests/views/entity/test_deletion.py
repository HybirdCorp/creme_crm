from functools import partial

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import EntityJobErrorsBrick, TrashBrick
from creme.creme_core.creme_jobs import reminder_type, trash_cleaner_type
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    EntityJobResult,
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    HistoryLine,
    Job,
    Relation,
    RelationType,
    SetCredentials,
    TrashCleaningCommand,
    history,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin, ViewsTestCase


class EntityViewsTestCase(BrickTestCaseMixin, ViewsTestCase):
    DEL_ENTITIES_URL = reverse('creme_core__delete_entities')
    EMPTY_TRASH_URL  = reverse('creme_core__empty_trash')

    @staticmethod
    def _build_delete_url(entity):
        return reverse('creme_core__delete_entity', args=(entity.id,))

    @staticmethod
    def _build_restore_url(entity):
        return reverse('creme_core__restore_entity', args=(entity.id,))

    def test_delete_dependencies_to_str(self):
        from creme.creme_core.views.entity import EntityDeletionMixin

        self.assertEqual(3, EntityDeletionMixin.dependencies_limit)

        class TestMixin(EntityDeletionMixin):
            dependencies_limit = 4

        dep_2_str = TestMixin().dependencies_to_str

        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        SetCredentials.objects.create(
            role=user.role,
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

        # other_user = self.other_user
        other_user = self.get_root_user()
        entity03 = create_orga(user=other_user, name='Acme#1')
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

        entity04 = create_orga(user=other_user, name='Acme#2')
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
        # user = self.login()
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        self.assertHasAttr(entity, 'is_deleted')
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
        # user = self.login()
        user = self.login_as_root_and_get()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertDoesNotExist(entity)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity03(self):
        "No DELETE credentials."
        # self.login(is_superuser=False)
        user = self.login_as_standard()
        self._set_all_creds_except_one(user=user, excluded=EntityCredentials.DELETE)

        # entity = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        self.assertPOST403(self._build_delete_url(entity))
        entity = self.assertStillExists(entity)
        self.assertFalse(entity.is_deleted)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entity_disabled01(self):
        "Deletion is disabled in settings."
        # self.login()
        self.login_as_root()

        # entity = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        entity = FakeOrganisation.objects.create(user=self.create_user(), name='Nerv')
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
        # self.login(is_staff=True)
        self.login_as_super(is_staff=True)

        entity = FakeOrganisation.objects.create(
            # user=self.other_user, name='Nerv', is_deleted=True,
            user=self.get_root_user(), name='Nerv', is_deleted=True,
        )

        self.assertPOST200(self._build_delete_url(entity), follow=True)
        self.assertDoesNotExist(entity)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entity_dependencies01(self):
        "Relations (not internal ones) & properties are deleted correctly."
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login()
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        response = self.assertPOST200(
            self._build_delete_url(entity),
            # HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            headers={'X-Requested-With': 'XMLHttpRequest'},
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
        # user = self.login()
        user = self.login_as_root_and_get()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        response = self.assertPOST200(
            self._build_delete_url(entity),
            # HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertDoesNotExist(entity)

        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            FakeOrganisation.get_lv_absolute_url().encode(),
            response.content,
        )

    @parameterized.expand([True, False])
    def test_delete_entity_auxiliary(self, deletion_allowed):
        with override_settings(ENTITIES_DELETION_ALLOWED=deletion_allowed):
            # user = self.login()
            user = self.login_as_root_and_get()
            invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
            line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice)

            self.assertPOST200(self._build_delete_url(line), follow=True)
            self.assertDoesNotExist(line)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_entities(self):
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login(is_superuser=False)
        user = self.login_as_standard()
        self._set_all_perms_on_own(user)

        # forbidden = CremeEntity.objects.create(user=self.other_user)
        forbidden = CremeEntity.objects.create(user=self.get_root_user())
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
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login(is_staff=True)
        user = self.login_as_super(is_staff=True)

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
        # user = self.login()
        user = self.login_as_root_and_get()

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
        # user = self.login()
        user = self.login_as_root_and_get()
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
        # user = self.login()
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        url = self._build_restore_url(entity)
        self.assertGET405(url)
        self.assertPOST404(url)

    def test_restore_entity02(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(
            user=user, name='Nerv', is_deleted=True,
        )
        url = self._build_restore_url(entity)

        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_absolute_url())

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity03(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)
        self.assertPOST200(
            # self._build_restore_url(entity), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            self._build_restore_url(entity), headers={'X-Requested-With': 'XMLHttpRequest'},
        )

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash01(self):
        # user = self.login(is_superuser=False, allowed_apps=('creme_core',))  # 'persons'
        user = self.login_as_standard(allowed_apps=('creme_core',))  # 'persons'
        self._set_all_perms_on_own(user)

        create_contact = partial(FakeContact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf')
        # contact3 = create_contact(first_name='Nora',     last_name='Alend', user=self.other_user)
        contact3 = create_contact(first_name='Nora', last_name='Alend', user=self.get_root_user())

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

        job = self.get_alone_element(Job.objects.filter(type_id=trash_cleaner_type.id))
        self.assertEqual(user, job.user)
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
        # user = self.login()
        user = self.login_as_root_and_get()

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

        result_brick = self.get_alone_element(trash_cleaner_type.results_bricks)
        self.assertIsInstance(result_brick, EntityJobErrorsBrick)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash03(self):
        "Credentials on specific ContentType."
        # NB: can delete ESET_OWN
        # user = self.login(is_superuser=False, allowed_apps=('creme_core',))
        user = self.login_as_standard(allowed_apps=('creme_core',))
        self._set_all_perms_on_own(user)
        # other_user = self.other_user
        other_user = self.get_root_user()

        SetCredentials.objects.create(
            role=user.role,
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
        # user = self.login()
        user = self.login_as_root_and_get()
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
        # self.login()
        self.login_as_root()
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
        # user = self.login()
        user = self.login_as_root_and_get()
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
        # self.login()
        self.login_as_root()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            # user=self.other_user,
            user=self.create_user(),
            status=Job.STATUS_OK,
        )

        self.assertPOST403(self._build_finish_cleaner_url(job))

    def test_finish_cleaner03(self):
        "Job not finished."
        # user = self.login()
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_WAIT,
        )

        self.assertPOST409(self._build_finish_cleaner_url(job))

    def test_finish_cleaner04(self):
        "Not cleaner job."
        # user = self.login()
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            type_id=reminder_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        self.assertPOST404(self._build_finish_cleaner_url(job))

    def test_finish_cleaner05(self):
        "Job with errors."
        # user = self.login()
        user = self.login_as_root_and_get()
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
        # response2 = self.assertPOST200(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response2 = self.assertPOST200(url, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(redir_url, response2.content.decode())
