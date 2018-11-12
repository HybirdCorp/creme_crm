# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from creme.creme_core.models import HeaderFilter, EntityFilter  # Relation
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from .. import constants, bricks, workflow
    from .base import Contact, Organisation
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class PersonsAppTestCase(CremeTestCase, BrickTestCaseMixin):
    def test_populate(self):
        self.get_relationtype_or_fail(constants.REL_SUB_EMPLOYED_BY,       [Contact],               [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_CUSTOMER_SUPPLIER, [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_MANAGES,           [Contact],               [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_PROSPECT,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_SUSPECT,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_PARTNER,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_INACTIVE,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_SUBSIDIARY,        [Organisation],          [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_COMPETITOR,        [Contact, Organisation], [Contact, Organisation])

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Contact)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Organisation)).exists())

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.FILTER_MANAGED_ORGA)
        self.assertFalse(efilter.is_custom)
        self.assertEqual(Organisation, efilter.entity_type.model_class())
        self.assertQuerysetSQLEqual(Organisation.objects.filter(is_managed=True),
                                    efilter.filter(Organisation.objects.all())
                                   )

    # def test_portal(self):
    #     self.login()
    #     self.assertGET200(reverse('persons__portal'))

    def test_config_portal(self):
        self.login()
        response = self.assertGET200(reverse('creme_config__portal'))
        self.get_brick_node(self.get_html_tree(response.content), bricks.ManagedOrganisationsBrick.id_)

    def test_transform_target_into_prospect01(self):
        user = self.login()
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source')
        target = create_orga(name='Target')

        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_PROSPECT, source)

        # Do not create duplicate
        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_PROSPECT, source)

    # def test_transform_target_into_prospect02(self):
    #     "Crash with existing duplicated Relation"
    #     user = self.login()
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source')
    #     target = create_orga(name='Target')
    #
    #     for i_ in range(2):
    #         Relation.objects.create(subject_entity=target,
    #                                 type_id=constants.REL_SUB_PROSPECT,
    #                                 object_entity=source,
    #                                 user=user,
    #                                )
    #
    #     with self.assertNoException():
    #         workflow.transform_target_into_prospect(source, target, user)
    #
    #     self.assertRelationCount(2, target, constants.REL_SUB_PROSPECT, source)

    def test_transform_target_into_customer01(self):
        user = self.login()
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source')
        target = create_orga(name='Target')

        workflow.transform_target_into_customer(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_CUSTOMER_SUPPLIER, source)

        # Do not create duplicate
        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_CUSTOMER_SUPPLIER, source)

    # def test_transform_target_into_customer02(self):
    #     "Crash with existing duplicated Relation"
    #     user = self.login()
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source')
    #     target = create_orga(name='Target')
    #
    #     for i_ in range(2):
    #         Relation.objects.create(subject_entity=target,
    #                                 type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
    #                                 object_entity=source,
    #                                 user=user,
    #                                )
    #
    #     with self.assertNoException():
    #         workflow.transform_target_into_customer(source, target, user)
    #
    #     self.assertRelationCount(2, target, constants.REL_SUB_CUSTOMER_SUPPLIER, source)
