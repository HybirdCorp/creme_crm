# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.template import Template, Context

    from ..base import CremeTestCase
    from creme.creme_core.core.entity_cell import EntityCellCustomField
    from creme.creme_core.models import CustomField, CustomFieldEnumValue

    from creme.persons.models import Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


#TODO: write complete tests for EntityCells

#TODO: to be completed
class CremeListViewTagsTestCase(CremeTestCase):
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
