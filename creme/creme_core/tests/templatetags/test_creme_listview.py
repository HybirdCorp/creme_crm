# -*- coding: utf-8 -*-

try:
    from django.core.paginator import Paginator
    from django.template import Template, Context
    from django.utils.translation import gettext as _

    from ..base import CremeTestCase

    from creme.creme_core.core.paginator import FlowPaginator
    from creme.creme_core.models import FakeOrganisation
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# TODO: write complete tests for EntityCells

# TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
    def test_listview_pager_slow(self):
        user = self.login()

        for i in range(1, 20):
            FakeOrganisation.objects.create(user=user, name='A{}'.format(i))

        paginator = Paginator(FakeOrganisation.objects.all(), 5)

        with self.assertNoException():
            template = Template(r'{% load creme_listview %}'
                                r'{% listview_pager page %}'
                               )
            rendered = template.render(Context({'page': paginator.page(1)}))

        self.assertInHTML(
            '<a class="pager-link is-disabled pager-link-previous" href="" title="" >{label}</a>'.format(
                label=_('Previous page'),
            ),
            rendered
        )

        self.assertInHTML(
            '<span class="pager-link is-disabled pager-link-current">1</span>',
            rendered
        )

        self.assertInHTML(
            '<a class="pager-link pager-link-next" href="" title="{help}" data-page="2">{label}</a>'.format(
                help=_('To page {}').format(2),
                label=_('Next page'),
            ),
            rendered
        )

    def test_listview_pager_fast(self):
        user = self.login()

        for i in range(1, 20):
            FakeOrganisation.objects.create(user=user, name='A{}'.format(i))

        paginator = FlowPaginator(queryset=FakeOrganisation.objects.all(),
                                  key='name', per_page=5, count=20,
                                 )

        with self.assertNoException():
            template = Template(r'{% load creme_listview %}'
                                r'{% listview_pager page %}'
                               )
            rendered = template.render(Context({
                'page': paginator.page({
                    'type': 'first',
                })
            }))

        self.assertInHTML(
            '<a class="pager-link is-disabled pager-link-first" href="" title="{label}" >{label}</a>'.format(
                label=_('First page'),
            ),
            rendered
        )

        self.assertInHTML(
            '<a class="pager-link is-disabled pager-link-previous" href="" title="{label}" >{label}</a>'.format(
                label=_('Previous page')
            ),
            rendered
        )

