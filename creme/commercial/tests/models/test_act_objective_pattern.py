from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from creme.commercial.models import ActObjectivePatternComponent
from creme.creme_core.models import EntityFilter, FakeContact, FakeOrganisation
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..base import CommercialBaseTestCase, skipIfCustomPattern


@skipIfCustomPattern
class ActObjectivePatternTestCase(BrickTestCaseMixin, CommercialBaseTestCase):
    def assertCompNamesEqual(self, comp_qs, *names):
        self.assertCountEqual(names, comp_qs.values_list('name', flat=True))

    def test_get_component_tree(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)

        create_comp = partial(
            ActObjectivePatternComponent.objects.create,
            pattern=pattern, success_rate=1,
        )
        root01 = create_comp(name='Root01')
        root02 = create_comp(name='Root02')

        child01 = create_comp(name='Child 01', parent=root01)
        create_comp(name='Child 11', parent=child01)
        create_comp(name='Child 12', parent=child01)
        create_comp(name='Child 13', parent=child01)

        child02 = create_comp(name='Child 02', parent=root01)
        create_comp(name='Child 21', parent=child02)

        # TODO: test that no additional queries are done ???
        comptree = pattern.get_components_tree()
        self.assertIsList(comptree, length=2)

        rootcomp01 = comptree[0]
        self.assertIsInstance(rootcomp01, ActObjectivePatternComponent)
        self.assertEqual(root01, rootcomp01)
        self.assertEqual(root02, comptree[1])

        children = rootcomp01.get_children()
        self.assertEqual(2, len(children))

        compchild01 = children[0]
        self.assertIsInstance(compchild01, ActObjectivePatternComponent)
        self.assertEqual(child01, compchild01)
        self.assertEqual(3, len(compchild01.get_children()))

        self.assertEqual(1, len(children[1].get_children()))

    def _delete_comp(self, comp):
        ct = ContentType.objects.get_for_model(ActObjectivePatternComponent)

        return self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': comp.id},
        )

    def test_delete_pattern_component(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        comp = ActObjectivePatternComponent.objects.create(
            name='Signed opportunities', pattern=pattern, success_rate=20,
        )
        self.assertNoFormError(self._delete_comp(comp), status=302)
        self.assertDoesNotExist(comp)

    def test_delete_pattern_component__children(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)
        create_comp = partial(
            ActObjectivePatternComponent.objects.create,
            pattern=pattern, success_rate=1,
        )
        comp00 = create_comp(name='Signed opportunities')  # NB: should not be removed
        comp01 = create_comp(name='DELETE ME')
        comp02 = create_comp(name='Will be orphaned01',  parent=comp01)
        comp03 = create_comp(name='Will be orphaned02',  parent=comp01)
        comp04 = create_comp(name='Will be orphaned03',  parent=comp02)
        comp05 = create_comp(name='Smiles done')  # NB: should not be removed
        # NB: should not be removed
        comp06 = create_comp(name='Stand by me',         parent=comp05)

        self.assertNoFormError(self._delete_comp(comp01), status=302)

        self.assertCountEqual(
            [comp00.id, comp05.id, comp06.id],
            pattern.components.values_list('id', flat=True),
        )
        self.assertDoesNotExist(comp01)
        self.assertDoesNotExist(comp02)
        self.assertDoesNotExist(comp03)
        self.assertDoesNotExist(comp04)

    def test_clone(self):
        user = self.login_as_root_and_get()
        pattern = self._create_pattern(user=user)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga    = get_ct(FakeOrganisation)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Ninja', FakeContact, is_custom=True,
        )

        create_comp = partial(
            ActObjectivePatternComponent.objects.create,
            pattern=pattern, success_rate=1,
        )
        comp1 = create_comp(name='1', ctype=ct_orga)

        comp11 = create_comp(name='1.1', parent=comp1, success_rate=20, ctype=ct_contact)
        create_comp(name='1.1.1', parent=comp11)
        create_comp(name='1.1.2', parent=comp11)

        comp12 = create_comp(name='1.2', parent=comp1, ctype=ct_contact, filter=efilter)
        create_comp(name='1.2.1', parent=comp12)
        create_comp(name='1.2.2', parent=comp12)

        comp2 = create_comp(name='2', success_rate=50)

        comp21 = create_comp(name='2.1', parent=comp2)
        create_comp(name='2.1.1', parent=comp21)
        create_comp(name='2.1.2', parent=comp21)

        comp22 = create_comp(name='2.2', parent=comp2)
        create_comp(name='2.2.1', parent=comp22)
        create_comp(name='2.2.2', parent=comp22)

        cloned_pattern = self.clone(pattern)

        filter_comp = partial(
            ActObjectivePatternComponent.objects.filter,
            pattern=cloned_pattern,
        )
        self.assertEqual(14, filter_comp().count())

        cloned_comp1 = self.get_object_or_fail(
            ActObjectivePatternComponent,
            pattern=cloned_pattern, name=comp1.name,
        )
        self.assertIsNone(cloned_comp1.parent)
        self.assertEqual(1, cloned_comp1.success_rate)
        self.assertEqual(ct_orga, cloned_comp1.ctype)
        self.assertIsNone(cloned_comp1.filter)

        with self.assertNoException():
            cloned_comp11, cloned_comp12 = cloned_comp1.children.all()

        self.assertEqual(ct_contact, cloned_comp11.ctype)
        self.assertEqual(efilter,    cloned_comp12.filter)

        self.assertCompNamesEqual(
            filter_comp(parent__name__in=['1.1', '1.2']),
            '1.1.1', '1.1.2', '1.2.1', '1.2.2',
        )

        cloned_comp2 = self.get_object_or_fail(
            ActObjectivePatternComponent,
            pattern=cloned_pattern, name=comp2.name,
        )
        self.assertIsNone(cloned_comp2.parent)
        self.assertEqual(50, cloned_comp2.success_rate)
        self.assertIsNone(cloned_comp2.ctype)
        self.assertIsNone(cloned_comp1.filter)
        self.assertCompNamesEqual(cloned_comp2.children, '2.1', '2.2')

        self.assertCompNamesEqual(
            filter_comp(parent__name__in=['2.1', '2.2']),
            '2.1.1', '2.1.2', '2.2.1', '2.2.2',
        )

    # def test_clone__method(self):  # DEPRECATED
    #     pattern = self._create_pattern()
    #
    #     get_ct = ContentType.objects.get_for_model
    #     ct_contact = get_ct(FakeContact)
    #     ct_orga    = get_ct(FakeOrganisation)
    #
    #     efilter = EntityFilter.objects.smart_update_or_create(
    #         'test-filter01', 'Ninja', FakeContact, is_custom=True,
    #     )
    #
    #     create_comp = partial(
    #         ActObjectivePatternComponent.objects.create,
    #         pattern=pattern, success_rate=1,
    #     )
    #     comp1 = create_comp(name='1', ctype=ct_orga)
    #
    #     comp11 = create_comp(name='1.1', parent=comp1, success_rate=20, ctype=ct_contact)
    #     create_comp(name='1.1.1', parent=comp11)
    #     create_comp(name='1.1.2', parent=comp11)
    #
    #     comp12 = create_comp(name='1.2', parent=comp1, ctype=ct_contact, filter=efilter)
    #     create_comp(name='1.2.1', parent=comp12)
    #     create_comp(name='1.2.2', parent=comp12)
    #
    #     comp2 = create_comp(name='2', success_rate=50)
    #
    #     comp21 = create_comp(name='2.1', parent=comp2)
    #     create_comp(name='2.1.1', parent=comp21)
    #     create_comp(name='2.1.2', parent=comp21)
    #
    #     comp22 = create_comp(name='2.2', parent=comp2)
    #     create_comp(name='2.2.1', parent=comp22)
    #     create_comp(name='2.2.2', parent=comp22)
    #
    #     cloned_pattern = pattern.clone()
    #
    #     filter_comp = partial(
    #         ActObjectivePatternComponent.objects.filter,
    #         pattern=cloned_pattern,
    #     )
    #     self.assertEqual(14, filter_comp().count())
    #
    #     cloned_comp1 = self.get_object_or_fail(
    #         ActObjectivePatternComponent,
    #         pattern=cloned_pattern, name=comp1.name,
    #     )
    #     self.assertIsNone(cloned_comp1.parent)
    #     self.assertEqual(1, cloned_comp1.success_rate)
    #     self.assertEqual(ct_orga, cloned_comp1.ctype)
    #     self.assertIsNone(cloned_comp1.filter)
    #
    #     with self.assertNoException():
    #         cloned_comp11, cloned_comp12 = cloned_comp1.children.all()
    #
    #     self.assertEqual(ct_contact, cloned_comp11.ctype)
    #     self.assertEqual(efilter,    cloned_comp12.filter)
    #
    #     self.assertCompNamesEqual(
    #         filter_comp(parent__name__in=['1.1', '1.2']),
    #         '1.1.1', '1.1.2', '1.2.1', '1.2.2',
    #     )
    #
    #     cloned_comp2 = self.get_object_or_fail(
    #         ActObjectivePatternComponent,
    #         pattern=cloned_pattern, name=comp2.name,
    #     )
    #     self.assertIsNone(cloned_comp2.parent)
    #     self.assertEqual(50, cloned_comp2.success_rate)
    #     self.assertIsNone(cloned_comp2.ctype)
    #     self.assertIsNone(cloned_comp1.filter)
    #     self.assertCompNamesEqual(cloned_comp2.children, '2.1', '2.2')
    #
    #     self.assertCompNamesEqual(
    #         filter_comp(parent__name__in=['2.1', '2.2']),
    #         '2.1.1', '2.1.2', '2.2.1', '2.2.2',
    #     )
