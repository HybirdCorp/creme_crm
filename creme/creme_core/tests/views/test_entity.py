# -*- coding: utf-8 -*-

from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import CharField
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_config.forms import fields as config_fields
from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import EntityJobErrorsBrick, TrashBrick
from creme.creme_core.creme_jobs import reminder_type, trash_cleaner_type
from creme.creme_core.forms.bulk import (
    _CUSTOMFIELD_FORMAT,
    BulkDefaultEditForm,
)
from creme.creme_core.gui import bulk_update
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldBoolean,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldMultiEnum,
    CustomFieldString,
    EntityJobResult,
    FakeAddress,
    FakeContact,
    FakeDocument,
    FakeFileBag,
    FakeFileComponent,
    FakeFolder,
    FakeImage,
    FakeImageCategory,
    FakeOrganisation,
    FakePosition,
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
from creme.creme_core.views.entity import BulkUpdate, InnerEdition

from .base import BrickTestCaseMixin, ViewsTestCase


class EntityViewsTestCase(ViewsTestCase, BrickTestCaseMixin):
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

    def test_delete_entity02(self):
        "is_deleted=True -> real deletion."
        user = self.login()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertDoesNotExist(entity)

    def test_delete_entity03(self):
        "No DELETE credentials."
        self.login(is_superuser=False)

        entity = FakeOrganisation.objects.create(user=self.other_user, name='Nerv')
        self.assertPOST403(self._build_delete_url(entity))
        self.assertStillExists(entity)

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
        creat_rel = partial(Relation.objects.create, user=user, subject_entity=entity01)
        rel1 = creat_rel(type=rtype1, object_entity=entity02)
        rel2 = creat_rel(type=rtype2, object_entity=entity03)
        rel3 = creat_rel(type=rtype2, object_entity=entity03, subject_entity=entity02)

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

    def test_delete_entities01(self):
        "NB: for the deletion of auxiliary entities => see billing app."
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

    def test_delete_entities_missing(self):
        "Some entities doesn't exist."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        entity01, entity02 = (create_entity() for __ in range(2))

        response = self.assertPOST404(
            self.DEL_ENTITIES_URL,
            data={'ids': '{},{},'.format(entity01.id, entity02.id + 1)},
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

    # TODO ??
    # def test_delete_entities04(self):
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

    def test_trash_view(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        response = self.assertGET200(reverse('creme_core__trash'))
        self.assertTemplateUsed(response, 'creme_core/trash.html')

        doc = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(doc, TrashBrick.id_)
        self.assertInstanceLink(brick_node, entity1)
        self.assertNoInstanceLink(brick_node, entity2)

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

    def test_empty_trash01(self):
        user = self.login(is_superuser=False, allowed_apps=('creme_core',))  # 'persons'

        create_contact = partial(FakeContact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf')
        contact3 = create_contact(first_name='Nora',     last_name='Alend', user=self.other_user)

        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_delete(contact3))

        url = self.EMPTY_TRASH_URL
        # self.assertGET404(url)
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
        self.assertListEqual(
            [_('Can not be deleted because of its dependencies.')],
            jresult1.messages,
        )

        self.assertIn(entity02.id, jresults)

        result_bricks = trash_cleaner_type.results_bricks
        self.assertEqual(1, len(result_bricks))
        self.assertIsInstance(result_bricks[0], EntityJobErrorsBrick)

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
        EntityJobResult.objects.create(job=job, entity=nerv)

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
        "Not super user with right credentials."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])
        self._set_all_creds_except_one(None)

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertPOST200(self.CLONE_URL, data={'id': mario.id}, follow=True)

    def test_clone04(self):
        "Not super user without creation credentials => error."
        self.login(is_superuser=False)
        self._set_all_creds_except_one(None)

        mario = FakeContact.objects.create(
            user=self.other_user, first_name='Mario', last_name='Bros',
        )
        count = FakeContact.objects.count()
        self.assertPOST403(self.CLONE_URL, data={'id': mario.id}, follow=True)
        self.assertEqual(count, FakeContact.objects.count())

    def test_clone05(self):
        "Not super user without VIEW credentials => error."
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
        # Phone is OK and but not readable
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


class _BulkEditTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._original_bulk_update_registry = bulk_update.bulk_update_registry

    @staticmethod
    def get_cf_values(cf, entity):
        return cf.value_class.objects.get(custom_field=cf, entity=entity)

    @staticmethod
    def create_image(name, user, categories=()):
        image = FakeImage.objects.create(user=user, name=name)
        image.categories.set(categories)

        return image


