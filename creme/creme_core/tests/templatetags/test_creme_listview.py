# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.template import Context, Template
from django.utils.translation import gettext as _

from creme.creme_core.core.paginator import FlowPaginator
from creme.creme_core.models import (
    FakeMailingList,
    FakeOrganisation,
    HeaderFilter,
)
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.templatetags.creme_listview import (
    listview_header_filters,
)

from ..base import CremeTestCase


# TODO: write complete tests for EntityCells
# TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
    def test_listview_pager_slow(self):
        user = self.login()

        for i in range(1, 20):
            FakeOrganisation.objects.create(user=user, name=f'A{i}')

        paginator = Paginator(FakeOrganisation.objects.all(), 5)

        with self.assertNoException():
            template = Template(
                r'{% load creme_listview %}'
                r'{% listview_pager page %}'
            )
            rendered = template.render(Context({'page': paginator.page(1)}))

        self.assertInHTML(
            f'<a class="pager-link is-disabled pager-link-previous" href="" '
            f'title="" >{_("Previous page")}</a>',
            rendered,
        )

        self.assertInHTML(
            '<span class="pager-link is-disabled pager-link-current">1</span>',
            rendered,
        )

        self.assertInHTML(
            '<a class="pager-link pager-link-next" href="" title="{help}" '
            'data-page="2">{label}</a>'.format(
                help=_('To page {}').format(2),
                label=_('Next page'),
            ),
            rendered,
        )

    def test_listview_pager_fast(self):
        user = self.login()

        for i in range(1, 20):
            FakeOrganisation.objects.create(user=user, name=f'A{i}')

        paginator = FlowPaginator(
            queryset=FakeOrganisation.objects.all(),
            key='name', per_page=5, count=20,
        )

        with self.assertNoException():
            template = Template(
                r'{% load creme_listview %}'
                r'{% listview_pager page %}'
            )
            rendered = template.render(Context({
                'page': paginator.page({
                    'type': 'first',
                })
            }))

        self.assertInHTML(
            '<a class="pager-link is-disabled pager-link-first" href="" '
            'title="{label}" >{label}</a>'.format(
                label=_('First page'),
            ),
            rendered
        )

        self.assertInHTML(
            '<a class="pager-link is-disabled pager-link-previous" href="" '
            'title="{label}" >{label}</a>'.format(
                label=_('Previous page'),
            ),
            rendered,
        )

    def test_listview_header_filters01(self):
        user = self.login()

        ctype = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ctype).first())

        hf = HeaderFilter.objects.create_if_needed(
            pk='test_hf-ml01', name='View', model=FakeMailingList,
        )

        hfilters = HeaderFilterList(
            content_type=ctype,
            user=user,
        )
        hfilters.select_by_id(hf.id)

        ctxt = listview_header_filters(
            model=FakeMailingList,
            user=user,
            hfilters=hfilters,
            show_buttons=True,
        )
        self.assertIsInstance(ctxt, dict)
        self.assertIs(ctxt.get('model'), FakeMailingList)
        self.assertIs(ctxt.get('show_buttons'), True)

        self.assertIs(ctxt.get('can_edit'),   True)
        self.assertIs(ctxt.get('can_delete'), False)
        self.assertEqual(ctxt.get('selected'), hf)

        self.assertEqual([hf], ctxt.get('global_header_filters'))
        self.assertFalse([*ctxt.get('my_header_filters')])
        self.assertFalse([*ctxt.get('other_header_filters')])

    def test_listview_header_filters02(self):
        user = self.login()
        other_user = self.other_user

        ctype = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ctype).first())

        create_hf = partial(HeaderFilter.objects.create_if_needed, model=FakeMailingList)
        hf01 = create_hf(pk='test_hf-ml01', name='View')
        hf02 = create_hf(pk='test_hf-ml02', name='My view',    user=user,       is_custom=True)
        hf03 = create_hf(pk='test_hf-ml03', name='Other view', user=other_user, is_custom=True)

        hfilters = HeaderFilterList(
            content_type=ctype,
            user=user,
        )
        hfilters.select_by_id(hf02.id)

        ctxt = listview_header_filters(
            model=FakeMailingList,
            user=user,
            hfilters=hfilters,
            show_buttons=False,
        )
        self.assertIs(ctxt.get('show_buttons'), False)

        self.assertIs(ctxt.get('can_edit'),   True)
        self.assertIs(ctxt.get('can_delete'), True)

        self.assertEqual(ctxt.get('selected'), hf02)
        self.assertEqual([hf01],                 ctxt.get('global_header_filters'))
        self.assertEqual([hf02],                 ctxt.get('my_header_filters'))
        self.assertEqual([(other_user, [hf03])], ctxt.get('other_header_filters'))
