from functools import partial

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_core.bricks import EntityJobErrorsBrick, TrashBrick
from creme.creme_core.creme_jobs import reminder_type, trash_cleaner_type
# from creme.creme_core.models import CremeEntity
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    EntityJobResult,
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
    FakeTicket,
    HistoryLine,
    Job,
    Relation,
    RelationType,
    TrashCleaningCommand,
    history,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


@override_settings(ENTITIES_DELETION_ALLOWED=True)
class EntityViewsTestCase(BrickTestCaseMixin, CremeTestCase):
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

        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

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

    def test_delete_entity(self):
        "is_deleted=False -> trash."
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

    def test_delete_entity__definitive_deletion(self):
        "is_deleted=True -> real deletion."
        user = self.login_as_root_and_get()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        url = self._build_delete_url(entity)
        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_lv_absolute_url())
        self.assertDoesNotExist(entity)

    def test_delete_entity__permissions(self):
        "No DELETE credentials."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!DELETE')

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        self.assertPOST403(self._build_delete_url(entity))
        entity = self.assertStillExists(entity)
        self.assertFalse(entity.is_deleted)

    def test_delete_entity__not_deletable(self):
        """<get_delete_absolute_url()> returns an empty URL."""
        user = self.login_as_root_and_get()
        ticket = FakeTicket.objects.create(user=user, title='Ticket#1')
        response = self.client.post(self._build_delete_url(ticket))
        self.assertContains(
            response,
            # text=_('«{entity}» does not use the generic deletion view.').format(entity=ticket),
            text=_('This type of entity does not use the generic deletion view.'),
            status_code=409, html=True,
        )

    def test_delete_entity__callback(self):
        user = self.login_as_root_and_get()
        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        cb_url = reverse('creme_core__my_page')
        self.assertRedirects(
            self.client.post(self._build_delete_url(entity), data={'callback_url': cb_url}),
            cb_url,
        )

    def test_delete_entity__callback_ajax(self):
        user = self.login_as_root_and_get()
        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        cb_url = reverse('creme_core__my_page')
        response = self.assertPOST200(
            self._build_delete_url(entity),
            data={'callback_url': cb_url},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(cb_url, response.content.decode())

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entity__disabled(self):
        "Deletion is disabled in settings."
        self.login_as_root()

        entity = FakeOrganisation.objects.create(user=self.create_user(), name='Nerv')
        url = self._build_delete_url(entity)

        self.assertPOST200(url, follow=True)
        entity = self.assertStillExists(entity)
        self.assertTrue(entity.is_deleted)

        response = self.client.post(url)
        self.assertStillExists(entity)
        self.assertContains(
            response,
            # _(
            #     '«{entity}» can not be deleted because the deletion has '
            #     'been disabled by the administrator.'
            # ).format(entity=entity),
            _('Deletion has been disabled by your administrator'),
            status_code=409,
            html=True,
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entity__disabled_but_staff(self):
        "Logged as staff."
        self.login_as_super(is_staff=True)

        entity = FakeOrganisation.objects.create(
            user=self.get_root_user(), name='Nerv', is_deleted=True,
        )

        self.assertPOST200(self._build_delete_url(entity), follow=True)
        self.assertDoesNotExist(entity)

    def test_delete_entity__deletor_check(self):
        user = self.login_as_root_and_get()
        other = self.create_user()
        user_contact = FakeContact.objects.create(
            user=user, first_name=other.first_name, last_name=other.last_name,
            is_user=other,
        )

        response = self.client.post(self._build_delete_url(user_contact))
        self.assertStillExists(user_contact)
        self.assertContains(
            response,
            'A user is associated with this contact.',
            status_code=409,
            html=True,
        )

    def test_delete_entity__dependencies(self):
        "Relations (not internal ones) & properties are deleted correctly."
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

        ptype = CremePropertyType.objects.create(text='has eva')
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

    def test_delete_entity__dependencies_error(self):  # TODO: detect dependencies when trashing?
        "Dependencies problem (with internal Relations)."
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
            # _(
            #     '«{entity}» can not be deleted because of its '
            #     'dependencies ({dependencies}).'
            # ).format(
            #     entity=entity01.name,
            #     dependencies=f'is a daughter of «{entity02.name}»',
            # ),
            _(
                'This entity can not be deleted because of its '
                'dependencies ({dependencies}).'
            ).format(dependencies=f'is a daughter of «{entity02.name}»'),
            msg,
        )

    def test_delete_entity__ajax01(self):
        "is_deleted=False -> trash (AJAX version)."
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        response = self.assertPOST200(
            self._build_delete_url(entity),
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

    def test_delete_entity__ajax02(self):
        "is_deleted=True -> real deletion(AJAX version)."
        user = self.login_as_root_and_get()

        # To get a get_lv_absolute_url() method
        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        response = self.assertPOST200(
            self._build_delete_url(entity),
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
            user = self.login_as_root_and_get()
            invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
            line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice)

            self.assertPOST200(self._build_delete_url(line), follow=True)
            self.assertDoesNotExist(line)

    def test_delete_entities(self):
        user = self.login_as_root_and_get()

        # create_entity = partial(CremeEntity.objects.create, user=user)
        # entity1, entity2 = (create_entity() for __ in range(2))
        # entity3, entity4 = (create_entity(is_deleted=True) for __ in range(2))
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1, entity2 = (create_orga(name=f'Orga #{i+1}') for i in range(2))
        entity3, entity4 = (
            create_orga(name=f'Del Orga #{i+1}', is_deleted=True) for i in range(2)
        )

        url = self.DEL_ENTITIES_URL
        self.assertPOST404(url)
        self.assertPOST(400, url, data={'ids': ''})
        self.assertPOST(400, url, data={'ids': 'notanint'})

        data = {'ids': f'{entity1.id},{entity2.id},{entity3.id}'}
        self.assertGET405(url, data=data)

        response = self.assertPOST200(url, data=data)
        self.assertEqual(response.content.decode(), _('Operation successfully completed'))

        # entity1 = self.get_object_or_fail(CremeEntity, pk=entity1.id)
        entity1 = self.get_object_or_fail(FakeOrganisation, pk=entity1.id)
        self.assertTrue(entity1.is_deleted)

        # entity2 = self.get_object_or_fail(CremeEntity, pk=entity2.id)
        entity2 = self.get_object_or_fail(FakeOrganisation, pk=entity2.id)
        self.assertTrue(entity2.is_deleted)

        self.assertDoesNotExist(entity3)
        self.assertStillExists(entity4)

    def test_delete_entities__missing(self):
        "Some entities do not exist."
        user = self.login_as_root_and_get()

        # create_entity = partial(CremeEntity.objects.create, user=user)
        # entity1, entity2 = (create_entity() for __ in range(2))
        create_entity = partial(FakeOrganisation.objects.create, user=user)
        entity1, entity2 = (create_entity(name=f'Orga #{i+1}') for i in range(2))

        response = self.assertPOST404(
            self.DEL_ENTITIES_URL,
            data={'ids': f'{entity1.id},{entity2.id + 1},'},
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

        # entity1 = self.get_object_or_fail(CremeEntity, pk=entity1.id)
        entity1 = self.get_object_or_fail(FakeOrganisation, pk=entity1.id)
        self.assertTrue(entity1.is_deleted)

        # self.get_object_or_fail(CremeEntity, pk=entity2.id)
        self.get_object_or_fail(FakeOrganisation, pk=entity2.id)

    def test_delete_entities__dependencies_error(self):
        "Dependencies problem (with internal Relations)."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Nerv', is_deleted=True)
        entity2 = create_orga(name='Seele')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_daughter', 'is a daughter of'),
            ('test-object_daughter',  'has a daughter'),
            is_internal=True,
        )[0]
        Relation.objects.create(
            user=user, type=rtype, subject_entity=entity1, object_entity=entity2,
        )

        response = self.assertPOST409(self.DEL_ENTITIES_URL, data={'ids': f'{entity1.id}'})
        self.assertStillExists(entity1)
        self.assertStillExists(entity2)
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [
                    _('{entity}: {error}').format(
                        entity=entity1.name,
                        error=_(
                            'This entity can not be deleted because of its '
                            'dependencies ({dependencies}).'
                        ).format(dependencies=f'is a daughter of «{entity2.name}»'),
                    ),
                ],
            },
            response.json(),
        )

    def test_delete_entities__not_allowed(self):
        "Some entities deletion is not allowed."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        # forbidden = CremeEntity.objects.create(user=self.get_root_user())
        # allowed   = CremeEntity.objects.create(user=user)
        forbidden = FakeOrganisation.objects.create(name='KO', user=self.get_root_user())
        allowed   = FakeOrganisation.objects.create(name='OK', user=user)

        response = self.assertPOST403(
            self.DEL_ENTITIES_URL,
            data={'ids': f'{forbidden.id},{allowed.id},'},
        )
        self.assertDictEqual(
            {
                'count': 2,
                'errors': [
                    # _('{entity}: <b>Permission denied</b>').format(
                    #     entity=forbidden.allowed_str(user),
                    # ),
                    _('{entity}: {error}').format(
                        entity=forbidden.allowed_str(user),
                        error=_('You are not allowed to delete this entity by your role'),
                    ),
                ],
            },
            response.json(),
        )

        # allowed = self.get_object_or_fail(CremeEntity, pk=allowed.id)
        allowed = self.get_object_or_fail(FakeOrganisation, pk=allowed.id)
        self.assertTrue(allowed.is_deleted)

        # self.get_object_or_fail(CremeEntity, pk=forbidden.id)
        self.get_object_or_fail(FakeOrganisation, pk=forbidden.id)

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entities__disabled01(self):
        "Deletion is disabled in settings."
        user = self.login_as_root_and_get()

        # create_entity = partial(CremeEntity.objects.create, user=user)
        # entity1, entity2 = (create_entity() for __ in range(2))
        create_entity = partial(FakeOrganisation.objects.create, user=user)
        entity1, entity2 = (create_entity(name=f'Orga #{i+1}') for i in range(2))

        url = self.DEL_ENTITIES_URL
        data = {'ids': f'{entity1.id},{entity2.id}'}
        response1 = self.assertPOST200(url, data=data)
        self.assertEqual(response1.content.decode(), _('Operation successfully completed'))

        entity1 = self.assertStillExists(entity1)
        self.assertTrue(entity1.is_deleted)

        self.assertStillExists(entity2)

        # ---
        response2 = self.assertPOST409(url, data=data)
        # msg = _(
        #     '«{entity}» can not be deleted because the deletion has been '
        #     'disabled by the administrator.'
        # )
        fmt = _('{entity}: {error}').format
        error_msg = _('Deletion has been disabled by your administrator')
        self.assertDictEqual(
            {
                'count': 2,
                'errors': [
                    # msg.format(entity=entity1),
                    # msg.format(entity=entity2),
                    fmt(entity=entity1, error=error_msg),
                    fmt(entity=entity2, error=error_msg),
                ],
            },
            response2.json(),
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=False)
    def test_delete_entities__disabled02(self):
        "Logged as staff."
        user = self.login_as_super(is_staff=True)

        # create_entity = partial(CremeEntity.objects.create, user=user, is_deleted=True)
        # entity1, entity2 = (create_entity() for __ in range(2))
        create_entity = partial(FakeOrganisation.objects.create, user=user, is_deleted=True)
        entity1, entity2 = (create_entity(name=f'Orga #{i+1}') for i in range(2))

        response = self.assertPOST200(
            self.DEL_ENTITIES_URL, data={'ids': f'{entity1.id},{entity2.id}'},
        )
        self.assertEqual(response.content.decode(), _('Operation successfully completed'))
        self.assertDoesNotExist(entity1)
        self.assertDoesNotExist(entity2)

    def test_delete_entities__not_registered(self):
        user = self.login_as_root_and_get()
        entity = FakeTicket.objects.create(user=user, title='Ticket #1')
        response = self.assertPOST409(
            self.DEL_ENTITIES_URL, data={'ids': f'{entity.id}'},
        )
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [
                    _('{entity}: {error}').format(
                        entity=entity,
                        error=_('This type of entity does not use the generic deletion view.'),
                    )
                ],
            },
            response.json(),
        )

    def test_delete_entities__deletor_check(self):
        user = self.login_as_root_and_get()
        other = self.create_user()
        user_contact = FakeContact.objects.create(
            user=user, first_name=other.first_name, last_name=other.last_name,
            is_user=other,
        )
        response = self.assertPOST409(
            self.DEL_ENTITIES_URL, data={'ids': f'{user_contact.id}'},
        )
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [
                    _('{entity}: {error}').format(
                        entity=user_contact,
                        error='A user is associated with this contact.',
                    )
                ],
            },
            response.json(),
        )

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

    def test_trash_view01(self):
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

    def test_restore_entity(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW', 'DELETE'])

        entity = FakeOrganisation.objects.create(
            user=user, name='Nerv', is_deleted=True,
        )
        url = self._build_restore_url(entity)

        self.assertGET405(url)
        self.assertRedirects(self.client.post(url), entity.get_absolute_url())

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity__ajax(self):
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)
        self.assertPOST200(
            self._build_restore_url(entity), headers={'X-Requested-With': 'XMLHttpRequest'},
        )

        entity = self.get_object_or_fail(FakeOrganisation, pk=entity.pk)
        self.assertFalse(entity.is_deleted)

    def test_restore_entity__not_deleted(self):
        user = self.login_as_root_and_get()

        entity = FakeOrganisation.objects.create(user=user, name='Nerv')
        url = self._build_restore_url(entity)
        self.assertGET405(url)
        self.assertPOST404(url)

    def test_restore_entity__permissions(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])  # 'DELETE'

        entity = FakeOrganisation.objects.create(user=user, name='Nerv', is_deleted=True)

        self.assertPOST403(self._build_restore_url(entity), follow=True)

    # TODO?
    # def test_restore_entity__auxiliary(self):
    #     user = self.login_as_root_and_get()
    #     invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
    #     line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice, is_deleted=True)
    #     response = self.assertPOST409(self._build_restore_url(line))
    #     self.assertContains(
    #         response, text='Can not restore an auxiliary entity', status_code=409,
    #     )

    # TODO?
    # def test_restore_entity__not_deletable(self):
    #     user = self.login_as_root_and_get()
    #     ticket = FakeTicket.objects.create(user=user, title='Ticket#1', is_deleted=True)
    #     response = self.client.post(self._build_restore_url(ticket))
    #     self.assertContains(
    #         response,
    #         text=_('This model does not use the generic deletion view.'),
    #         status_code=409, html=True,
    #     )

    def test_empty_trash(self):
        user = self.login_as_standard(allowed_apps=('creme_core',))  # 'persons'
        # self._set_all_perms_on_own(user)
        self.add_credentials(user.role, own='*')

        create_contact = partial(FakeContact.objects.create, user=user, is_deleted=True)
        contact1 = create_contact(first_name='Lawrence', last_name='Kraft')
        contact2 = create_contact(first_name='Holo',     last_name='Wolf')
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

    def test_empty_trash__dependencies(self):
        "Dependencies problem."
        user = self.login_as_root_and_get()

        create_contact = partial(
            FakeContact.objects.create,
            user=user, last_name='Doe', is_deleted=True,
        )
        entity1 = create_contact(first_name='#1')
        entity2 = create_contact(first_name='#2')
        entity3 = create_contact(first_name='#3')  # Not linked => can be deleted
        entity4 = create_contact(first_name='#4', is_deleted=False)
        entity5 = FakeOrganisation.objects.create(
            user=user, name='Acme', is_deleted=True,
        )  # Not linked => can be deleted

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_linked', 'is linked to'),
            ('test-object_linked',  'is linked to'),
            is_internal=True,
        )[0]
        Relation.objects.create(
            user=user, type=rtype, subject_entity=entity1, object_entity=entity2,
        )

        self.assertPOST200(self.EMPTY_TRASH_URL)

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertStillExists(entity1)
        self.assertStillExists(entity2)
        self.assertDoesNotExist(entity3)
        self.assertStillExists(entity4)
        self.assertDoesNotExist(entity5)

        jresults = {jr.entity_id: jr for jr in EntityJobResult.objects.filter(job=job)}
        self.assertEqual(2, len(jresults), jresults)

        jresult1 = jresults.get(entity1.id)
        self.assertIsNotNone(jresult1)
        self.assertEqual(entity1.entity_type, jresult1.entity_ctype)
        self.assertListEqual(
            [_('Can not be deleted because of its dependencies.')],
            jresult1.messages,
        )

        self.assertIn(entity2.id, jresults)

        result_brick = self.get_alone_element(trash_cleaner_type.results_bricks)
        self.assertIsInstance(result_brick, EntityJobErrorsBrick)

    def test_empty_trash__perms(self):
        "Credentials on specific ContentType."
        # NB: can delete ESET_OWN
        user = self.login_as_standard(allowed_apps=('creme_core',))
        self.add_credentials(user.role, own='*')
        self.add_credentials(user.role, all='*', model=FakeOrganisation)

        other_user = self.get_root_user()

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

    def test_empty_trash__existing_job(self):
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
    def test_empty_trash__deletion_disabled(self):
        "Deletion is disabled."
        self.login_as_root()
        self.assertContains(
            self.client.post(self.EMPTY_TRASH_URL),
            _('The definitive deletion has been disabled by the administrator.'),
            status_code=409,
            html=True,
        )

    def test_empty_trash__deletion_disabled_for_model(self):
        user = self.login_as_root_and_get()

        ticket = FakeTicket.objects.create(user=user, title='Golden', is_deleted=True)

        self.assertPOST200(self.EMPTY_TRASH_URL)

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertStillExists(ticket)

        jresult = self.get_alone_element(EntityJobResult.objects.filter(job=job))
        self.assertEqual(ticket.entity_type, jresult.entity_ctype)
        self.assertListEqual(
            [_('This type of entity does not use the generic deletion way.')],
            jresult.messages,
        )

    def test_empty_trash__deletor_check(self):
        user = self.login_as_root_and_get()

        user_contact = FakeContact.objects.create(
            user=user, last_name='Doe', is_deleted=True, is_user=self.create_user(),
        )

        self.assertPOST200(self.EMPTY_TRASH_URL)

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertStillExists(user_contact)

        jresult = self.get_alone_element(EntityJobResult.objects.filter(job=job))
        self.assertEqual(user_contact.entity_type, jresult.entity_ctype)
        self.assertListEqual(
            ['A user is associated with this contact.'],
            jresult.messages,
        )

    @staticmethod
    def _build_finish_cleaner_url(job):
        return reverse('creme_core__finish_trash_cleaner', args=(job.id,))

    def test_finish_cleaner(self):
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

    def test_finish_cleaner__perms(self):
        "Other user's job."
        self.login_as_root()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=self.create_user(),
            status=Job.STATUS_OK,
        )

        self.assertPOST403(self._build_finish_cleaner_url(job))

    def test_finish_cleaner__job_not_finished(self):
        "Job not finished."
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_WAIT,
        )

        self.assertPOST409(self._build_finish_cleaner_url(job))

    def test_finish_cleaner__bad_job(self):
        "Not cleaner job."
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            type_id=reminder_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        self.assertPOST404(self._build_finish_cleaner_url(job))

    def test_finish_cleaner__errors(self):
        "Job with errors."
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            type_id=trash_cleaner_type.id,
            user=user,
            status=Job.STATUS_OK,
        )
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        EntityJobResult.objects.create(job=job, real_entity=nerv)

        url = self._build_finish_cleaner_url(job)
        redir_url = job.get_absolute_url()
        response1 = self.client.post(url)
        self.assertRedirects(response1, redir_url)
        self.assertStillExists(job)

        # AJAX version
        response2 = self.assertPOST200(url, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(redir_url, response2.content.decode())
