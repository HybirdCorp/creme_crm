# -*- coding: utf-8 -*-

from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import FakeContact, FakeOrganisation, WorkflowRule
from creme.creme_core.tests.base import CremeTestCase


class WorkflowEngineTestCase(CremeTestCase):
    # ADD_URL = reverse('creme_config__create_workflow_rule')

    # @staticmethod
    # def _build_edit_url(rtype):
    #     return reverse('creme_config__edit_rtype', args=(rtype.id,))

    def test_portal(self):
        self.login()

        response = self.assertGET200(reverse('creme_config__workflow_engine'))
        self.assertTemplateUsed(response, 'creme_config/portals/workflow-engine.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        # TODO
        # brick_node = self.get_brick_node(
        #     self.get_html_tree(response.content),
        #     bricks.CustomFieldsBrick.id_,
        # )
        # self.assertEqual(
        #     _('{count} Configured types of resource').format(count=2),
        #     self.get_brick_title(brick_node),
        # )
        # self.assertSetEqual(
        #     {cfield1.name, cfield2.name, cfield3.name},
        #     {
        #         n.text
        #         for n in brick_node.findall('.//td[@class="cfields-config-name"]')
        #     },
        # )

    def test_add_ct01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))
        url = reverse('creme_config__create_first_ctype_workflow_rule')

        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)
        ct_orga = get_ct(FakeOrganisation)

        WorkflowRule.objects.create(
            content_type=ct_orga,
            # name='Programming languages',
            # field_type=CustomField.ENUM,
        )

        # Should be ignored when hiding used ContentTypes (deleted)
        # WorkflowRule.objects.create(
        #     content_type=ct_doc,
        #     # name='Programming languages',
        #     # field_type=CustomField.ENUM,
        #     # is_deleted=True,
        # )

        # Step 1
        response1 = self.assertGET200(url)
        context1 = response1.context
        self.assertEqual(
            pgettext('creme_core-workflow_engine', 'Create a rule'),
            context1.get('title'),
        )
        self.assertEqual(_('Next step'), context1.get('submit_label'))

        with self.assertNoException():
            ctypes = context1['form'].fields['content_type'].ctypes

        self.assertIn(ct, ctypes)
        self.assertNotIn(ct_orga, ctypes)

        step_key = 'first_c_type_workflow_rule_creation_wizard-current_step'
        response2 = self.client.post(
            url,
            data={
                step_key: '0',
                '0-content_type': ct.id,
            },
        )
        self.assertNoFormError(response2)

        # Step 2
        # with self.assertNoException():
        #     adm_app_labels = response2.context['form'].fields['admin_4_apps'].choices

        context2 = response2.context
        self.assertEqual(
            pgettext('creme_config-workflow_engine', 'Save the rule'),
            context2.get('submit_label'),
        )

        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                # TODO: method
                '1-rule': json_dump({
                    # 'ctype': {'id': str(entity.entity_type_id)},
                    # 'entity': str(entity.id),
                }),
            },
        )
        self.assertNoFormError(response3)

        # count = RelationType.objects.count()
        # subject_pred = 'loves'
        # object_pred  = 'is loved by'
        # response2 = self.client.post(
        #     url,
        #     data={
        #         # 'subject_predicate': subject_pred,
        #         # 'object_predicate':  object_pred,
        #         #
        #         # 'subject_is_copiable': 'on',
        #     },
        # )
        # self.assertNoFormError(response2)

        # self.assertEqual(count + 2, RelationType.objects.count())  # 2 freshly created
        #
        # rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        # self.assertTrue(rel_type.is_custom)
        # self.assertTrue(rel_type.is_copiable)
        # self.assertFalse(rel_type.minimal_display)
        # self.assertFalse(rel_type.subject_ctypes.all())
        # self.assertFalse(rel_type.subject_properties.all())
