# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.template import Template, Context

    from ..base import CremeTestCase
    from creme.creme_core.core.entity_cell import EntityCellCustomField
    from creme.creme_core.models import CustomField, CustomFieldEnumValue
    from creme.creme_core.forms.bulk import _CUSTOMFIELD_FORMAT
    from creme.creme_core.forms.header_filter import EntityCellRegularField
    from creme.creme_core.utils.meta import FieldInfo

    from creme.persons.models import Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


#TODO: write complete tests for EntityCells

#TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
    def assertFieldEditorTag(self, render, entity, field_name, block=False):
        fmt = """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {blockReloadUrl:""" if block else \
              """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {reloadOnSuccess:"""
        expected = fmt % (entity.entity_type_id, entity.id, field_name)
        self.assertTrue(render.strip().startswith(expected),
                        "%s\n doesn't start with\n %s" % (render.strip(), expected))

    def test_get_listview_cell_cfield01(self):
        "{% get_listview_cell cell entity user %}"
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
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
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        orga_field_name = orga.entity_type.model_class()._meta.get_field('name')

        cell = EntityCellRegularField(Organisation, 'name', FieldInfo(Organisation, 'name'))

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on entity_cell cell for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': self.user, 'cell': cell}))

        self.assertFieldEditorTag(render, orga, orga_field_name.name)

    def test_get_field_editor_cell_custom(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        custom_field_orga = CustomField.objects.create(name='custom 1', content_type=orga.entity_type, field_type=CustomField.STR)

        cell = EntityCellCustomField(custom_field_orga)

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on entity_cell cell for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': self.user, 'cell': cell}))

        self.assertFieldEditorTag(render, orga, _CUSTOMFIELD_FORMAT % custom_field_orga.id)
