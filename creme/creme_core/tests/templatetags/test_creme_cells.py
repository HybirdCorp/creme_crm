# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.template import Template, Context
    from django.utils.translation import gettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.models import Currency, FakeContact

    from creme.creme_core.core.sorter import cell_sorter_registry

    from ..base import CremeTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CremeCellsTagsTestCase(CremeTestCase):
    def test_cell_4_regularfield01(self):
        "By model."
        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield model=model1 field="name" as curr_cell %}'
                r"{% cell_4_regularfield model=model2 field='first_name' as contact_cell %}"
                r'{{curr_cell.key}}#{{contact_cell.key}}'
            )
            render = template.render(Context({'model1': Currency,
                                              'model2': FakeContact,
                                             }))

        self.assertEqual('regular_field-name#regular_field-first_name',
                         render.strip()
                        )

    def test_cell_4_regularfield02(self):
        "By ContentType."
        get_ct = ContentType.objects.get_for_model

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct1 field="name" as curr_cell %}'
                r"{% cell_4_regularfield ctype=ct2 field='first_name' as contact_cell %}"
                r'{{curr_cell.key}}#{{contact_cell.key}}'
            )
            render = template.render(Context({'ct1': get_ct(Currency),
                                              'ct2': get_ct(FakeContact),
                                             }))

        self.assertEqual('regular_field-name#regular_field-first_name',
                         render.strip()
                        )

    def test_cell_4_regularfield03(self):
        "By instance."
        user = self.login()

        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield instance=helen field="first_name" as fname_cell %}'
                r'{% cell_4_regularfield instance=helen field="last_name" as lname_cell %}'
                r'{{fname_cell.key}}#{{lname_cell.key}}'
            )
            render = template.render(Context({'helen': ripley}))

        self.assertEqual('regular_field-first_name#regular_field-last_name',
                         render.strip()
                        )

    def test_cell_4_regularfield04(self):
        "No assignment."
        user = self.login()

        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield instance=helen field="first_name" %}'
            )
            render = template.render(Context({'helen': ripley}))

        self.assertEqual(_('First name'), render.strip())

    def test_cell_4_regularfield05(self):
        "Errors."
        # Invalid field
        with self.assertRaises(ValueError):
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field="invalid" as inv_cell %}'
            )
            template.render(Context({'ct': ContentType.objects.get_for_model(Currency)}))

        # Invalid content type
        with self.assertRaises(AttributeError):
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field="name" as inv_cell %}'
            )
            template.render(Context({}))

    def test_cell_render01(self):
        "Direct render ; default output."
        user = self.login()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')
        cell = EntityCellRegularField.build(model=FakeContact, name='last_name')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user %}'
            )
            render = template.render(Context({'cell': cell, 'helen': ripley, 'user': user}))

        self.assertEqual(ripley.last_name, render.strip())

    def test_cell_render02(self):
        "Direct render ; html output."
        user = self.login()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley', email='hripley@nostromo.corp')
        cell = EntityCellRegularField.build(model=FakeContact, name='email')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user output="html" %}'
            )
            render = template.render(Context({'cell': cell, 'helen': ripley, 'user': user}))

        self.assertEqual(
            '<a href="mailto:hripley@nostromo.corp">hripley@nostromo.corp</a>',
            render.strip()
        )

    def test_cell_render03(self):
        "Direct render ; CSV output."
        user = self.login()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley',
                             email='hripley@nostromo.corp',
                            )
        cell = EntityCellRegularField.build(model=FakeContact, name='email')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user output="csv" %}'
            )
            render = template.render(Context({'cell': cell, 'helen': ripley, 'user': user}))

        self.assertEqual(ripley.email, render.strip())

    def test_cell_render04(self):
        "Assignment."
        user = self.login()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley',
                             email='hripley@nostromo.corp',
                            )
        cell = EntityCellRegularField.build(model=FakeContact, name='email')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user as cell_content %}'
                r'{{cell_content}}'
            )
            render = template.render(Context({'cell': cell, 'helen': ripley, 'user': user}))

        self.assertEqual(
            '<a href="mailto:hripley@nostromo.corp">hripley@nostromo.corp</a>',
            render.strip()
        )

    def test_cell_is_sortable(self):
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell1 = build_cell(name='email')
        cell2 = build_cell(name='languages')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% if cell1|cell_is_sortable:registry %}CELL1 IS SORTABLE{% endif %}'
                r'{% if cell2|cell_is_sortable:registry %}CELL2 IS SORTABLE{% endif %}'
            )
            render = template.render(Context({
                'cell1': cell1,
                'cell2': cell2,
                'registry': cell_sorter_registry,
            }))

        self.assertEqual('CELL1 IS SORTABLE', render.strip())

# TODO: missing argument ?