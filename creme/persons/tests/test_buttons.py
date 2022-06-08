from django import template
from django.utils.translation import gettext_lazy as _
from parameterized import parameterized

from creme.creme_core.models import Relation
from creme.creme_core.models.relation import RelationType
from creme.creme_core.templatetags.creme_core_tags import jsondata
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import buttons

from .base import Organisation, skipIfCustomOrganisation


@skipIfCustomOrganisation
class ButtonsTestCase(CremeTestCase):
    @parameterized.expand([
        buttons.BecomeCustomerButton,
        buttons.BecomeProspectButton,
        buttons.BecomeSuspectButton,
        buttons.BecomeInactiveButton,
        buttons.BecomeSupplierButton,
    ])
    def test_become(self, button_class):
        user = self.get_root_user()

        managed_orga = self.get_alone_element(
            Organisation.objects.filter_managed_by_creme().all()
        )
        orga = Organisation.objects.create(user=user, name='Acme')

        button = button_class()
        self.assertTrue(button.ok_4_display(orga))

        # Already linked
        Relation.objects.create(
            user=user,
            subject_entity=orga,
            type_id=button.relation_type_deps[0],
            object_entity=managed_orga,
        )
        self.assertFalse(button.ok_4_display(orga))

    def test_become_can_display__link_organisation_to_itself(self):
        "Cannot link a managed organisation with itself."
        managed_orga = self.get_alone_element(
            Organisation.objects.filter_managed_by_creme().all()
        )

        button = buttons.BecomeCustomerButton()
        self.assertFalse(button.ok_4_display(managed_orga))

    @parameterized.expand(
        [
            (False, False, _("You are not allowed to link this entity")),
            (False, True, _("You are not allowed to link this entity")),
            (
                True,
                False,
                _("The relationship type «{predicate}» is disabled").format(
                    predicate="Is fake"
                ),
            ),
            (True, True, buttons.BecomeCustomerButton.description),
        ]
    )
    def test_become_description(self, can_link, rtype_enabled, expected):
        user = self.create_user()

        managed_orga = Organisation.objects.filter_managed_by_creme().first()
        button = buttons.BecomeCustomerButton()
        rtype = RelationType(enabled=rtype_enabled, predicate="Is fake")

        context = button.get_button_context(
            {
                "object": managed_orga,
                "user": user,
                "rtype": rtype,
                "can_link": can_link,
            }
        )

        self.assertEqual(context["description"], expected)

    def test_become_action_data(self):
        user = self.create_user()

        managed_orga = Organisation.objects.filter_managed_by_creme().first()
        orga = Organisation.objects.create(user=user, name="Acme")

        button = buttons.BecomeCustomerButton()
        rtype = RelationType.objects.get(id=button.relation_type_id)

        context = button.get_button_context(
            {
                "object": orga,
                "user": user,
            }
        )

        self.assertEqual(
            context["action_data"],
            {
                "organisations": [
                    {"value": managed_orga.pk, "label": str(managed_orga)}
                ],
                "subject_id": orga.id,
                "rtype_id": button.relation_type_id,
            },
        )

        self.assertEqual(context["rtype"], rtype)
        self.assertEqual(context["is_enabled"], False)

    @parameterized.expand(
        [
            ({"can_link": False}, False),
            ({"can_link": True, "rtype": RelationType(enabled=False)}, False),
            ({"can_link": True, "rtype": RelationType(enabled=True)}, True),
        ]
    )
    def test_become_is_enabled(self, context, expected):
        user = self.create_user()
        orga = Organisation.objects.create(user=user, name="Acme")
        button = buttons.BecomeCustomerButton()

        context = button.get_button_context(
            {
                **context,
                "object": orga,
                "user": user,
            }
        )

        self.assertEqual(context["is_enabled"], expected)

    def test_become_render(self):
        user = self.create_user()

        managed_orga = Organisation.objects.filter_managed_by_creme().first()
        orga = Organisation.objects.create(user=user, name="Acme")

        button = buttons.BecomeCustomerButton()

        output = button.render(
            {
                "object": orga,
                "user": user,
            }
        )

        icon_html = template.Template(
            r"{% load creme_widgets %}"
            rf"{{% widget_icon name='relations' size='instance-button' label='{button.icon_title}' %}}"  # noqa
        ).render(template.Context({"THEME_NAME": "icecream"}))

        json_data_html = jsondata(
            {
                "data": {
                    "organisations": [
                        {"value": managed_orga.pk, "label": str(managed_orga)}
                    ],
                    "subject_id": orga.id,
                    "rtype_id": button.relation_type_id,
                },
                "options": {},
            }
        )

        self.assertHTMLEqual(
            output,
            (
                f'<a data-action="{button.action}" class="menu_button menu-button-icon" title="{button.description}" href="">'  # noqa
                f"{icon_html}{button.verbose_name}{json_data_html}"
                "</a>"
            ),
        )
