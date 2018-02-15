# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.core.paginator import Paginator
    from django.core.urlresolvers import reverse
    from django.template import Template, Context
    from django.utils.translation import ugettext as _
    from django.utils.html import escape

    from ..base import CremeTestCase
    from ..fake_models import FakeOrganisation
    from creme.creme_core.core.entity_cell import EntityCellCustomField
    from creme.creme_core.core.paginator import FlowPaginator
    from creme.creme_core.forms.bulk import _CUSTOMFIELD_FORMAT
    from creme.creme_core.forms.header_filter import EntityCellRegularField
    from creme.creme_core.models import CustomField, CustomFieldEnumValue
    from creme.creme_core.utils.meta import FieldInfo
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


# TODO: write complete tests for EntityCells

# TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
    def assertFieldEditorTag(self, render, entity, field_name, block=False):
        url = reverse('creme_core__inner_edition', args=(entity.entity_type_id, entity.id, field_name))

        if block:
            expected = """<a onclick="creme.blocks.form('%s', {blockReloadUrl:""" % url
        else:
            expected = """<a onclick="creme.blocks.form('%s', {reloadOnSuccess:""" % url

        self.assertTrue(render.strip().startswith(expected),
                        "%s\n doesn't start with\n %s" % (render.strip(), expected))

    def test_get_listview_cell_cfield01(self):
        "{% get_listview_cell cell entity user %}"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        cfield = CustomField.objects.create(content_type=bebop.entity_type,
                                            field_type=CustomField.ENUM,
                                           )

        heavy_name = 'Heavy'
        create_evalue = CustomFieldEnumValue.objects.create
        heavy = create_evalue(custom_field=cfield, value=heavy_name)
        create_evalue(custom_field=cfield, value='Light')

        klass = cfield.get_value_class()
        klass(custom_field=cfield, entity=bebop).set_value_n_save(heavy.id)

        cell = EntityCellCustomField(cfield)

        def print_cell(entity):
            with self.assertNoException():
                template = Template(r"{% load creme_listview %}{% get_listview_cell cell entity user %}")
                return template.render(Context({'cell': cell, 'entity': entity, 'user': user}))

        render = print_cell(bebop)
        self.assertEqual(heavy_name, render)

        render = print_cell(swordfish)
        self.assertEqual('', render)

    def test_get_field_editor_cell_regular(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Amestris')
        orga_field_name = orga.entity_type.model_class()._meta.get_field('name')

        cell = EntityCellRegularField(FakeOrganisation, 'name', FieldInfo(FakeOrganisation, 'name'))

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on entity_cell cell for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': user, 'cell': cell}))

        self.assertFieldEditorTag(render, orga, orga_field_name.name)

    def test_get_field_editor_cell_custom(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Amestris')
        custom_field_orga = CustomField.objects.create(name='custom 1',
                                                       content_type=orga.entity_type,
                                                       field_type=CustomField.STR,
                                                      )

        cell = EntityCellCustomField(custom_field_orga)

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on entity_cell cell for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': user, 'cell': cell}))

        self.assertFieldEditorTag(render, orga, _CUSTOMFIELD_FORMAT % custom_field_orga.id)

    def test_listview_pager_slow(self):
        user = self.login()

        for i in xrange(1, 20):
            FakeOrganisation.objects.create(user=user, name='A%d' % i)

        paginator = Paginator(FakeOrganisation.objects.all(), 5)

        with self.assertNoException():
            template = Template(r"{% load creme_listview %}"
                                r"{% listview_pager page %}"
                               )
            rendered = template.render(Context({'page': paginator.page(1)}))

        self.assertInHTML(u'<a class="pager-link is-disabled pager-link-previous" href="" title="" >{label}</a>'.format(
                              label=_(u'Previous page')
                          ), rendered)

        self.assertInHTML(u'<span class="pager-link is-disabled pager-link-current">1</span>',
                          rendered)

        self.assertInHTML(u'<a class="pager-link pager-link-next" href="" title="{help}" data-page="2">{label}</a>'.format(
                              help=_(u'To page %s') % 2,
                              label=_(u'Next page')
                          ), rendered)

    def test_listview_pager_fast(self):
        user = self.login()

        for i in xrange(1, 20):
            FakeOrganisation.objects.create(user=user, name='A%d' % i)

        paginator = FlowPaginator(queryset=FakeOrganisation.objects.all(),
                                  key='name', per_page=5, count=20)

        with self.assertNoException():
            template = Template(r"{% load creme_listview %}"
                                r"{% listview_pager page %}"
                               )
            rendered = template.render(Context({
                'page': paginator.page({
                    'type': 'first'
                })
            }))

        self.assertInHTML(u'<a class="pager-link is-disabled pager-link-first" href="" title="{label}" >{label}</a>'.format(
                              label=_(u'First page')
                          ), rendered)

        self.assertInHTML(u'<a class="pager-link is-disabled pager-link-previous" href="" title="{label}" >{label}</a>'.format(
                              label=_(u'Previous page')
                          ), rendered)

