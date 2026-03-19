from django.template import Context, Template
from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.models import EntityFilter, FakeContact

from ..base import CremeTestCase


class EntityFilterTagsTestCase(CremeTestCase):
    def test_efilter_edition_forbidden(self):
        user = self.create_user(role=self.create_role(allowed_apps=['creme_core']))

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_edition_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(user=user, entity_type=FakeContact),
            }))
        self.assertEqual('', render1)

        # ---
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_edition_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(entity_type=FakeContact),
            }))
        self.assertEqual(
            escape(_('Only superusers can edit this filter (no owner)')),
            render2,
        )

    def test_efilter_deletion_forbidden(self):
        user = self.get_root_user()

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_deletion_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(user=user, entity_type=FakeContact),
            }))
        self.assertEqual('', render1)

        # ---
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_deletion_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(entity_type=FakeContact, is_custom=False),
            }))
        self.assertEqual(
            escape(_("This filter can't be deleted (system filter)")),
            render2,
        )

    def test_efilter_view_forbidden(self):
        user = self.get_root_user()

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_view_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(user=user, entity_type=FakeContact),
            }))
        self.assertEqual('', render1)

        # ---
        owner = self.create_user()
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_entity_filter %}{{efilter|efilter_view_forbidden:user}}'
            ).render(Context({
                'user': user,
                'efilter': EntityFilter(
                    user=owner, entity_type=FakeContact, is_private=True,
                ),
            }))
        self.assertEqual(
            escape(_(
                # 'You are not allowed to view/edit/delete this filter '
                'You are not the owner of this private filter'
            )),
            render2,
        )
