from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import CharField, DateField
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

import creme.creme_config.forms.fields as config_fields
from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import EntityJobErrorsBrick, TrashBrick
from creme.creme_core.creme_jobs import reminder_type, trash_cleaner_type
# from creme.creme_core.forms.bulk import (
#      BulkDefaultEditForm,
#     _CUSTOMFIELD_FORMAT,
# )
from creme.creme_core.gui import bulk_update
from creme.creme_core.models import (  # FakeFileComponent FakeFileBag
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
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
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
from creme.creme_core.utils.collections import LimitedList
from creme.creme_core.views.entity import BulkUpdate, InnerEdition

from .base import BrickTestCaseMixin, ViewsTestCase


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


class _BulkEditTestCase(ViewsTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #     cls._original_bulk_update_registry = bulk_update.bulk_update_registry

    @staticmethod
    def get_cf_values(cf, entity):
        return cf.value_class.objects.get(custom_field=cf, entity=entity)

    @staticmethod
    def create_image(name, user, categories=()):
        image = FakeImage.objects.create(user=user, name=name)
        image.categories.set(categories)

        return image


class BulkUpdateTestCase(_BulkEditTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #
    #     BulkUpdate.bulk_update_registry = bulk_update._BulkUpdateRegistry()
    #     # cls.contact_bulk_status = bulk_update.bulk_update_registry.status(FakeContact)
    #
    # @classmethod
    # def tearDownClass(cls):
    #     super().tearDownClass()
    #
    #     BulkUpdate.bulk_update_registry = cls._original_bulk_update_registry
    #
    # def setUp(self):
    #     super().setUp()
    #     contact_status = BulkUpdate.bulk_update_registry.status(FakeContact)
    #
    #     self._contact_innerforms = contact_status._innerforms
    #     BulkUpdate.bulk_update_registry.status(FakeContact)._innerforms = {}
    #
    #     self._contact_excludes = contact_status.excludes
    #     BulkUpdate.bulk_update_registry.status(FakeContact).excludes = set()
    #
    # def tearDown(self):
    #     super().tearDown()
    #     contact_status = BulkUpdate.bulk_update_registry.status(FakeContact)
    #     contact_status._innerforms = self._contact_innerforms
    #     contact_status.excludes = self._contact_excludes

    def setUp(self):
        super().setUp()
        self._original_bulk_update_registry = BulkUpdate.bulk_update_registry

    def tearDown(self):
        super().tearDown()
        BulkUpdate.bulk_update_registry = self._original_bulk_update_registry

    def create_2_contacts_n_url(self, mario_kwargs=None, luigi_kwargs=None, field='first_name'):
        create_contact = partial(
            FakeContact.objects.create, user=self.user, last_name='Bros',
        )
        mario = create_contact(first_name='Mario', **(mario_kwargs or {}))
        luigi = create_contact(first_name='Luigi', **(luigi_kwargs or {}))

        return (
            mario,
            luigi,
            self.build_bulkupdate_uri(
                model=FakeContact, field=field, entities=(mario, luigi),
            ),
        )

    def test_not_registered_model(self):
        user = self.login()
        BulkUpdate.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeOrganisation)  # Not FakeContact

        self.assertGET404(
            self.build_bulkupdate_uri(model=FakeImage, entities=[user.linked_contact])
        )

    def test_regular_field_invalid_field(self):
        self.login()

        # response = self.assertGET(400, self.build_bulkupdate_url(FakeContact, 'unknown'))
        # self.assertContains(
        #     response,
        #     "The field Test Contact.unknown doesn't exist",
        #     status_code=400,
        # )
        self.assertContains(
            self.client.get(self.build_bulkupdate_uri(model=FakeContact, field='unknown')),
            'The cell "regular_field-unknown" is invalid',
            status_code=404, html=True,
        )

    def test_no_field_given(self):
        user = self.login()

        uri = self.build_bulkupdate_uri(model=FakeContact, entities=[user.linked_contact])
        response1 = self.assertGET200(uri)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Multiple update'),        context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                1
            ).format(count=1, model='Test Contact'),
            context1.get('help_message'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            choices_f = fields['_bulk_fieldname']
            choices = choices_f.choices

        other_fields = [name for name in fields.keys() if name != '_bulk_fieldname']
        self.assertEqual(1, len(other_fields))

        with self.assertNoException():
            FakeContact._meta.get_field(other_fields[0])

        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        self.assertInChoices(
            value=build_url(field='first_name'), label=_('First name'), choices=choices,
        )
        self.assertInChoices(
            value=build_url(field='user'),       label=_('Owner user'), choices=choices,
        )
        self.assertEqual(build_url(field=other_fields[0]), choices_f.initial)

    def test_regular_field_not_entity_model(self):
        self.login()
        self.assertGET409(self.build_bulkupdate_uri(model=FakeSector))
        self.assertGET409(self.build_bulkupdate_uri(model=FakeSector, field='title'))

    def test_regular_field_1_entity(self):
        user = self.login()

        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        field_name = 'first_name'
        response1 = self.assertGET200(build_url(field=field_name, entities=[mario]))
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(_('Multiple update'),        context1.get('title'))
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                1
            ).format(
                count=1, model='Test Contact',
            ),
            context1.get('help_message'),
        )

        with self.assertNoException():
            form = context1['form']
            fields = form.fields
            choices_f = fields['_bulk_fieldname']
            choices = choices_f.choices
            edition_field = fields[field_name]

        self.assertIsInstance(edition_field, CharField)
        self.assertEqual(_('First name'), edition_field.label)
        self.assertFalse(edition_field.required)
        self.assertDictEqual({field_name: getattr(mario, field_name)}, form.initial)

        url = build_url(field=field_name)
        self.assertInChoices(value=url,                     label=_('First name'), choices=choices)
        self.assertInChoices(value=build_url(field='user'), label=_('Owner user'), choices=choices)
        self.assertEqual(url, choices_f.initial)

        # ---
        first_name = 'Marioooo'
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.pk],
                # 'field_value': first_name,
                field_name: first_name,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(first_name, self.refresh(mario).first_name)

        # self.assertTemplateUsed(response2, 'creme_core/frags/bulk_process_report.html')
        self.assertTemplateUsed(response2, 'creme_core/bulk-update-results.html')

        get_context2 = response2.context.get
        self.assertEqual(_('Multiple update'), get_context2('title'))
        # self.assertEqual(
        #     ngettext(
        #         '{success} «{model}» has been successfully modified.',
        #         '{success} «{model}» have been successfully modified.',
        #         1,
        #     ).format(success=1, model='Test Contact'),
        #     get_context2('summary'),
        # )
        self.assertEqual(1, get_context2('initial_count'))
        self.assertEqual(1, get_context2('success_count'))
        self.assertEqual(0, get_context2('forbidden_count'))

        errors = get_context2('errors')
        self.assertIsInstance(errors, LimitedList)
        self.assertEqual(0, len(errors))
        self.assertEqual(100, errors.max_size)

        self.assertContains(
            response2,
            ngettext(
                '%(counter)s entity has been successfully modified.',
                '%(counter)s entities have been successfully modified.',
                1,
            ) % {'counter': 1},
        )

    def test_regular_field_2_entities(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Bros')
        mario = create_contact(first_name='Mario')
        luigi = create_contact(first_name='Luigi')
        field_name = 'first_name'
        build_url = partial(self.build_bulkupdate_uri, model=FakeContact, field=field_name)
        entities = [mario, luigi]
        response1 = self.assertGET200(build_url(entities=entities))

        context1 = response1.context
        self.assertHTMLEqual(
            ngettext(
                '{count} «{model}» has been selected.',
                '{count} «{model}» have been selected.',
                2
            ).format(
                count=2, model='Test Contacts',
            ),
            context1.get('help_message'),
        )

        with self.assertNoException():
            form = context1['form']

        self.assertDictEqual({}, form.initial)

        # ---
        value = 'Peach'
        response2 = self.client.post(
            build_url(),
            data={
                'entities': [e.id for e in entities],
                field_name: value,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(value, self.refresh(mario).first_name)
        self.assertEqual(value, self.refresh(luigi).first_name)

        get_context2 = response2.context.get
        self.assertEqual(_('Multiple update'), get_context2('title'))
        self.assertEqual(2, get_context2('initial_count'))
        self.assertEqual(2, get_context2('success_count'))
        self.assertEqual(0, get_context2('forbidden_count'))

        self.assertContains(
            response2,
            ngettext(
                '%(counter)s entity has been successfully modified.',
                '%(counter)s entities have been successfully modified.',
                2,
            ) % {'counter': 2},
        )

    def test_regular_field_not_super_user01(self):
        user = self.login(is_superuser=False)
        mario = FakeContact.objects.create(user=user, first_name='Mario', last_name='Bros')
        self.assertTrue(user.has_perm_to_change(mario))

        field_name = 'first_name'
        url = self.build_bulkupdate_uri(model=FakeContact, field=field_name)
        self.assertGET200(url)

        field_value = 'Marioooo'
        response = self.client.post(
            url,
            data={
                'entities': [mario.pk],
                # 'field_value': field_value,
                field_name: field_value,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(field_value, getattr(self.refresh(mario), field_name))

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

        field_name = 'first_name'
        url = self.build_bulkupdate_uri(model=type(mario), field=field_name)
        self.assertGET200(url)

        self.assertPOST403(
            url,
            data={
                'entities': [mario.pk],
                # 'field_value': 'Marioooo',
                field_name: 'Marioooo',
            },
        )
        self.assertEqual(old_first_name, getattr(self.refresh(mario), field_name))

    def test_regular_field_fk(self):
        self.login()

        create_pos = FakePosition.objects.create
        unemployed   = create_pos(title='unemployed')
        plumber      = create_pos(title='plumber')
        ghost_hunter = create_pos(title='ghost hunter')

        field_name = 'position'
        mario, luigi, url = self.create_2_contacts_n_url(
            mario_kwargs={field_name: plumber},
            luigi_kwargs={field_name: ghost_hunter},
            field=field_name,
        )
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': unemployed.id,
                field_name: unemployed.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(unemployed, getattr(self.refresh(mario), field_name))
        self.assertEqual(unemployed, getattr(self.refresh(luigi), field_name))

    def test_regular_field_ignore_missing(self):
        user = self.login()

        create_sector = FakeSector.objects.create
        plumbing = create_sector(title='Plumbing')
        games    = create_sector(title='Games')

        field_name = 'sector'
        create_contact = partial(FakeContact.objects.create, user=user, **{field_name: games})
        mario = create_contact(first_name='Mario', last_name='Bros')
        luigi = create_contact(first_name='Luigi', last_name='Bros')

        nintendo = FakeOrganisation.objects.create(
            user=user, name='Nintendo', **{field_name: games},
        )

        url = self.build_bulkupdate_uri(model=FakeContact, field=field_name)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id, nintendo.id],
                # 'field_value': plumbing.id,
                field_name: plumbing.id,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(plumbing, getattr(self.refresh(mario), field_name))
        self.assertEqual(plumbing, getattr(self.refresh(luigi), field_name))
        # Missing id in Contact's table
        self.assertEqual(games, getattr(self.refresh(nintendo), field_name))

    def test_regular_field_not_editable(self):
        self.login()

        field_name = 'position'
        # BulkUpdate.bulk_update_registry.register(FakeContact, exclude=[field_name])
        # self.assertFalse(BulkUpdate.bulk_update_registry.is_updatable(FakeContact, field_name))
        BulkUpdate.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeContact).exclude(field_name)

        unemployed = FakePosition.objects.create(title='unemployed')
        mario, luigi, url = self.create_2_contacts_n_url(field=field_name)
        # self.assertPOST(
        #     400, url,
        #     data={
        #         'field_value': unemployed.id,
        #         'entities': [mario.id, luigi.id],
        #     },
        # )
        self.assertPOST404(
            url,
            data={
                'entities': [mario.id, luigi.id],
                field_name: unemployed.id,
            },
        )

    def test_regular_field_required_empty(self):
        self.login()

        field_name = 'last_name'
        mario, luigi, url = self.create_2_contacts_n_url(field=field_name)
        response = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': '',
                field_name: '',
            },
        )
        self.assertFormError(
            # response, 'form', 'field_value', _('This field is required.'),
            response, 'form', field_name, _('This field is required.'),
        )

    def test_regular_field_empty(self):
        self.login()

        field_name = 'description'
        mario, luigi, url = self.create_2_contacts_n_url(
            mario_kwargs={field_name: "Luigi's brother"},
            luigi_kwargs={field_name: "Mario's brother"},
            field=field_name,
        )
        response = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': '',
                field_name: '',
            },
        )
        self.assertNoFormError(response)
        self.assertEqual('', getattr(self.refresh(mario), field_name))
        self.assertEqual('', getattr(self.refresh(luigi), field_name))

    def test_regular_field_unique(self):
        user = self.login()

        BulkUpdate.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeActivity)

        atype = FakeActivityType.objects.first()
        activity = FakeActivity.objects.create(user=user, title='Comiket', type=atype)

        build_url = partial(self.build_bulkupdate_uri, model=FakeActivity)
        response1 = self.assertGET200(build_url(entities=[activity]))

        with self.assertNoException():
            choices = response1.context['form'].fields['_bulk_fieldname'].choices

        field_name = 'title'
        self.assertInChoices(value=build_url(field='user'), label=_('Owner user'), choices=choices)
        url = build_url(field=field_name)
        self.assertNotInChoices(value=url, choices=choices)

        self.assertGET404(url)

    def test_regular_field_ignore_forbidden_entity(self):
        user = self.login(is_superuser=False)

        field_name = 'description'
        mario_desc = "Luigi's brother"
        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=self.other_user, first_name='Mario', **{field_name: mario_desc})
        luigi = create_bros(user=user, first_name='Luigi', **{field_name: "Mario's brother"})
        toad  = create_bros(user=user, first_name='Toad', **{field_name: "Mario's friend"})

        response = self.client.post(
            self.build_bulkupdate_uri(model=FakeContact, field=field_name),
            data={
                'entities': [mario.id, luigi.id, toad.id],
                # 'field_value': '',
                field_name: '',
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(mario_desc, getattr(self.refresh(mario), field_name))  # Not allowed
        self.assertEqual('',         getattr(self.refresh(luigi), field_name))
        self.assertEqual('',         getattr(self.refresh(toad),  field_name))

        get_context = response.context.get
        self.assertEqual(3, get_context('initial_count'))
        self.assertEqual(2, get_context('success_count'))
        self.assertEqual(1, get_context('forbidden_count'))
        self.assertFalse(get_context('errors'))

        self.assertContains(
            response,
            ngettext(
                '%(counter)s entity on %(initial_count)s has been successfully modified.',
                '%(counter)s entities on %(initial_count)s have been successfully modified.',
                2,
            ) % {'counter': 2, 'initial_count': 3},
        )
        self.assertContains(
            response,
            ngettext(
                '%(counter)s entity was not editable.',
                '%(counter)s entities were not editable.',
                1,
            ) % {'counter': 1},
        )

    @override_settings(USE_L10N=False, DATE_INPUT_FORMATS=['%d/%m/%Y'])
    def test_regular_field_date(self):
        self.login()

        field_name = 'birthday'
        mario, luigi, url = self.create_2_contacts_n_url(field=field_name)

        birthday = date(2000, 1, 31)
        response1 = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': 'bad date',
                # 'field_value': birthday.strftime('%d-%m-%y'),
                field_name: birthday.strftime('%d-%m-%y'),
            },
        )
        self.assertFormError(
            # response1, 'form', 'field_value', _('Enter a valid date.'),
            response1, 'form', field_name, _('Enter a valid date.'),
        )

        # settings.DATE_INPUT_FORMATS += ('-%dT%mU%Y-',)

        response2 = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': '-31T01U2000-',
                # 'field_value': self.formfield_value_date(birthday),
                field_name: self.formfield_value_date(birthday),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(birthday, getattr(self.refresh(mario), field_name))
        self.assertEqual(birthday, getattr(self.refresh(luigi), field_name))

    def test_regular_field_ignore_forbidden_field(self):
        user = self.login(is_superuser=False)
        other_user = self.other_user

        create_bros = partial(FakeContact.objects.create, last_name='Bros')
        mario = create_bros(user=other_user, first_name='Mario')
        luigi = create_bros(user=user,       first_name='Luigi')

        create_img = FakeImage.objects.create
        forbidden = create_img(user=other_user, name='forbidden')
        # allowed   = create_img(user=user,       name='allowed')
        self.assertFalse(user.has_perm_to_view(forbidden))
        # self.assertTrue(user.has_perm_to_view(allowed))

        field_name = 'image'
        url = self.build_bulkupdate_uri(model=FakeContact, field=field_name)
        response = self.assertPOST200(
            url,
            data={
                'entities': [mario.id, luigi.id],
                # 'field_value': forbidden.id,
                field_name: forbidden.id,
            },
        )
        self.assertFormError(
            # response, 'form', 'field_value',
            response, 'form', field_name,
            _('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=forbidden.id),
            ),
        )

        # # ---
        # response2 = self.client.post(
        #     url,
        #     data={
        #         'entities': [mario.id, luigi.id],
        #         # 'field_value': allowed.id,
        #         field_name: allowed.id,
        #     },
        # )
        # self.assertNotEqual(allowed, getattr(self.refresh(mario), field_name))
        # self.assertEqual(allowed,    getattr(self.refresh(luigi), field_name))
        #
        # self.assertEqual(
        #     '{} {}'.format(
        #         ngettext(
        #             '{success} of {initial} «{model}» has been successfully modified.',
        #             '{success} of {initial} «{model}» have been successfully modified.',
        #             1,
        #         ).format(
        #             success=1,
        #             initial=2,
        #             model='Test Contact',
        #         ),
        #         ngettext(
        #             '{forbidden} was not editable.',
        #             '{forbidden} were not editable.',
        #             1,
        #         ).format(forbidden=1),
        #     ),
        #     response2.context.get('summary'),
        # )

    # def test_regular_field_custom_edit_form(self):
    #     self.login()
    #
    #     class _InnerEditBirthday(BulkDefaultEditForm):
    #         pass
    #
    #     BulkUpdate.bulk_update_registry.register(
    #         FakeContact, innerforms={'birthday': _InnerEditBirthday},
    #     )
    #
    #     mario, luigi, url = self.create_2_contacts_n_url(field='birthday')
    #     birthday = date(2000, 1, 31)
    #     response = self.client.post(
    #         url,
    #         data={
    #             # 'field_value': '31-01-2000',
    #             'field_value': self.formfield_value_date(birthday),
    #             'entities': [mario.id, luigi.id],
    #         },
    #     )
    #     self.assertNoFormError(response)
    #
    #     self.assertEqual(birthday, self.refresh(mario).birthday)
    #     self.assertEqual(birthday, self.refresh(luigi).birthday)
    def test_regular_field_overrider(self):
        self.login()

        field_name = 'birthday'
        called_instances = []

        class DateDelayOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                called_instances.append(instances)
                return DateField()

            def post_clean_instance(this, *, instance, value, form):
                setattr(instance, field_name, value + timedelta(days=1))

        BulkUpdate.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(DateDelayOverrider)

        mario, luigi, url = self.create_2_contacts_n_url(field=field_name)
        response1 = self.assertGET200(url)
        formfield_name = f'override-{field_name}'

        with self.assertNoException():
            overridden_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(overridden_f, DateField)

        self.assertEqual(1, len(called_instances))
        self.assertCountEqual([mario, luigi], called_instances[0])

        # ---
        called_instances.clear()
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.id, luigi.id],
                formfield_name: self.formfield_value_date(date(2000, 1, 31)),
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(3, len(called_instances))
        self.assertCountEqual([mario, luigi], called_instances[0])
        self.assertCountEqual([mario, luigi], called_instances[1])

        field_value = date(2000, 2, 1)
        self.assertEqual(field_value, getattr(self.refresh(mario), field_name))
        self.assertEqual(field_value, getattr(self.refresh(luigi), field_name))

    def test_regular_field_user(self):
        """Fix a bug with the field list when bulk editing user
        (i.e. a field of the parent class CremeEntity).
        """
        self.login()

        build_url = partial(self.build_bulkupdate_uri, model=FakeContact)
        url = build_url(field='user')
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(
            value=url, label=_('Owner user'), choices=choices,
        )
        self.assertInChoices(
            value=build_url(field='first_name'), label=_('First name'), choices=choices,
        )

    def test_regular_field_file01(self):
        "FileFields are excluded."
        user = self.login()

        BulkUpdate.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeDocument)

        doc = FakeDocument.objects.create(
            user=user, title='Japan map',
            linked_folder=FakeFolder.objects.create(user=user, title='Earth maps'),
        )
        build_uri = partial(self.build_bulkupdate_uri, model=type(doc))
        response = self.assertGET200(build_uri())

        with self.assertNoException():
            choices = response.context['form'].fields['_bulk_fieldname'].choices

        self.assertInChoices(value=build_uri(field='title'), label=_('Title'), choices=choices)

        uri = build_uri(field='filedata')
        self.assertNotInChoices(value=uri, choices=choices)
        self.assertGET404(uri)

    # TODO: if subfield are unleashed
    # def test_regular_field_file02(self):
    #     "FileFields are excluded (sub-field case)."
    #     user = self.login()
    #     bag = FakeFileBag.objects.create(user=user, name='Stuffes')
    #     response = self.assertGET200(self.build_bulkupdate_uri(model=type(bag), field='name'))
    #
    #     with self.assertNoException():
    #         field_urls = {
    #             f_url
    #             for f_url, label in response.context['form'].fields['_bulk_fieldname'].choices
    #         }
    #
    #     self.assertIn(
    #         reverse('creme_core__bulk_update', args=(bag.entity_type_id, 'name')),
    #         field_urls,
    #     )
    #     self.assertNotIn('file1', field_urls)

    def test_regular_field_many2many(self):
        user = self.login()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*image1.categories.all()], categories)
        self.assertListEqual([*image2.categories.all()], categories[:1])

        m2m_name = 'categories'
        response = self.client.post(
            self.build_bulkupdate_uri(model=FakeImage, field=m2m_name),
            data={
                'entities': [image1.id, image2.id],
                # 'field_value': [categories[0].pk, categories[2].pk],
                m2m_name: [categories[0].pk, categories[2].pk],
            },
        )
        self.assertNoFormError(response)

        expected = [categories[0], categories[2]]
        self.assertListEqual([*getattr(image1, m2m_name).all()], expected)
        self.assertListEqual([*getattr(image2, m2m_name).all()], expected)

    def test_regular_field_many2many_invalid(self):
        user = self.login()

        categories = [FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')]

        m2m_name = 'categories'
        image1 = self.create_image('image1', user, categories)
        image2 = self.create_image('image2', user, categories[:1])

        self.assertListEqual([*getattr(image1, m2m_name).all()], categories)
        self.assertListEqual([*getattr(image2, m2m_name).all()], categories[:1])

        url = self.build_bulkupdate_uri(model=type(image1), field=m2m_name)
        invalid_pk = (FakeImageCategory.objects.aggregate(Max('id'))['id__max'] or 0) + 1

        response = self.client.post(
            url,
            data={
                'entities': [image1.id, image2.id],
                # 'field_value': [categories[0].pk, invalid_pk],
                m2m_name: [categories[0].pk, invalid_pk],
            },
        )
        self.assertFormError(
            # response, 'form', 'field_value',
            response, 'form', m2m_name,
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': invalid_pk,
            },
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

        # build_url = self._build_update_url
        #
        # GET (no field given) ---
        # response1 = self.assertGET200(f'{build_url()}?entities={mario.id}')
        # response1 = self.assertGET200(build_url())
        #
        # with self.assertNoException():
        #     choices = response1.context['form'].fields['_bulk_fieldname'].choices
        #     baddr_choices = dict(choices)[_('Billing address')]
        #
        # self.assertInChoices(
        #     value=build_url(field='address__city'), label=_('City'), choices=baddr_choices,
        # )

        # GET (field given) ---
        # uri = f'{build_url(field="address__city")}?entities={mario.id}'
        # response2 = self.assertGET200(uri)
        self.assertGET404(self.build_bulkupdate_uri(
            field='address__city', model=FakeContact, entities=[mario, luigi],
        ))

        # with self.assertNoException():
        #     city_f = response2.context['form'].fields['field_value']
        #
        # self.assertIsInstance(city_f, CharField)
        # self.assertEqual(_('City'), city_f.label)
        #
        # # POST ---
        # city = 'New Dong city'
        # response3 = self.client.post(
        #     uri,
        #     data={
        #         'entities': [mario.id, luigi.id],
        #         'field_value': city,
        #     },
        # )
        # self.assertNoFormError(response3)
        #
        # self.assertEqual(city, self.refresh(mario).address.city)
        # self.assertIsNone(self.refresh(luigi).address)

    def test_regular_field_fields_config_hidden(self):
        self.login()

        hidden_fname = 'phone'
        hidden_fkname = 'image'
        # hidden_subfname = 'zipcode'  TODO

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
            ],
        )
        # create_fconf(
        #     content_type=FakeAddress,
        #     descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})],
        # )

        build_uri = partial(self.build_bulkupdate_uri, model=FakeContact)
        self.assertGET404(build_uri(field=hidden_fname))
        self.assertGET404(build_uri(field=hidden_fkname))
        # self.assertGET(404, build_uri(field='address__' + hidden_subfname))

    def test_regular_field_fields_config_required(self):
        self.login()

        model = FakeContact
        field_name1 = 'phone'
        url = self.build_bulkupdate_uri(model=model, field=field_name1)

        # ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            edition_field1 = response1.context['form'].fields[field_name1]

        self.assertFalse(edition_field1.required)

        # ---
        field_name2 = 'mobile'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (field_name1, {FieldsConfig.REQUIRED: True}),
                (field_name2, {FieldsConfig.REQUIRED: True}),
            ],
        )
        response2 = self.assertGET200(url)

        with self.assertNoException():
            fields2 = response2.context['form'].fields
            edition_field2 = fields2[field_name1]

        self.assertTrue(edition_field2.required)
        self.assertNotIn(field_name2, fields2)

    def test_custom_field_error01(self):
        self.login()

        cell_key = 'custom_field-44500124'
        response = self.client.get(
            reverse(
                'creme_core__bulk_update',
                args=(
                    ContentType.objects.get_for_model(FakeContact).id,
                    cell_key,
                ),
            )
        )
        self.assertContains(
            response,
            f'The cell "{cell_key}" is invalid',
            status_code=404, html=True,
        )

    def test_custom_field_integer(self):
        self.login()

        cf_int = CustomField.objects.create(
            name='int', content_type=FakeContact, field_type=CustomField.INT,
        )
        # mario, luigi, url = self.create_2_contacts_n_url(
        #     field=_CUSTOMFIELD_FORMAT.format(cf_int.id),
        # )
        mario, luigi, uri = self.create_2_contacts_n_url(field=cf_int)

        # GET ---
        # response1 = self.assertGET200(url)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            choices = response1.context['form'].fields['_bulk_fieldname'].choices

        # TODO: improve assertInChoices for opt-groups
        cf_gname = _('Custom fields')
        url = self.build_bulkupdate_uri(model=FakeContact, field=cf_int)
        for group_label, group_choices in choices:
            if group_label == cf_gname:
                self.assertInChoices(value=url, label=cf_int.name, choices=group_choices)
                break
        else:
            self.fail(f'Group "{cf_gname}" not found')

        # POST ---
        response2 = self.client.post(
            # url,
            uri,
            data={
                'entities': [mario.pk, luigi.pk],
                # 'field_value': 10,
                f'custom_field-{cf_int.id}': 10,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(mario)).value)
        self.assertEqual(10, self.get_cf_values(cf_int, self.refresh(luigi)).value)

        # POST (empty) ---
        response3 = self.client.post(
            uri,
            data={
                'field_value': '',
                'entities': [mario.pk, luigi.pk],
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldInteger.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_int, self.refresh(luigi))

    def test_custom_field_decimal(self):
        self.login()

        cf_decimal = CustomField.objects.create(
            name='float', content_type=FakeContact,
            field_type=CustomField.FLOAT,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_decimal.id),
            field=cf_decimal,
        )

        formfield_name = f'custom_field-{cf_decimal.id}'
        response1 = self.client.post(
            url,
            data={
                'entities': [mario.pk, luigi.pk],
                # 'field_value': '10.2',
                formfield_name: '10.2',
            },
        )
        self.assertNoFormError(response1)
        expected = Decimal('10.2')
        self.assertEqual(expected, self.get_cf_values(cf_decimal, self.refresh(mario)).value)
        self.assertEqual(expected, self.get_cf_values(cf_decimal, self.refresh(luigi)).value)

        # Empty ---
        response2 = self.client.post(
            url,
            data={
                'entities': [mario.pk, luigi.pk],
                # 'field_value': '',
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldFloat.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_decimal, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_decimal, self.refresh(luigi))

    def test_custom_field_boolean(self):
        self.login()

        cf_bool = CustomField.objects.create(
            name='bool', content_type=FakeContact,
            field_type=CustomField.BOOL,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_bool.id),
            field=cf_bool,
        )

        # Bool
        formfield_name = f'custom_field-{cf_bool.id}'
        e_ids = [mario.pk, luigi.pk]
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': 'true',
                formfield_name: 'true',
            },
        )
        self.assertNoFormError(response1)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(True, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool false
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': 'false',
                formfield_name: 'false',
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(mario)).value)
        self.assertEqual(False, self.get_cf_values(cf_bool, self.refresh(luigi)).value)

        # Bool empty
        response3 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': 'unknown',
                formfield_name: 'unknown',
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldBoolean.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_bool, self.refresh(luigi))

    def test_custom_field_string(self):
        self.login()

        cf_str = CustomField.objects.create(
            name='str', content_type=FakeContact, field_type=CustomField.STR,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_str.id),
            field=cf_str,
        )

        # Str
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_str.id}'
        field_value = 'my value'
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': field_value,
                formfield_name: field_value,
            },
        )
        self.assertNoFormError(response1)
        self.assertEqual(field_value, self.get_cf_values(cf_str, self.refresh(mario)).value)
        self.assertEqual(field_value, self.get_cf_values(cf_str, self.refresh(luigi)).value)

        # Str empty
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': '',
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldString.DoesNotExist
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(mario))
        self.assertRaises(DoesNotExist, self.get_cf_values, cf_str, self.refresh(luigi))

    @override_settings(USE_L10N=False, DATE_INPUT_FORMATS=['%d/%m/%Y %H:%M:%S'])
    def test_custom_field_datetime(self):
        self.login()

        get_cf_values = self.get_cf_values
        cf_date = CustomField.objects.create(
            name='date', content_type=FakeContact, field_type=CustomField.DATETIME,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_date.id),
            field=cf_date,
        )

        # settings.DATETIME_INPUT_FORMATS += ("-%dT%mU%Y-",)

        # Date
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_date.id}'
        dt = self.create_datetime(2000, 1, 31)
        response1 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': '-31T01U2000-',
                # 'field_value': self.formfield_value_datetime(dt),
                formfield_name: self.formfield_value_datetime(dt),
            },
        )
        self.assertNoFormError(response1)

        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(mario)).value)
        self.assertEqual(dt, get_cf_values(cf_date, self.refresh(luigi)).value)

        # Date empty
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': '',
                formfield_name: '',
            },
        )
        self.assertNoFormError(response2)

        DoesNotExist = CustomFieldDateTime.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_date, self.refresh(luigi))

    def test_custom_field_enum(self):
        user = self.login()
        get_cf_values = self.get_cf_values

        cf_enum = CustomField.objects.create(
            name='enum', content_type=FakeContact, field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        enum1 = create_evalue(value='Enum1')
        create_evalue(value='Enum2')

        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_enum.id),
            field=cf_enum,
        )

        response1 = self.assertGET200(url)
        formfield_name = f'custom_field-{cf_enum.id}'

        with self.assertNoException():
            # field = response1.context['form'].fields['field_value']
            field = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(field, config_fields.CustomEnumChoiceField)
        self.assertEqual(user, field.user)

        # Enum
        e_ids = [mario.pk, luigi.pk]
        response2 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': enum1.id,
                formfield_name: enum1.id,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(mario)).value)
        self.assertEqual(enum1, get_cf_values(cf_enum, self.refresh(luigi)).value)

        # Enum empty
        response3 = self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': '',
                formfield_name: '',
            },
        )
        self.assertNoFormError(response3)

        DoesNotExist = CustomFieldEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_enum, self.refresh(luigi))

    def test_custom_field_enum_multiple(self):
        self.login()
        get_cf_values = self.get_cf_values

        cf_multi_enum = CustomField.objects.create(
            name='multi_enum', content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )

        create_cfvalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=cf_multi_enum,
        )
        m_enum1 = create_cfvalue(value='MEnum1')
        create_cfvalue(value='MEnum2')
        m_enum3 = create_cfvalue(value='MEnum3')

        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cf_multi_enum.id),
            field=cf_multi_enum,
        )
        self.assertGET200(url)

        # Multi-Enum
        e_ids = [mario.pk, luigi.pk]
        formfield_name = f'custom_field-{cf_multi_enum.id}'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': [m_enum1.id, m_enum3.id],
                formfield_name: [m_enum1.id, m_enum3.id],
            },
        ))

        mario = self.refresh(mario)
        luigi = self.refresh(luigi)

        values_set = {
            *get_cf_values(cf_multi_enum, mario).value.values_list('pk', flat=True),
        }
        self.assertIn(m_enum1.id, values_set)
        self.assertIn(m_enum3.id, values_set)

        # Multi-Enum empty
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities': e_ids,
                # 'field_value': [],
                formfield_name: [],
            },
        ))

        DoesNotExist = CustomFieldMultiEnum.DoesNotExist
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(mario))
        self.assertRaises(DoesNotExist, get_cf_values, cf_multi_enum, self.refresh(luigi))

    def test_custom_field_deleted(self):
        self.login()

        cfield = CustomField.objects.create(
            name='int', content_type=FakeContact, field_type=CustomField.INT,
            is_deleted=True,
        )
        mario, luigi, url = self.create_2_contacts_n_url(
            # field=_CUSTOMFIELD_FORMAT.format(cfield.id),
            field=cfield,
        )
        # self.assertGET(400, url)
        self.assertGET404(url)

    def test_other_field_validation_error_1_entity(self):
        user = self.login()

        empty_user1 = get_user_model().objects.create_user(
            username='empty1', first_name='', last_name='', email='',
        )
        empty_contact1 = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user1,
        )

        field_name = 'last_name'
        response = self.assertPOST200(
            self.build_bulkupdate_uri(model=FakeContact, field=field_name),
            data={
                'entities': [empty_contact1.id],
                field_name: 'Bros',
            },
        )
        self.assertFormError(
            response, 'form', None,
            _('This Contact is related to a user and must have a first name.'),
        )

    def test_other_field_validation_error_several_entities(self):
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

        field_name = 'last_name'
        build_uri = partial(self.build_bulkupdate_uri, model=FakeContact, field=field_name)
        self.assertGET200(build_uri(entities=[empty_contact1, empty_contact2, mario]))

        # ---
        response = self.client.post(
            build_uri(),
            data={
                'entities': [empty_contact1.id, empty_contact2.id, mario.id],
                # 'field_value': 'Bros',
                field_name: 'Bros',
            },
        )
        self.assertNoFormError(response)

        get_context = response.context.get
        self.assertEqual(3, get_context('initial_count'))
        self.assertEqual(1, get_context('success_count'))
        self.assertEqual(2, len(get_context('errors')))

        self.assertContains(
            response,
            _('This Contact is related to a user and must have a first name.'),
            count=2,
        )


