from django.contrib.contenttypes.models import ContentType
from django.template import loader
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_config import bricks as config_bricks
from creme.creme_config.gui.admin_history import (
    AdminHistoryRegistry,
    CremeUserHistoryExplainer,
    EmptyExplainer,
    PropertyTypeHistoryExplainer,
    admin_history_registry,
)
from creme.creme_config.models import AdminHistoryLine
from creme.creme_core.global_info import set_global_info
from creme.creme_core.models import CremePropertyType, CremeUser
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class AdminHistoryLineTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login_as_root()
        response = self.assertGET200(reverse('creme_config__admin_history'))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=config_bricks.AdminHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=AdminHistoryLine.objects.count(),
            title='{count} History event',
            plural_title='{count} History events',
        )

        # TODO: reloading (register etc...)

    def test_user_creation(self):
        user = self.login_as_root_and_get()
        set_global_info(user=user)

        old_count = AdminHistoryLine.objects.count()
        self.create_user()
        self.assertEqual(old_count + 1, AdminHistoryLine.objects.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremeUser,          line.content_type.model_class())
        self.assertEqual(user.username,      line.username)
        self.assertEqual(line.Type.CREATION, line.type)
        self.assertDatetimesAlmostEqual(now(), line.date)
        # TODO: fields values?
        # TODO: by_wf_engine?

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=config_bricks.UserAdminHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=old_count + 1,
            title='{count} History event',
            plural_title='{count} History events',
        )
        # TODO: test content (only user)

    def test_user_edition(self):
        self.login_as_root()
        # set_global_info(user=user)

        user = self.create_user()
        old_count = AdminHistoryLine.objects.count()

        user.email = f'{user.username}@acme.fr'
        user.save()
        self.assertEqual(old_count + 1, AdminHistoryLine.objects.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremeUser, line.content_type.model_class())
        self.assertEqual('',                line.username)
        self.assertEqual(line.Type.EDITION, line.type)

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=config_bricks.UserAdminHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=AdminHistoryLine.objects.filter(
                content_type=ContentType.objects.get_for_model(CremeUser),
            ).count(),
            title='{count} History event',
            plural_title='{count} History events',
        )

    def test_user_deletion(self):
        root = self.login_as_root_and_get()

        user = self.create_user(role=self.get_regular_role())
        old_count = AdminHistoryLine.objects.count()

        self.assertNoFormError(self.client.post(
            reverse('creme_config__delete_user', args=(user.id,)),
            {'to_user': root.id},
        ))
        self.assertDoesNotExist(user)

        self.assertEqual(old_count + 1, AdminHistoryLine.objects.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremeUser, line.content_type.model_class())
        self.assertEqual(root.username,      line.username)
        self.assertEqual(line.Type.DELETION, line.type)
        # TODO: user_id/uuid ??

        # TODO: test content?
        # response = self.assertGET200(reverse('creme_config__users'))
        # brick_node = self.get_brick_node(
        #     self.get_html_tree(response.content),
        #     brick=config_bricks.UserAdminHistoryBrick,
        # )
        # self.assertBrickTitleEqual(
        #     brick_node,
        #     count=AdminHistoryLine.objects.filter(
        #         content_type=ContentType.objects.get_for_model(CremeUser),
        #     ).count(),
        #     title='{count} History event',
        #     plural_title='{count} History events',
        # )

    def test_property_creation(self):
        user = self.login_as_super()
        set_global_info(user=user)

        qs = AdminHistoryLine.objects.filter(
            content_type=ContentType.objects.get_for_model(CremePropertyType),
        )
        old_count = qs.count()
        self.assertNotEqual(AdminHistoryLine.objects.count(), old_count)

        CremePropertyType.objects.create(text='New property')
        self.assertEqual(old_count + 1, qs.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremePropertyType,  line.content_type.model_class())
        self.assertEqual(user.username,      line.username)
        self.assertEqual(line.Type.CREATION, line.type)

        portal_resp = self.assertGET200(reverse('creme_config__ptypes'))
        brick_node = self.get_brick_node(
            self.get_html_tree(portal_resp.content),
            brick=config_bricks.PropertyTypeAdminHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=old_count + 1,
            title='{count} History event',
            plural_title='{count} History events',
        )

    def test_property_deletion(self):
        user = self.login_as_super()
        set_global_info(user=user)

        qs = AdminHistoryLine.objects.filter(
            content_type=ContentType.objects.get_for_model(CremePropertyType),
        )
        ptype = CremePropertyType.objects.create(text='Type to be deleted')
        old_count = qs.count()

        ptype.delete()
        self.assertEqual(old_count + 1, qs.count())

        line = AdminHistoryLine.objects.order_by('-id')[0]
        self.assertEqual(CremePropertyType,  line.content_type.model_class())
        self.assertEqual(user.username,      line.username)
        self.assertEqual(line.Type.DELETION, line.type)


