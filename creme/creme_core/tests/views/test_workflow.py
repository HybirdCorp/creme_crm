from django.urls import reverse

from creme.creme_core import workflows
from creme.creme_core.models import CremePropertyType, FakeContact, Workflow
from creme.creme_core.views import workflow as workflow_views

from ..base import CremeTestCase
from .base import BrickTestCaseMixin, ButtonTestCaseMixin


class WorkflowViewsTestCase(BrickTestCaseMixin, ButtonTestCaseMixin, CremeTestCase):
    def test_detailview(self):
        self.login_as_standard(admin_4_apps=['creme_core'])

        ptype = CremePropertyType.objects.create(text='is a fighter', is_custom=True)

        wf = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=workflows.PropertyAddingTrigger(
                entity_model=FakeContact, ptype=ptype,
            ),
            # conditions=...
            # actions=[],
        )
        response = self.assertGET200(wf.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/detail/workflow.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/workflow/hat-bar.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/workflow/info.html')
        # TODO?
        # self.assertEqual(
        #     reverse('creme_core__reload_workflow_bricks', args=(workflow.id,)),
        #     response.context.get('bricks_reload_url'),
        # )

        with self.assertNoException():
            ctxt_wf = response.context['object']
        self.assertEqual(wf, ctxt_wf)

        tree = self.get_html_tree(response.content)
        config_button_node = self.get_alone_element(
            self.iter_button_nodes(self.get_global_buttons_node(tree))
        )
        self.assertEqual('a', config_button_node.name)
        self.assertEqual(
            reverse('creme_config__workflows'), config_button_node.attrs.get('href'),
        )

        # TODO: complete tests of bricks
        self.get_brick_node(tree, workflow_views.WorkflowBarHatBrick)
        self.get_brick_node(tree, workflow_views.WorkflowInfoBrick)

    def test_detailview__forbidden(self):
        self.login_as_standard()  # admin_4_apps=['creme_core']

        ptype = CremePropertyType.objects.create(text='is a fighter', is_custom=True)

        wf = Workflow.objects.create(
            title='Flow #1',
            content_type=FakeContact,
            trigger=workflows.PropertyAddingTrigger(
                entity_model=FakeContact, ptype=ptype,
            ),
            # conditions=...
            # actions=[],
        )
        self.assertGET403(wf.get_absolute_url())
