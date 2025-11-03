from django.template import Context, Template
from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.models import EntityFilter, FakeContact

from ..base import CremeTestCase


class EntityFilterTagsTestCase(CremeTestCase):
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
                'You are not allowed to view this filter '
                '(you are not the owner)'
            )),
            render2,
        )
