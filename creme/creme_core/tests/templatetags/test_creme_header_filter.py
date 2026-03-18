from django.template import Context, Template
from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.models import FakeContact, HeaderFilter

from ..base import CremeTestCase


class HeaderFilterTagsTestCase(CremeTestCase):
    def test_hfilter_edition_forbidden(self):
        root = self.get_root_user()

        with self.assertNoException():
            render1 = Template(
                '{% load creme_header_filter %}'
                '{{hfilter|hfilter_edition_forbidden:user|default:"OK"}}'
            ).render(Context({
                'hfilter': HeaderFilter(entity_type=FakeContact, is_custom=False),
                'user': root,
            }))

        self.assertEqual('OK', render1.strip())

        # ---
        other = self.create_user()

        with self.assertNoException():
            render2 = Template(
                '{% load creme_header_filter %}'
                '{{hfilter|hfilter_edition_forbidden:user}}'
            ).render(Context({
                'hfilter': HeaderFilter(entity_type=FakeContact, user=other, is_private=True),
                'user': root,
            }))

        self.assertEqual(
            escape(_('You are not the owner of this private view')),
            render2.strip(),
        )

    def test_hfilter_deletion_forbidden(self):
        root = self.get_root_user()

        with self.assertNoException():
            render1 = Template(
                '{% load creme_header_filter %}'
                '{{hfilter|hfilter_deletion_forbidden:user|default:"OK"}}'
            ).render(Context({
                'hfilter': HeaderFilter(user=root, entity_type=FakeContact),
                'user': root,
            }))
        self.assertEqual('OK', render1.strip())

        # ---
        with self.assertNoException():
            render2 = Template(
                '{% load creme_header_filter %}'
                '{{hfilter|hfilter_deletion_forbidden:user}}'
            ).render(Context({
                'hfilter': HeaderFilter(entity_type=FakeContact, is_custom=False),
                'user': root,
            }))

        self.assertEqual(escape(_('This is a system view')), render2.strip())