class InnerEditTestCase(_BulkEditTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #
    #     InnerEdition.bulk_update_registry = bulk_update._BulkUpdateRegistry()
    #
    # @classmethod
    # def tearDownClass(cls):
    #     super().tearDownClass()
    #
    #     InnerEdition.bulk_update_registry = cls._original_bulk_update_registry
    def setUp(self):
        super().setUp()
        self._original_bulk_update_registry = InnerEdition.bulk_update_registry

    def tearDown(self):
        super().tearDown()
        InnerEdition.bulk_update_registry = self._original_bulk_update_registry

    def create_contact(self):
        return FakeContact.objects.create(user=self.user, first_name='Mario', last_name='Bros')

    def create_orga(self):
        return FakeOrganisation.objects.create(user=self.user, name='Mushroom kingdom')

    def test_callback_url(self):
        self.login()

        mario = self.create_contact()
        cb_url = mario.get_lv_absolute_url()
        response = self.assertGET200(
            self.build_inneredit_uri(mario, 'first_name') + f'&callback_url={cb_url}'
        )
        self.assertEqual(
            '<a href="{url}">{label}</a>'.format(
                url=f'{mario.get_edit_absolute_url()}?callback_url={cb_url}',
                label=_('Full edition form'),
            ),
            response.context.get('help_message'),
        )

    def test_regular_field(self):
        self.login()

        mario = self.create_contact()
        # self.assertGET(400, self.build_inneredit_url(mario, 'unknown'))
        self.assertGET404(self.build_inneredit_uri(mario, 'unknown'))

        field_name = 'first_name'
        # url = self.build_inneredit_url(mario, 'first_name')
        url = self.build_inneredit_uri(mario, field_name)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt = response1.context.get
        self.assertEqual(_('Edit «{object}»').format(object=mario), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt('submit_label'))
        self.assertIsNone(get_ctxt('help_message'))

        # ---
        first_name = 'Luigi'
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'entities_lbl': [str(mario)],
                # 'field_value': first_name,
                field_name: first_name,
            },
        ))
        self.assertEqual(first_name, self.refresh(mario).first_name)

    def test_regular_field_validation(self):
        self.login()

        mario = self.create_contact()
        field_name = 'birthday'
        response = self.assertPOST200(
            # self.build_inneredit_url(mario, 'birthday'),
            self.build_inneredit_uri(mario, field_name),
            # data={'field_value': 'whatever'},
            data={field_name: 'whatever'},
        )
        # self.assertFormError(response, 'form', 'field_value', _('Enter a valid date.'))
        self.assertFormError(response, 'form', field_name, _('Enter a valid date.'))

    def test_regular_field_not_allowed(self):
        "No permission."
        self.login(
            is_superuser=False, creatable_models=[FakeContact],
            allowed_apps=['documents'],
        )
        self._set_all_creds_except_one(EntityCredentials.CHANGE)

        mario = self.create_contact()
        self.assertFalse(self.user.has_perm_to_change(mario))
        # self.assertGET403(self.build_inneredit_url(mario, 'first_name'))
        self.assertGET403(self.build_inneredit_uri(mario, 'first_name'))

    def test_regular_field_required(self):
        self.login()

        mario = self.create_contact()
        field_name = 'last_name'
        response = self.assertPOST200(
            # self.build_inneredit_url(mario, 'last_name'),
            self.build_inneredit_uri(mario, field_name),
            data={
                # 'entities_lbl': [str(mario)],
                # 'field_value': '',
                field_name: '',
            },
        )
        self.assertFormError(
            # response, 'form', 'field_value', _('This field is required.'),
            response, 'form', field_name, _('This field is required.'),
        )

    def test_regular_field_not_editable(self):
        self.login()

        mario = self.create_contact()
        self.assertFalse(mario._meta.get_field('is_user').editable)

        # build_url = self.build_inneredit_url
        build_uri = self.build_inneredit_uri
        uri = build_uri(mario, 'is_user')
        # self.assertGET(400, url)
        self.assertGET404(uri)
        # self.assertPOST(400, url, data={'field_value': self.other_user.id})
        self.assertPOST404(uri, data={'is_user': self.other_user.id})

        # Fields without form-field
        # self.assertGET(400, build_url(mario, 'id'))
        self.assertGET404(build_uri(mario, 'id'))
        # self.assertGET(400, build_url(mario, 'cremeentity_ptr'))
        self.assertGET404(build_uri(mario, 'cremeentity_ptr'))

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

        # build_url = partial(self.build_inneredit_url, mario)
        # self.assertGET(400, build_url(hidden_fname))
        # self.assertGET(400, build_url(hidden_fkname))
        # self.assertGET(400, build_url('address__' + hidden_subfname))
        build_uri = partial(self.build_inneredit_uri, mario)
        self.assertGET404(build_uri(hidden_fname))
        self.assertGET404(build_uri(hidden_fkname))
        self.assertGET404(build_uri('address__' + hidden_subfname))

    def test_regular_field_fields_config_required01(self):
        self.login()

        field_name = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(field_name, {FieldsConfig.REQUIRED: True})],
        )

        mario = self.create_contact()
        # uri = self.build_inneredit_url(mario, field_name)
        uri = self.build_inneredit_uri(mario, field_name)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            edition_f = response1.context['form'].fields[field_name]

        self.assertIsInstance(edition_f, CharField)
        self.assertTrue(edition_f.required)

        # ---
        response2 = self.assertPOST200(
            uri,
            data={
                # 'entities_lbl': [str(mario)],
                # 'field_value': '',
                field_name: '',
            },
        )
        self.assertFormError(
            # response2, 'form', 'field_value', _('This field is required.'),
            response2, 'form', field_name, _('This field is required.'),
        )

    def test_regular_field_fields_config_required02(self):
        "The required field is not edited & is not filled."
        self.login()

        field_name1 = 'phone'
        field_name2 = 'mobile'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(field_name2, {FieldsConfig.REQUIRED: True})],
        )

        mario = self.create_contact()
        uri = self.build_inneredit_uri(mario, field_name1)
        response1 = self.assertGET200(uri)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn(field_name1, fields)

        field2 = fields.get(field_name2)
        # TODO?
        # self.assertIsInstance(field2, CharField)
        # self.assertTrue(field2.required)
        self.assertIsNone(field2)

        # ---
        response2 = self.assertPOST200(
            uri,
            data={
                field_name1: '123456',
                # field_name2: '',  # Not filled
            },
        )
        self.assertFormError(
            # TODO?
            # response2, 'form', field_name2, _('This field is required.'),
            response2, 'form', None,
            _('The field «{}» has been configured as required.').format(_('Mobile')),
        )

        # TODO?
        # # ---
        # value2 = '8463469'
        # response3 = self.client.post(
        #     uri,
        #     data={
        #         field_name1: value1,
        #         field_name2: value2,
        #     },
        # )
        # self.assertNoFormError(response3)
        #
        # mario = self.refresh(mario)
        # self.assertEqual(value1, getattr(mario, field_name1))
        # self.assertEqual(value2, getattr(mario, field_name2))

    def test_regular_field_many2many(self):
        user = self.login()

        create_cat = FakeImageCategory.objects.create
        categories = [create_cat(name='A'), create_cat(name='B'), create_cat(name='C')]

        image = self.create_image('image', user, categories)
        # self.assertListEqual([*image.categories.all()], categories)
        image.categories.set([categories[1]])

        # url = self.build_inneredit_url(image, 'categories')
        m2m_name = 'categories'
        uri = self.build_inneredit_uri(image, m2m_name)

        response1 = self.assertGET200(uri)

        with self.assertNoException():
            form1 = response1.context['form']
            edition_f = form1.fields[m2m_name]

        self.assertIsInstance(edition_f, config_fields.CreatorModelMultipleChoiceField)
        self.assertListEqual([categories[1]], form1.initial.get(m2m_name))

        # ---
        response2 = self.client.post(
            # url, data={'field_value': [categories[0].pk, categories[2].pk]},
            uri, data={m2m_name: [categories[0].pk, categories[2].pk]},
        )
        self.assertNoFormError(response2)

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

        # url = self.build_inneredit_url(image, 'categories')
        m2m_name = 'categories'
        uri = self.build_inneredit_uri(image, m2m_name)
        response = self.assertPOST200(
            # url, data={'field_value': [categories[0].pk, invalid_pk]},
            uri, data={m2m_name: [categories[0].pk, invalid_pk]},
        )
        self.assertFormError(
            # response, 'form', 'field_value',
            response, 'form', m2m_name,
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': invalid_pk,
            },
        )
        self.assertCountEqual(categories, self.refresh(image).categories.all())

    def test_regular_field_unique(self):
        user = self.login()

        InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeActivity)

        atype = FakeActivityType.objects.first()
        activity = FakeActivity.objects.create(user=user, title='Comiket', type=atype)

        field_name = 'title'
        uri = self.build_inneredit_uri(activity, field_name)
        self.assertGET200(uri)

        title = f'{activity.title} (edited)'
        response2 = self.client.post(uri, data={field_name: title})
        self.assertNoFormError(response2)
        self.assertEqual(title, self.refresh(activity).title)

    def test_regular_field_invalid_model(self):
        "Neither an entity & neither related to an entity."
        self.login()

        sector = FakeSector.objects.all()[0]
        # self.assertGET403(self.build_inneredit_url(sector, 'title'))
        response = self.client.get(self.build_inneredit_uri(sector, 'title'))
        self.assertIn(
            escape(f'This model is not a entity model: {FakeSector}'),
            response.content.decode(),
        )

    # def test_regular_field_innerform(self):
    #     self.login()
    #
    #     class _InnerEditName(BulkDefaultEditForm):
    #         def clean(self):
    #             raise ValidationError('invalid name')
    #
    #     InnerEdition.bulk_update_registry.register(
    #         FakeContact, innerforms={'last_name': _InnerEditName},
    #     )
    #
    #     mario = self.create_contact()
    #     url = self.build_inneredit_url(mario, 'last_name')
    #     self.assertGET200(url)
    #
    #     response = self.assertPOST200(url, data={'field_value': 'luigi'})
    #     self.assertFormError(response, 'form', '', 'invalid name')
    def test_regular_field_overrider(self):
        self.login()

        field_name = 'last_name'

        class UpperOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                return CharField()

            def post_clean_instance(this, *, instance, value, form):
                setattr(instance, field_name, value.upper())

        InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(UpperOverrider)

        mario = self.create_contact()
        uri = self.build_inneredit_uri(mario, field_name)
        self.assertGET200(uri)

        self.assertNoFormError(
            self.client.post(uri, data={f'override-{field_name}': 'luigi'})
        )
        self.assertEqual('LUIGI', self.refresh(mario).last_name)

    # def test_regular_field_innerform_fielderror(self):
    #     self.login()
    #
    #     class _InnerEditName(BulkDefaultEditForm):
    #         def _bulk_clean_entity(self, entity, values):
    #             BulkDefaultEditForm._bulk_clean_entity(self, entity, values)
    #             raise ValidationError('invalid name')
    #
    #     InnerEdition.bulk_update_registry.register(
    #         FakeContact, innerforms={'last_name': _InnerEditName},
    #     )
    #
    #     mario = self.create_contact()
    #     url = self.build_inneredit_url(mario, 'last_name')
    #     self.assertGET200(url)
    #
    #     response = self.assertPOST200(url, data={'field_value': 'luigi'})
    #     self.assertFormError(response, 'form', None, 'invalid name')

    def test_regular_field_overrider_validation_error(self):
        self.login()

        field_name = 'last_name'
        error_msg = 'Invalid name'

        class ForbiddenOverrider(bulk_update.FieldOverrider):
            field_names = [field_name]

            def formfield(self, instances, user, **kwargs):
                return CharField()

            def post_clean_instance(this, *, instance, value, form):
                raise ValidationError(error_msg)

        InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeContact).add_overriders(ForbiddenOverrider)

        mario = self.create_contact()

        formfield_name = f'override-{field_name}'
        response = self.assertPOST200(
            self.build_inneredit_uri(mario, 'last_name'),
            data={formfield_name: 'luigi'},
        )
        self.assertFormError(response, 'form', formfield_name, error_msg)

    def test_regular_field_file01(self):
        user = self.login()

        InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
        registry.register(FakeDocument)

        folder = FakeFolder.objects.create(user=user, title='Earth maps')
        doc = FakeDocument.objects.create(
            user=user, title='Japan map', linked_folder=folder,
        )

        # url = self.build_inneredit_url(doc, 'filedata')
        uri = self.build_inneredit_uri(doc, 'filedata')
        # self.assertGET200(url)
        self.assertGET200(uri)

        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj = self.build_filedata(content, suffix=f'.{settings.ALLOWED_EXTENSIONS[0]}')
        response = self.client.post(
            # url,
            uri,
            data={
                # 'entities_lbl': [str(doc)],
                # 'field_value': file_obj,
                'filedata': file_obj,
            },
        )
        self.assertNoFormError(response)

        filedata = self.refresh(doc).filedata
        self.assertEqual(f'creme_core-tests/{file_obj.base_name}', filedata.name)

        with filedata.open('r') as f:
            self.assertEqual([content], f.readlines())

    # TODO: test FileField + blank=True (need a new fake CremeEntity)
    # def test_regular_field_file02(self):
    #     "Empty data."
    #     user = self.login()
    #
    #     InnerEdition.bulk_update_registry = registry = bulk_update._BulkUpdateRegistry()
    #     registry.register(FakeDocument)
    #
    #     file_path = self.create_uploaded_file(
    #         file_name='InnerEditTestCase_test_regular_field_file02.txt',
    #         dir_name='views',
    #     )
    #
    #     comp = FakeFileComponent.objects.create(filedata=file_path)
    #     bag = FakeFileBag.objects.create(user=user, name='Stuffes', file1=comp)
    #
    #     # url = self.build_inneredit_url(bag, 'file1__filedata')
    #     url = self.build_inneredit_uri(bag, 'file1__filedata')
    #     self.assertGET200(url)
    #
    #     response = self.client.post(
    #         url,
    #         data={
    #             'entities_lbl': [str(bag)],
    #             'field_value-clear': 'on',
    #             'field_value': b'',
    #         },
    #     )
    #     self.assertNoFormError(response)
    #     self.assertEqual('', self.refresh(comp).filedata.name)

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
        # url = self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id))
        uri = self.build_inneredit_uri(mario, cfield)
        # response1 = self.assertGET200(url)
        response1 = self.assertGET200(uri)

        formfield_name = f'custom_field-{cfield.id}'

        with self.assertNoException():
            # field = response1.context['form'].fields['field_value']
            field = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(field, CharField)

        value = 'hihi'
        # response2 = self.client.post(url, data={'field_value': value})
        response2 = self.client.post(uri, data={formfield_name: value})
        self.assertNoFormError(response2)

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
        # url = self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id))
        uri = self.build_inneredit_uri(mario, cfield)
        # response = self.assertGET200(url)
        response = self.assertGET200(uri)

        with self.assertNoException():
            # field = response.context['form'].fields['field_value']
            field = response.context['form'].fields[f'custom_field-{cfield.id}']

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
        # self.assertGET(
        #     400,
        #     self.build_inneredit_url(mario, _CUSTOMFIELD_FORMAT.format(cfield.id)),
        # )
        self.assertGET404(self.build_inneredit_uri(mario, cfield))

    # def test_related_subfield_missing(self):
    #     self.login()
    #     orga = self.create_orga()
    #
    #     url = self.build_inneredit_url(orga, 'address__city')
    #     self.assertGET200(url)
    #
    #     city = 'Marseille'
    #     response = self.assertPOST200(url, data={'field_value': city})
    #     self.assertFormError(
    #         response, 'form', None,
    #         _('The field «{}» is empty').format(_('Billing address')),
    #     )

    def test_related_subfield(self):
        self.login()
        orga = self.create_orga()
        # orga.address = FakeAddress.objects.create(entity=orga, value='address 1')
        # orga.save()

        # url = self.build_inneredit_url(orga, 'address__city')
        # self.assertGET200(url)
        self.assertGET404(self.build_inneredit_uri(orga, 'address__city'))

        # city = 'Marseille'
        # response = self.client.post(url, data={'field_value': city})
        # self.assertNoFormError(response)
        # self.assertEqual(city, self.refresh(orga).address.city)

    def test_related_field(self):
        self.login()
        orga = self.create_orga()
        orga.address = FakeAddress.objects.create(entity=orga, value='address 1')
        orga.save()

        # self.assertGET(400, self.build_inneredit_url(orga, 'address'))
        self.assertGET404(self.build_inneredit_uri(orga, 'address'))

    # def test_manytomany_field(self):
    #     """Edition of a ManyToManyField
    #     (needs a special hack with initial values for this case).
    #     """
    #     user = self.login()
    #     image = FakeImage.objects.create(user=user, name='Konoha by night')
    #     # self.assertGET(200, self.build_inneredit_url(image, 'categories'))
    #     self.assertGET200(self.build_inneredit_uri(image, 'categories'))

    def test_other_field_validation_error(self):
        user = self.login()
        empty_user = get_user_model().objects.create_user(
            username='empty', first_name='', last_name='', email='',
        )
        empty_contact = FakeContact.objects.create(
            user=user, first_name='', last_name='', is_user=empty_user,
        )

        field_name = 'last_name'
        # url = self.build_inneredit_url(empty_contact, 'last_name')
        uri = self.build_inneredit_uri(empty_contact, field_name)
        # self.assertGET200(url)
        self.assertGET200(uri)

        # response2 = self.assertPOST200(url, data={'field_value': 'Bros'})
        response2 = self.assertPOST200(uri, data={field_name: 'Bros'})
        self.assertFormError(
            response2, 'form', None,
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

        field_name = 'last_name'
        # url = self.build_inneredit_url(empty_contact, 'last_name')
        uri = self.build_inneredit_uri(empty_contact, field_name)
        # self.assertGET200(url)
        self.assertGET200(uri)

        # response = self.assertPOST200(url, data={'field_value': ''})
        response = self.assertPOST200(uri, data={field_name: ''})
        self.assertFormError(
            # response, 'form', 'field_value', _('This field is required.'),
            response, 'form', field_name, _('This field is required.'),
        )

    def test_multi_fields(self):
        "2 regular fields + 1 CustomField."
        self.login()

        mario = self.create_contact()

        cfield = CustomField.objects.create(
            content_type=mario.entity_type, name='Coins', field_type=CustomField.INT,
        )

        url = self.build_inneredit_uri(mario, 'first_name', 'phone', cfield)
        response1 = self.assertGET200(url)
        # TODO: template with no block?
        # self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(_('Edit «{object}»').format(object=mario), get_ctxt1('title'))
        self.assertEqual(_('Save the modifications'),               get_ctxt1('submit_label'))

        # ---
        first_name = 'Luigi'
        phone = '123 456'
        coins = 569
        response = self.client.post(
            url,
            data={
                # 'entities_lbl': [str(mario)],  # TODO?
                # 'regular_field-first_name': first_name,  # TODO?
                'first_name': first_name,
                'phone':      phone,
                f'custom_field-{cfield.id}': coins,
            },
        )
        self.assertNoFormError(response)

        mario = self.refresh(mario)
        self.assertEqual(first_name, mario.first_name)
        self.assertEqual(phone,      mario.phone)
        self.assertEqual(
            coins,
            cfield.value_class.objects.get(custom_field=cfield, entity=mario).value,
        )

    def test_multi_fields_errors01(self):
        self.login()

        mario = self.create_contact()
        self.assertGET404(self.build_inneredit_uri(mario))  # No field
        self.assertGET404(self.build_inneredit_uri(mario, 'unknown', 'phone'))  # Invalid field

    def test_multi_fields_errors02(self):
        "Hidden field given."
        self.login()

        mario = self.create_contact()
        hidden = 'phone'
        FieldsConfig.objects.create(
            content_type=mario.entity_type,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        self.assertGET404(self.build_inneredit_uri(mario, 'first_name', hidden))