class BulkUpdateTestCase(_BulkEditTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        BulkUpdate.bulk_update_registry = bulk_update._BulkUpdateRegistry()

        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)
        cls.contact_bulk_status = bulk_update.bulk_update_registry.status(FakeContact)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        BulkUpdate.bulk_update_registry = cls._original_bulk_update_registry

    def setUp(self):
        super().setUp()
        contact_status = BulkUpdate.bulk_update_registry.status(FakeContact)

        self._contact_innerforms = contact_status._innerforms
        BulkUpdate.bulk_update_registry.status(FakeContact)._innerforms = {}

        self._contact_excludes = contact_status.excludes
        BulkUpdate.bulk_update_registry.status(FakeContact).excludes = set()

    def tearDown(self):
        super().tearDown()
        contact_status = BulkUpdate.bulk_update_registry.status(FakeContact)
        contact_status._innerforms = self._contact_innerforms
        contact_status.excludes = self._contact_excludes

    def _build_update_url(self, *, field=None, ids=(), ctype=None):
        if ctype is None:
            ctype = self.contact_ct

        url = (
            reverse('creme_core__bulk_update', args=(ctype.id, field))
            if field else
            reverse('creme_core__bulk_update', args=(ctype.id,))
        )
        return f"{url}?entities={'.'.join(str(id) for id in ids)}" if ids else url

    def create_2_contacts_n_url(self, mario_kwargs=None, luigi_kwargs=None, field='first_name'):
        create_contact = partial(FakeContact.objects.create, user=self.user)
        mario = create_contact(first_name='Mario', last_name='Bros', **(mario_kwargs or {}))
        luigi = create_contact(first_name='Luigi', last_name='Bros', **(luigi_kwargs or {}))

        return mario, luigi, self._build_update_url(field=field, ids=(mario.id, luigi.id))

    def test_regular_field_error01(self):
        self.login()

        build_url = self._build_update_url

        response = self.assertGET(400, build_url(field='unknown'))
        self.assertContains(
            response,
            "The field Test Contact.unknown doesn't exist",
            status_code=400,
        )

        cfield_name = _CUSTOMFIELD_FORMAT.format(44500124)
        response = self.assertGET(400, build_url(field=cfield_name))
        self.assertContains(
            response,
            "The field Test Contact.customfield-44500124 doesn't exist",
            status_code=400,
        )

    def test_regular_field_error02(self):
        "Not entities."
        self.login()
        self.assertGET409(self.build_bulkupdate_url(FakeSector))
        self.assertGET409(self.build_bulkupdate_url(FakeSector, 'title'))

    def test_regular_field(self):
        user = self.login()

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        build_url = self._build_update_url
        url = build_url(field='first_name')
        response = self.assertGET200(f'{url}?entities={mario.id}')
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Multiple update'),        context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» has been selected.',
                1
            ).format(
                count=1, model='Test Contact',
            ),
            context.get('help_message'),
        )

        with self.assertNoException():
            choices = context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(value=url,                     label=_('First name'), choices=choices)
        self.assertInChoices(value=build_url(field='user'), label=_('Owner user'), choices=choices)

        # ---
        first_name = 'Marioooo'
        response = self.client.post(
            url,
            data={
                'field_value': first_name,
                'entities': [mario.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(first_name, self.refresh(mario).first_name)

        self.assertTemplateUsed(response, 'creme_core/frags/bulk_process_report.html')

        context = response.context
        self.assertEqual(_('Multiple update'), context.get('title'))
        self.assertEqual(
            ngettext(
                '{success} «{model}» has been successfully modified.',
                '{success} «{model}» have been successfully modified.',
                1,
            ).format(success=1, model='Test Contact'),
            context.get('summary'),
        )

    def test_regular_field_not_super_user01(self):
        user = self.login(is_superuser=False)
        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertTrue(user.has_perm_to_change(mario))

        url = self._build_update_url(field='first_name')
        self.assertGET200(url)

        first_name = 'Marioooo'
        response = self.client.post(
            url,
            data={
                'field_value': first_name,
                'entities': [mario.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_not_super_user02(self):
        "No entity is allowed to be changed."
        user = self.login(is_superuser=False)

        old_first_name = 'Mario'
        mario = FakeContact.objects.create(
            user=self.other_user,
            first_name=old_first_name,
            last_name='Bros',
        )
        self.assertFalse(user.has_perm_to_change(mario))

        url = self._build_update_url(field='first_name')
        self.assertGET200(url)

        self.assertPOST403(
            url,
            data={
                'field_value': 'Marioooo',
                'entities': [mario.pk],
            },
        )
        self.assertEqual(old_first_name, self.refresh(mario).first_name)

    def test_regular_field_fk(self):
        self.login()

        create_pos = FakePosition.objects.create
        unemployed   = create_pos(title='unemployed')
        plumber      = create_pos(title='plumber')
        ghost_hunter = create_pos(title='ghost hunter')

        mario, luigi, url = self.create_2_contacts_n_url(
            mario_kwargs={'position': plumber},
            luigi_kwargs={'position': ghost_hunter},
            field='position',
        )
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            data={
                'field_value': unemployed.id,
                'entities': [mario.id, luigi.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(unemployed, self.refresh(mario).position)
        self.assertEqual(unemployed, self.refresh(luigi).position)

    def test_regular_field_ignore_missing(self):
        user = self.login()

        plumbing = FakeSector.objects.create(title='Plumbing')
        games    = FakeSector.objects.create(title='Games')

        create_contact = partial(FakeContact.objects.create, user=user, sector=games)
        mario = create_contact(first_name='Mario', last_name='Bros')
        luigi = create_contact(first_name='Luigi', last_name='Bros')

        nintendo = FakeOrganisation.objects.create(user=user, name='Nintendo', sector=games)

        url = self._build_update_url(field='sector')
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'field_value': plumbing.id,
                'entities': [mario.id, luigi.id, nintendo.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(plumbing, self.refresh(mario).sector)
        self.assertEqual(plumbing, self.refresh(luigi).sector)
        self.assertEqual(games,    self.refresh(nintendo).sector)  # missing id in contact table

    def test_regular_field_not_editable(self):
        self.login()

        fname = 'position'
        BulkUpdate.bulk_update_registry.register(FakeContact, exclude=[fname])
        self.assertFalse(BulkUpdate.bulk_update_registry.is_updatable(FakeContact, 'position'))

        unemployed = FakePosition.objects.create(title='unemployed')
        mario, luigi, url = self.create_2_contacts_n_url(field=fname)
        self.assertPOST(
            400, url,
            data={
                'field_value': unemployed.id,
                'entities': [mario.id, luigi.id],
            },
        )

    def test_regular_field_required_empty(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(field='last_name')
        response = self.assertPOST200(
            url,
            data={
                'field_value': '',
                'entities': [mario.id, luigi.id],
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('This field is required.'),
        )

    def test_regular_field_empty(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(
            mario_kwargs={'description': "Luigi's brother"},
            luigi_kwargs={'description': "Mario's brother"},
            field='description',
        )
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.id, luigi.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(mario).description)
        self.assertEqual('', self.refresh(luigi).description)

    def test_regular_field_ignore_forbidden_entity(self):
        user = self.login(is_superuser=False)

        mario_desc = "Luigi's brother"
        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=self.other_user, first_name='Mario', description=mario_desc)
        luigi = create_bros(user=user, first_name='Luigi', description="Mario's brother")

        response = self.client.post(
            self._build_update_url(field='description'),
            data={
                'field_value': '',
                'entities': [mario.id, luigi.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(mario_desc, self.refresh(mario).description)  # Not allowed
        self.assertEqual('',         self.refresh(luigi).description)

    def test_regular_field_datetime(self):
        self.login()

        mario, luigi, url = self.create_2_contacts_n_url(field='birthday')
        response = self.client.post(
            url,
            data={
                'field_value': 'bad date',
                'entities': [mario.id, luigi.id]
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('Enter a valid date.'),
        )

        # TODO: @override_settings...
        # This weird format have few chances to be present in settings
        settings.DATE_INPUT_FORMATS += ('-%dT%mU%Y-',)

        self.client.post(
            url,
            data={
                'field_value': '-31T01U2000-',
                'entities': [mario.id, luigi.id],
            },
        )
        birthday = date(2000, 1, 31)
        self.assertEqual(birthday, self.refresh(mario).birthday)
        self.assertEqual(birthday, self.refresh(luigi).birthday)

    def test_regular_field_ignore_forbidden_field(self):
        user = self.login(is_superuser=False)
        other_user = self.other_user

        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=other_user, first_name='Mario')
        luigi = create_bros(user=user,       first_name='Luigi')

        create_img = FakeImage.objects.create
        forbidden = create_img(user=other_user, name='forbidden')
        allowed   = create_img(user=user,       name='allowed')
        self.assertFalse(user.has_perm_to_view(forbidden))
        self.assertTrue(user.has_perm_to_view(allowed))

        url = self._build_update_url(field='image')
        response = self.assertPOST200(
            url,
            data={
                'field_value': forbidden.id,
                'entities': [mario.id, luigi.id]
            },
        )
        self.assertFormError(
            response, 'form', 'field_value',
            _('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=forbidden.id),
            ),
        )

        response = self.client.post(
            url,
            data={
                'field_value': allowed.id,
                'entities': [mario.id, luigi.id]
            },
        )
        self.assertNotEqual(allowed, self.refresh(mario).image)
        self.assertEqual(allowed,    self.refresh(luigi).image)

        self.assertEqual(
            '{} {}'.format(
                ngettext(
                    '{success} of {initial} «{model}» has been successfully modified.',
                    '{success} of {initial} «{model}» have been successfully modified.',
                    1,
                ).format(
                    success=1,
                    initial=2,
                    model='Test Contact',
                ),
                ngettext(
                    '{forbidden} was not editable.',
                    '{forbidden} were not editable.',
                    1,
                ).format(forbidden=1),
            ),
            response.context.get('summary'),
        )

    def test_regular_field_custom_edit_form(self):
        self.login()

        class _InnerEditBirthday(BulkDefaultEditForm):
            pass

        BulkUpdate.bulk_update_registry.register(
            FakeContact, innerforms={'birthday': _InnerEditBirthday},
        )

        mario, luigi, url = self.create_2_contacts_n_url(field='birthday')
        response = self.client.post(
            url,
            data={
                'field_value': '31-01-2000',
                'entities': [mario.id, luigi.id],
            },
        )
        self.assertNoFormError(response)

        birthday = date(2000, 1, 31)
        self.assertEqual(birthday, self.refresh(mario).birthday)
        self.assertEqual(birthday, self.refresh(luigi).birthday)

    def test_regular_field_user(self):
        """Fix a bug with the field list when bulk editing user
        (ie: a field of the parent class CremeEntity).
        """
        self.login()

        build_url = self._build_update_url
        url = build_url(field='user')
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(
            value=url,                           label=_('Owner user'), choices=choices,
        )
        self.assertInChoices(
            value=build_url(field='first_name'), label=_('First name'), choices=choices,
        )

    def test_regular_field_file01(self):
        "FileFields are excluded."
        user = self.login()

        folder = FakeFolder.objects.create(user=user, title='Earth maps')
        doc = FakeDocument.objects.create(user=user, title='Japan map', linked_folder=folder)

        ctype = doc.entity_type
        response = self.assertGET200(self._build_update_url(field='filedata', ctype=ctype))

        with self.assertNoException():
            field_urls = {
                f_url
                for f_url, label in response.context['form'].fields['_bulk_fieldname'].choices
            }

        self.assertIn(
            reverse('creme_core__bulk_update', args=(ctype.id, 'title')),
            field_urls,
        )
        self.assertNotIn(
            reverse('creme_core__bulk_update', args=(ctype.id, 'filedata')),
            field_urls,
        )

    def test_regular_field_file02(self):
        "FileFields are excluded (sub-field case)."
        user = self.login()

        bag = FakeFileBag.objects.create(user=user, name='Stuffes')

        ctype = bag.entity_type
        response = self.assertGET200(self._build_update_url(field='name', ctype=ctype))

        with self.assertNoException():
            field_urls = {
                f_url
                for f_url, label in response.context['form'].fields['_bulk_fieldname'].choices
            }

        self.assertIn(reverse('creme_core__bulk_update', args=(ctype.id, 'name')), field_urls)
        self.assertNotIn('file1', field_urls)

    def test_regular_field_many2many(self):
        user = self.login()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

        response = self.client.post(
            reverse('creme_core__bulk_update', args=(image1.entity_type_id, 'categories')),
            data={
                'field_value': [categories[0].pk, categories[2].pk],
                'entities': [image1.id, image2.id],
            },
        )
        self.assertNoFormError(response)

        expected = [categories[0], categories[2]]
        self.assertListEqual([*image1.categories.all()], expected)
        self.assertListEqual([*image2.categories.all()], expected)

    def test_regular_field_many2many_invalid(self):
        user = self.login()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

        url = reverse('creme_core__bulk_update', args=(image1.entity_type_id, 'categories'))
        invalid_pk = (FakeImageCategory.objects.aggregate(Max('id'))['id__max'] or 0) + 1

        response = self.client.post(
            url,
            data={
                'field_value': [categories[0].pk, invalid_pk],
                'entities': [image1.id, image2.id],
            },
        )
        self.assertFormError(
            response, 'form', 'field_value',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': invalid_pk,
            }
        )

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

    def test_regular_field_subfield(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Bros')
        mario = create_contact(first_name='Mario')
        luigi = create_contact(first_name='Luigi')

        address1 = FakeAddress.objects.create(entity=mario, value='address 1')
        mario.address = address1
        mario.save()

        build_url = self._build_update_url

        # GET (no field given) ---
        response1 = self.assertGET200(f'{build_url()}?entities={mario.id}')

        with self.assertNoException():
            choices = response1.context['form'].fields['_bulk_fieldname'].choices
            baddr_choices = dict(choices)[_('Billing address')]

        self.assertInChoices(
            value=build_url(field='address__city'), label=_('City'), choices=baddr_choices,
        )

        # GET (field given) ---
        uri = f'{build_url(field="address__city")}?entities={mario.id}'
        response2 = self.assertGET200(uri)

        with self.assertNoException():
            city_f = response2.context['form'].fields['field_value']

        self.assertIsInstance(city_f, CharField)
        self.assertEqual(_('City'), city_f.label)

        # POST ---
        city = 'New Dong city'
        response3 = self.client.post(
            uri,
            data={
                'entities': [mario.id, luigi.id],
                'field_value': city,
            },
        )
        self.assertNoFormError(response3)

        self.assertEqual(city, self.refresh(mario).address.city)
        self.assertIsNone(self.refresh(luigi).address)

    def test_custom_field_integer(self):
        self.login()

        cf_int = CustomField.objects.create(
            name='int', content_type=self.contact_ct, field_type=CustomField.INT,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_int.id),
        )

        # Int
        response = self.client.post(
            url,
            data={
                'field_value': 10,
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(mario)).value)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(luigi)).value)

        # Int empty
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldInteger.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(luigi))

    def test_custom_field_float(self):
        self.login()

        cf_float = CustomField.objects.create(
            name='float', content_type=self.contact_ct,
            field_type=CustomField.FLOAT,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_float.id),
        )

        # Float
        response = self.client.post(
            url,
            data={
                'field_value': '10.2',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(Decimal('10.2'), self.get_cf_values(cf_float, self.refresh(mario)).value)
        self.assertEqual(Decimal('10.2'), self.get_cf_values(cf_float, self.refresh(luigi)).value)

        # Float empty
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldFloat.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_float, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_float, self.refresh(luigi))

    def test_custom_field_boolean(self):
        self.login()

        cf_bool = CustomField.objects.create(
            name='bool', content_type=self.contact_ct,
            field_type=CustomField.BOOL,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_bool.id),
        )

        # Bool
        response = self.client.post(
            url,
            data={
                'field_value': 'true',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool false
        response = self.client.post(
            url,
            data={
                'field_value': 'false',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool empty
        response = self.client.post(
            url,
            data={
                'field_value': 'unknown',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldBoolean.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(luigi))

    def test_custom_field_string(self):
        self.login()

        cf_str = CustomField.objects.create(
            name='str', content_type=self.contact_ct,
            field_type=CustomField.STR,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_str.id),
        )

        # Str
        response = self.client.post(
            url,
            data={
                'field_value': 'str',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(mario)).value)
        self.assertEqual('str', self.get_cf_values(cf_str, self.refresh(luigi)).value)

        # Str empty
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldString.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(luigi))

    def test_custom_field_date(self):
        self.login()

        get_cf_values = self.get_cf_values
        cf_date = CustomField.objects.create(
            name='date', content_type=self.contact_ct,
            field_type=CustomField.DATETIME,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_date.id),
        )

        # TODO: use @override_settings
        # This weird format have few chances to be present in settings
        settings.DATETIME_INPUT_FORMATS += ("-%dT%mU%Y-",)

        # Date
        response = self.client.post(
            url,
            data={
                'field_value': '-31T01U2000-',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        dt = self.create_datetime(2000, 1, 31)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(mario)).value)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(luigi)).value)

        # Date empty
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldDateTime.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(luigi))

    def test_custom_field_enum(self):
        user = self.login()
        get_cf_values = self.get_cf_values

        cf_enum = CustomField.objects.create(
            name='enum', content_type=self.contact_ct,
            field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        enum1 = create_evalue(value='Enum1')
        create_evalue(value='Enum2')

        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_enum.id),
        )

        response = self.assertGET200(url)

        with self.assertNoException():
            field = response.context['form'].fields['field_value']

        self.assertIsInstance(field, config_fields.CustomEnumChoiceField)
        self.assertEqual(user, field.user)

        # Enum
        response = self.client.post(
            url,
            data={
                'field_value': enum1.id,
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(mario)).value)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(luigi)).value)

        # Enum empty
        response = self.client.post(
            url,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response)

        DoesNotExist = CustomFieldEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(luigi))

    def test_custom_field_enum_multiple(self):
        self.login()
        get_cf_values = self.get_cf_values

        cf_multi_enum = CustomField.objects.create(
            name='multi_enum', content_type=self.contact_ct,
            field_type=CustomField.MULTI_ENUM,
        )

        create_cfvalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=cf_multi_enum,
        )
        m_enum1 = create_cfvalue(value='MEnum1')
        create_cfvalue(value='MEnum2')
        m_enum3 = create_cfvalue(value='MEnum3')

        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cf_multi_enum.id),
        )
        self.assertGET200(url)

        # Multi-Enum
        self.assertNoFormError(self.client.post(
            url,
            data={
                'field_value': [m_enum1.id, m_enum3.id],
                'entities': [mario.pk, luigi.pk],
            },
        ))

        mario = self.refresh(mario)
        luigi = self.refresh(luigi)

        values_set = {
            *get_cf_values(cf_multi_enum, mario).value.values_list('pk', flat=True),
        }
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        values_set = {
            *get_cf_values(cf_multi_enum, luigi).value.values_list('pk', flat=True),
        }
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        # Multi-Enum empty
        self.assertNoFormError(self.client.post(
            url,
            data={
                'field_value': [],
                'entities': [mario.pk, luigi.pk],
            },
        ))

        DoesNotExist = CustomFieldMultiEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(luigi))

    def test_custom_field_deleted(self):
        self.login()

        cfield = CustomField.objects.create(
            name='int', content_type=self.contact_ct, field_type=CustomField.INT,
            is_deleted=True,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            field=_CUSTOMFIELD_FORMAT.format(cfield.id),
        )
        self.assertGET(400, url)

    def test_other_field_validation_error(self):
        user = self.login()
        create_empty_user = partial(
            get_user_model().objects.create_user,
            first_name='', last_name='', email='',
        )
        empty_user1 = create_empty_user(username='empty1')
        empty_user2 = create_empty_user(username='empty2')

        create_contact = partial(
            FakeContact.objects.create, user=user, first_name='', last_name='',
        )
        empty_contact1 = create_contact(is_user=empty_user1)
        empty_contact2 = create_contact(is_user=empty_user2)
        mario          = create_contact(first_name='Mario', last_name='Bros')

        url = self._build_update_url(field='last_name')
        self.assertGET200(
            f'{url}?entities={empty_contact1.id}.{empty_contact2.id}.{mario.id}'
        )

        response = self.client.post(
            url,
            data={
                'field_value': 'Bros',
                'entities': [empty_contact1.id, empty_contact2.id, mario.id],
            },
        )
        self.assertNoFormError(response)
        self.assertContains(
            response,
            _('This Contact is related to a user and must have a first name.'),
            count=2,
        )