class ExplainersTestCase(CremeTestCase):
    def _render(self, expl_context):
        return loader.render_to_string(
            template_name=expl_context['template_name'],
            context=expl_context,
            # request,
            # using=using
        )

    def test_empty(self):
        user = self.get_root_user()
        line = AdminHistoryLine(content_type=CremeUser)

        explainer = EmptyExplainer(hline=line, user=user)
        self.assertEqual(line, explainer.hline)
        self.assertEqual(user, explainer.user)

        template_name = 'creme_config/history/empty.html'
        self.assertEqual(template_name, explainer.template_name)

        ctxt = explainer.get_context()
        self.assertDictEqual(
            {'template_name': template_name, 'hline': line, 'user': user},
            ctxt,
        )
        self.assertHTMLEqual(
            '<span class="admin-history-empty">?</span>', self._render(ctxt),
        )

    def test_user__creation(self):
        user = self.get_root_user()
        line = AdminHistoryLine(content_type=CremeUser)

        explainer = CremeUserHistoryExplainer(hline=line, user=user)
        self.assertEqual(line, explainer.hline)
        self.assertEqual(user, explainer.user)

        template_name = 'creme_config/history/user.html'
        self.assertEqual(template_name, explainer.template_name)

        ctxt = {'template_name': template_name, 'hline': line, 'user': user}
        self.assertDictEqual(ctxt, explainer.get_context())
        self.assertHTMLEqual(
            # TODO: complete (fields at creation? which fields?)
            f'<span class="admin-history-user">{_("User created")}</span>',
            self._render(ctxt),
        )


class AdminHistoryRegistryTestCase(CremeTestCase):
    def test_empty(self):
        user = self.get_root_user()
        registry = AdminHistoryRegistry()
        line = AdminHistoryLine(content_type=CremeUser)
        explainers = registry.explainers([line], user=user)
        self.assertIsList(explainers, length=1)

        explainer = explainers[0]
        self.assertIsInstance(explainer, EmptyExplainer)
        self.assertEqual(line, explainer.hline)
        self.assertEqual(user, explainer.user)

    def test_register(self):
        user = self.get_root_user()
        registry = AdminHistoryRegistry().register(
            model=CremeUser, explainer=CremeUserHistoryExplainer,
        )

        line = AdminHistoryLine(content_type=CremeUser)
        explainers = registry.explainers([line], user=user)
        self.assertIsList(explainers, length=1)

        explainer = explainers[0]
        self.assertIsInstance(explainer, CremeUserHistoryExplainer)
        self.assertEqual(line, explainer.hline)
        self.assertEqual(user, explainer.user)

    def test_global_registry(self):
        user = self.get_root_user()

        explainers = admin_history_registry.explainers(
            hlines=[
                AdminHistoryLine(content_type=CremeUser),
                AdminHistoryLine(content_type=CremePropertyType)
            ],
            user=user,
        )
        self.assertIsList(explainers, length=2)
        self.assertIsInstance(explainers[0], CremeUserHistoryExplainer)
        self.assertIsInstance(explainers[1], PropertyTypeHistoryExplainer)

    # TODO: registration error?
