from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.template import Context, Template
from django.utils.translation import gettext as _

from creme.creme_core.core.paginator import FlowPaginator
from creme.creme_core.models import (
    EntityFilter,
    FakeMailingList,
    FakeOrganisation,
    HeaderFilter,
)
from creme.creme_core.models.entity_filter import EntityFilterList
from creme.creme_core.models.header_filter import HeaderFilterList
from creme.creme_core.templatetags.creme_listview import (
    listview_entity_filters,
    listview_header_filters,
)

from ..base import CremeTestCase


# TODO: write complete tests for EntityCells
# TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
    def test_listview_pager_slow(self):
        user = self.get_root_user()

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
        user = self.get_root_user()

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
        user = self.get_root_user()

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
        self.assertEqual(ctxt.get('selected'), hf)

        # self.assertIs(ctxt.get('can_edit'),   True)
        self.assertIs(True, ctxt.get('edition_allowed'))
        self.assertEqual('OK', ctxt.get('edition_error'))

        # self.assertIs(ctxt.get('can_delete'), False)
        self.assertIs(False, ctxt.get('deletion_allowed'))
        self.assertEqual(_("This view can't be deleted"), ctxt.get('deletion_error'))

        self.assertEqual([hf], ctxt.get('global_header_filters'))
        self.assertFalse([*ctxt.get('my_header_filters')])
        self.assertFalse([*ctxt.get('other_header_filters')])

    def test_listview_header_filters02(self):
        user = self.get_root_user()
        other_user = self.create_user()

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

        # self.assertIs(ctxt.get('can_edit'),   True)
        self.assertIs(True, ctxt.get('edition_allowed'))
        self.assertEqual('OK', ctxt.get('edition_error'))

        # self.assertIs(ctxt.get('can_delete'), True)
        self.assertIs(True, ctxt.get('deletion_allowed'))
        self.assertEqual('OK', ctxt.get('deletion_error'))

        self.assertEqual(ctxt.get('selected'), hf02)
        self.assertEqual([hf01],                 ctxt.get('global_header_filters'))
        self.assertEqual([hf02],                 ctxt.get('my_header_filters'))
        self.assertEqual([(other_user, [hf03])], ctxt.get('other_header_filters'))

    def test_listview_header_filters__no_edition(self):
        user = self.create_user(role=self.get_regular_role())
        hf = HeaderFilter.objects.create_if_needed(
            pk='test_hf-ml01', name='View', model=FakeMailingList, is_custom=True,
        )

        hfilters = HeaderFilterList(
            content_type=ContentType.objects.get_for_model(FakeMailingList),
            user=user,
        )
        hfilters.select_by_id(hf.id)

        ctxt = listview_header_filters(
            model=FakeMailingList,
            user=user,
            hfilters=hfilters,
            show_buttons=True,
        )
        self.assertIs(False, ctxt.get('edition_allowed'))
        self.assertEqual(
            _('Only superusers can edit/delete this view (no owner)'),
            ctxt.get('edition_error'),
        )

        self.assertIs(False, ctxt.get('deletion_allowed'))
        self.assertEqual(
            _('Only superusers can edit/delete this view (no owner)'),
            ctxt.get('deletion_error'),
        )

    def test_listview_entity_filters(self):
        user = self.get_root_user()
        other_user1 = self.create_user(index=0)
        other_user2 = self.create_user(index=1)

        ctype = ContentType.objects.get_for_model(FakeMailingList)
        self.assertFalse(EntityFilter.objects.filter(entity_type=ctype).first())

        create_efilter = partial(EntityFilter.objects.create, entity_type=ctype)
        g_filter1 = create_efilter(id='creme_core-ml1', name='Second ML filter')
        g_filter2 = create_efilter(id='creme_core-ml2', name='First ML filter')

        user_filter = create_efilter(id='creme_core-ml3', name='My ML filter', user=user)

        other_filter1 = create_efilter(id='creme_core-ml4', name='ML filter #1', user=other_user1)
        other_filter2 = create_efilter(id='creme_core-ml5', name='ML filter #2', user=other_user2)

        efilters = EntityFilterList(content_type=ctype, user=user)
        # efilters.select_by_id(efilter1.id)
        efilters.select_by_id(g_filter1.id)

        ctxt1 = listview_entity_filters(
            model=FakeMailingList,
            user=user,
            efilters=efilters,
            show_buttons=True,
        )
        self.assertIsInstance(ctxt1, dict)
        self.assertIs(ctxt1.get('model'), FakeMailingList)
        # self.assertIs(ctxt1.get('entity_filters'), efilters)
        self.assertListEqual([g_filter2, g_filter1], ctxt1.get('global_efilters'))
        self.assertListEqual([user_filter],          ctxt1.get('my_efilters'))
        self.assertListEqual(
            [
                (other_user1, [other_filter1]),
                (other_user2, [other_filter2]),
            ],
            ctxt1.get('other_efilters'),
        )
        self.assertIs(ctxt1.get('show_buttons'), True)
        # self.assertEqual(ctxt1.get('efilter_id'), efilter1.id)
        self.assertEqual(ctxt1.get('selected'), g_filter1)

        self.assertIs(True, ctxt1.get('edition_allowed'))
        self.assertEqual('OK', ctxt1.get('edition_error'))

        self.assertIs(True, ctxt1.get('deletion_allowed'))
        self.assertEqual('OK', ctxt1.get('deletion_error'))

        # ---
        ctxt2 = listview_entity_filters(
            model=FakeMailingList,
            user=user,
            efilters=efilters,
            show_buttons=False,
        )
        self.assertIs(ctxt2.get('show_buttons'), False)

    def test_listview_entity_filters__no_edition(self):
        user = self.create_user(role=self.get_regular_role())

        efilter = EntityFilter.objects.create(
            id='creme_core-ml_filter01', name='ML filter #1', entity_type=FakeMailingList,
            # user=None
        )

        efilters = EntityFilterList(
            content_type=ContentType.objects.get_for_model(FakeMailingList), user=user,
        )
        efilters.select_by_id(efilter.id)

        ctxt = listview_entity_filters(
            model=FakeMailingList,
            user=user,
            efilters=efilters,
            show_buttons=True,
        )
        self.assertIs(False, ctxt.get('edition_allowed'))
        self.assertEqual(
            _('Only superusers can edit/delete this filter (no owner)'),
            ctxt.get('edition_error'),
        )

        self.assertIs(False, ctxt.get('deletion_allowed'))
        self.assertEqual(
            _('Only superusers can edit/delete this filter (no owner)'),
            ctxt.get('deletion_error'),
        )