class InnerEditTestCase(_BulkEditTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        InnerEdition.bulk_update_registry = bulk_update._BulkUpdateRegistry()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        InnerEdition.bulk_update_registry = cls._original_bulk_update_registry

    def create_contact(self):
        return FakeContact.objects.create(user=self.user, first_name='Mario', last_name='Bros')

    def create_orga(self):
        return FakeOrganisation.objects.create(user=self.user, name='Mushroom kingdom')

    def test_regular_field_01(self):
        self.login()

        mario = self.create_contact()
        self.assertGET(400, self.build_inneredit_url(mario, 'unknown'))

        url = self.build_inneredit_url(mario, 'first_name')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response.context.get
        self.assertEqual(_('Edit «{object}»').format(object=mario), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt('submit_label'))

        # ---
        first_name = 'Luigi'
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(mario)],
                'field_value': first_name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_02(self):
        self.login()

        mario = self.create_contact()
        response = self.client.post(
            self.build_inneredit_url(mario, 'birthday'),
            data={'field_value': 'whatever'},
        )
        self.assertFormError(response, 'form', 'field_value', _('Enter a valid date.'))

    def test_regular_field_03(self):
        "No permission."
        self.login(
            is_superuser=False, creatable_models=[FakeContact],
            allowed_apps=['documents'],
        )
        self._set_all_creds_except_one(EntityCredentials.CHANGE)

        mario = self.create_contact()
        self.assertFalse(self.user.has_perm_to_change(mario))
        self.assertGET403(self.build_inneredit_url(mario, 'first_name'))

    def test_regular_field_required(self):
        self.login()

        mario = self.create_contact()
        response = self.assertPOST200(
            self.build_inneredit_url(mario, 'last_name'),
            data={
                'entities_lbl': [str(mario)],
                'field_value': '',
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('This field is required.'),
        )

    def test_regular_field_not_editable(self):
        self.login()

        mario = self.create_contact()
        self.assertFalse(mario._meta.get_field('is_user').editable)

        build_url = self.build_inneredit_url
        url = build_url(mario, 'is_user')
        self.assertGET(400, url)
        self.assertPOST(400, url, data={'field_value': self.other_user.id})

        # Fields without form-field
        self.assertGET(400, build_url(mario, 'id'))
        self.assertGET(400, build_url(mario, 'cremeentity_ptr'))

    def test_regular_field_fields_config_hidden(self):
        self.login()

        hidden_fname = 'phone'
        hidden_fkname = 'image'
        hidden_subfname = 'zipcode'

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})],
        )

        mario = self.create_contact()

        build_url = partial(self.build_inneredit_url, mario)
        self.assertGET(400, build_url(hidden_fname))
        self.assertGET(400, build_url(hidden_fkname))
        self.assertGET(400, build_url('address__' + hidden_subfname))

    def test_regular_field_fields_config_required(self):
        self.login()

        fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(fname, {FieldsConfig.REQUIRED: True})],
        )

        mario = self.create_contact()
        response = self.assertPOST200(
            self.build_inneredit_url(mario, fname),
            data={
                'entities_lbl': [str(mario)],
                'field_value': '',
            },
        )
        self.assertFormError(
            response, 'form', 'field_value', _('This field is required.'),
        )

    def test_regular_field_many2many(self):
        user = self.login()

        create_cat = FakeImageCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        self.assertListEqual([*image.categories.all()], categories)

        url = self.build_inneredit_url(image, 'categories')
        response = self.client.post(
            url, data={'field_value': [categories[0].pk, categories[2].pk]},
        )
        self.assertNoFormError(response)

        image = self.refresh(image)
        self.assertListEqual([*image.categories.all()], [categories[0], categories[2]])

    def test_regular_field_many2many_invalid(self):
        user = self.login()

        create_cat = FakeImageCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        self.assertSetEqual({*image.categories.all()}, {*categories})

        invalid_pk = self.UNUSED_PK
        self.assertFalse(FakeImageCategory.objects.filter(id=invalid_pk))

        url = self.build_inneredit_url(image, 'categories')
        response = self.client.post(url, data={'field_value': [categories[0].pk, invalid_pk]})
        self.assertFormError(
            response, 'form', 'field_value',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': invalid_pk,
            },
        )

        image = self.refresh(image)
        self.assertSetEqual({*image.categories.all()}, {*categories})

    def test_regular_field_invalid_model(self):
        "Neither an entity & neither related to an entity."
        self.login()

        sector = FakeSector.objects.all()[0]
        # TODO: a 404/409 would be better ?
        self.assertGET403(self.build_inneredit_url(sector, 'title'))

    def test_regular_field_innerform(self):
        self.login()

        class _InnerEditName(BulkDefaultEditForm):
            def clean(self):
                raise ValidationError('invalid name')

        InnerEdition.bulk_update_registry.register(
            FakeContact, innerforms={'last_name': _InnerEditName},
        )

        mario = self.create_contact()
        url = self.build_inneredit_url(mario, 'last_name')
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'field_value': 'luigi'})
        self.assertFormError(response, 'form', '', 'invalid name')

    def test_regular_field_innerform_fielderror(self):
        self.login()

        class _InnerEditName(BulkDefaultEditForm):
            def _bulk_clean_entity(self, entity, values):
                BulkDefaultEditForm._bulk_clean_entity(self, entity, values)
                raise ValidationError('invalid name')

        InnerEdition.bulk_update_registry.register(
            FakeContact, innerforms={'last_name': _InnerEditName},
        )

        mario = self.create_contact()
        url = self.build_inneredit_url(mario, 'last_name')
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'field_value': 'luigi'})
        self.assertFormError(response, 'form', None, 'invalid name')

    def test_regular_field_file01(self):
        user = self.login()

        folder = FakeFolder.objects.create(user=user, title='Earth maps')
        doc = FakeDocument.objects.create(
            user=user, title='Japan map', linked_folder=folder,
        )

        url = self.build_inneredit_url(doc, 'filedata')
        self.assertGET200(url)

        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj = self.build_filedata(content, suffix=f'.{settings.ALLOWED_EXTENSIONS[0]}')
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(doc)],
                'field_value': file_obj,
            },
        )
        self.assertNoFormError(response)

        filedata = self.refresh(doc).filedata
        # self.assertEqual(f'upload/creme_core-tests/{file_obj.base_name}', filedata.name)
        self.assertEqual(f'creme_core-tests/{file_obj.base_name}', filedata.name)

        with filedata.open('r') as f:
            self.assertEqual([content], f.readlines())

    def test_regular_field_file02(self):
        "Empty data."
        user = self.login()

        file_path = self.create_uploaded_file(
            file_name='InnerEditTestCase_test_regular_field_file02.txt',
            dir_name='views',
        )

        comp = FakeFileComponent.objects.create(filedata=file_path)
        bag = FakeFileBag.objects.create(user=user, name='Stuffes', file1=comp)

        url = self.build_inneredit_url(bag, 'file1__filedata')
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(bag)],
                'field_value-clear': 'on',
                'field_value': b'',
            },
        )
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(comp).filedata.name)

    def test_custom_field01(self):
        self.login()
        mario = self.create_contact()
        old_created = mario.created - timedelta(days=1)
        type(mario).objects.filter(id=mario.id).update(
            created=old_created,
            modified=mario.modified - timedelta(days=1),
        )

        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.STR,
        )
        url = self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id))
        response = self.assertGET200(url)

        with self.assertNoException():
            field = response.context['form'].fields['field_value']

        self.assertIsInstance(field, CharField)

        value = 'hihi'
        response = self.client.post(url, data={'field_value': value})
        self.assertNoFormError(response)

        mario = self.refresh(mario)
        self.assertEqual(value, self.get_cf_values(cfield, mario).value)
        self.assertEqual(old_created, mario.created)
        self.assertDatetimesAlmostEqual(now(), mario.modified)

    def test_custom_field02(self):
        user = self.login()
        mario = self.create_contact()
        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.ENUM,
        )
        url = self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id))
        response = self.assertGET200(url)

        with self.assertNoException():
            field = response.context['form'].fields['field_value']

        self.assertIsInstance(field, config_fields.CustomEnumChoiceField)
        self.assertEqual(user, field.user)

    def test_custom_field03(self):
        "Deleted CustomField => error."
        self.login()
        mario = self.create_contact()
        cfield = CustomField.objects.create(
            name='custom 1', content_type=mario.entity_type,
            field_type=CustomField.INT,
            is_deleted=True,
        )
        self.assertGET(
            400,
            self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id)),
        )

    def test_related_subfield_missing(self):
        self.login()
        orga = self.create_orga()

        url = self.build_inneredit_url(orga, 'address__city')
        self.assertGET200(url)

        city = 'Marseille'
        response = self.client.post(url, data={'field_value': city})
        self.assertFormError(
            response, 'form', None,
            _('The field «{}» is empty').format(_('Billing address'))
        )

    def test_related_subfield(self):
        self.login()
        orga = self.create_orga()
        orga.address = FakeAddress.objects.create(entity=orga, value='address 1')
        orga.save()

        url = self.build_inneredit_url(orga, 'address__city')
        self.assertGET200(url)

        city = 'Marseille'
        response = self.client.post(url, data={'field_value': city})
        self.assertNoFormError(response)
        self.assertEqual(city, self.refresh(orga).address.city)

    def test_related_field(self):
        self.login()
        orga = self.create_orga()
        orga.address = FakeAddress.objects.create(entity=orga, value='address 1')
        orga.save()

        url = self.build_inneredit_url(orga, 'address')
        self.assertGET(400, url)

    def test_manytomany_field(self):
        """Edition of a manytomany field
        (needs a special hack with initial values for this case).
        """
        user = self.login()
        image = FakeImage.objects.create(user=user, name='Konoha by night')

        url = self.build_inneredit_url(image, 'categories')
        self.assertGET(200, url)

    def test_other_field_validation_error(self):
        user = self.login()
        empty_user = get_user_model().objects.create_user(
            username='empty', first_name='', last_name='', email='',
        )
        empty_contact = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user,
        )

        url = self.build_inneredit_url(empty_contact, 'last_name')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': 'Bros'})
        self.assertFormError(
            response, 'form', None,
            _('This Contact is related to a user and must have a first name.'),
        )

    def test_both_edited_field_and_field_validation_error(self):
        user = self.login()
        empty_user = get_user_model().objects.create_user(
            username='empty', first_name='', last_name='', email='',
        )
        empty_contact = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user,
        )

        url = self.build_inneredit_url(empty_contact, 'last_name')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': ''})
        self.assertFormError(
            response, 'form', 'field_value', _('This field is required.'),
        )
