from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template, TemplateSyntaxError
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.sorter import cell_sorter_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import Currency, FakeContact

from ..base import CremeTestCase


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
            render = template.render(Context({
                'model1': Currency,
                'model2': FakeContact,
            }))

        self.assertEqual(
            'regular_field-name#regular_field-first_name',
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
            render = template.render(Context({
                'ct1': get_ct(Currency),
                'ct2': get_ct(FakeContact),
            }))

        self.assertEqual(
            'regular_field-name#regular_field-first_name',
            render.strip()
        )

    def test_cell_4_regularfield03(self):
        "By instance."
        user = self.get_root_user()

        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield instance=helen field="first_name" as fname_cell %}'
                r'{% cell_4_regularfield instance=helen field="last_name" as lname_cell %}'
                r'{{fname_cell.key}}#{{lname_cell.key}}'
            )
            render = template.render(Context({'helen': ripley}))

        self.assertEqual(
            'regular_field-first_name#regular_field-last_name',
            render.strip()
        )

    def test_cell_4_regularfield04(self):
        "No assignment."
        user = self.get_root_user()

        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield instance=helen field="first_name" %}'
            )
            render = template.render(Context({'helen': ripley}))

        self.assertEqual(_('First name'), render.strip())

    def test_cell_4_regularfield_syntax_errors(self):
        ctxt = Context({'ct': ContentType.objects.get_for_model(Currency)})

        with self.assertRaises(TemplateSyntaxError) as cm1:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct as inv_cell %}'
            ).render(ctxt)

        self.assertEqual(
            '"cell_4_regularfield" takes 2 arguments (ctype/instance=... & field=...), '
            '& then optionally "as my_var".',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm2:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field="name" assign inv_cell %}'
            ).render(ctxt)

        self.assertEqual(
            '"cell_4_regularfield" tag expected a keyword "as" here, found "assign".',
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm3:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ct field="name" as inv_cell %}'
            ).render(ctxt)

        self.assertEqual(
            '"cell_4_regularfield" tag has a malformed 1rst argument: <ct>.',
            str(cm3.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm4:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield class=ct field="name" as inv_cell %}'
            ).render(ctxt)

        self.assertStartsWith(
            str(cm4.exception),
            '"cell_4_regularfield" tag has an invalid 1rst argument; it must be in [\'',
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm5:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct "name" as inv_cell %}'
            ).render(ctxt)

        self.assertEqual(
            '"cell_4_regularfield" tag a malformed 2nd argument: <"name">.',
            str(cm5.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm6:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field_name="name" as inv_cell %}'
            ).render(ctxt)

        self.assertEqual(
            '"cell_4_regularfield" tag has an invalid 2nd argument; it must be "field".',
            str(cm6.exception),
        )

    def test_cell_4_regularfield_render_errors(self):
        # Invalid field
        with self.assertRaises(ValueError) as cm1:
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field="invalid" as inv_cell %}'
            )
            template.render(Context({'ct': ContentType.objects.get_for_model(Currency)}))

        self.assertEqual(
            r'''{% cell_4_regularfield %}: the field seems invalid '''
            r'''(model=<class 'creme.creme_core.models.currency.Currency'>, field="invalid")''',
            str(cm1.exception),
        )

        # Invalid content type ---
        with self.assertRaises(AttributeError) as cm2:
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_4_regularfield ctype=ct field="name" as inv_cell %}'
            )
            template.render(Context({}))

        self.assertEqual(
            "'str' object has no attribute 'model_class'",
            str(cm2.exception),
        )

    def test_cell_render01(self):
        "Direct render ; default tag."
        user = self.get_root_user()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')
        cell = EntityCellRegularField.build(model=FakeContact, name='last_name')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user %}'
            )
            render = template.render(Context({
                'cell': cell, 'helen': ripley, 'user': user,
            }))

        self.assertEqual(ripley.last_name, render.strip())

    def test_cell_render_tag01(self):
        "Direct render ; tag=ViewTag.HTML_DETAIL."
        user = self.get_root_user()
        ripley = FakeContact(
            user=user, first_name='Helen', last_name='Ripley', email='hripley@nostromo.corp',
        )
        cell = EntityCellRegularField.build(model=FakeContact, name='email')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user tag=tag %}'
            )
            render = template.render(Context({
                'cell': cell, 'helen': ripley, 'user': user, 'tag': ViewTag.HTML_DETAIL,
            }))

        self.assertEqual(
            '<a href="mailto:hripley@nostromo.corp">hripley@nostromo.corp</a>',
            render.strip()
        )

    def test_cell_render_tag02(self):
        "Direct render ; tag=ViewTag.TEXT_PLAIN."
        user = self.get_root_user()
        ripley = FakeContact(
            user=user, first_name='Helen', last_name='Ripley',
            email='hripley@nostromo.corp',
        )
        cell = EntityCellRegularField.build(model=FakeContact, name='email')

        with self.assertNoException():
            template = Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen user=user tag=tag %}'
            )
            render = template.render(Context({
                'cell': cell, 'helen': ripley, 'user': user, 'tag': ViewTag.TEXT_PLAIN,
            }))

        self.assertEqual(ripley.email, render.strip())

    def test_cell_render_assignment(self):
        user = self.get_root_user()
        ripley = FakeContact(
            user=user, first_name='Helen', last_name='Ripley',
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

    def test_cell_render_syntax_errors(self):
        user = self.get_root_user()
        ripley = FakeContact(user=user, first_name='Helen', last_name='Ripley')
        cell = EntityCellRegularField.build(model=FakeContact, name='last_name')

        with self.assertRaises(TemplateSyntaxError) as cm1:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell instance=helen %}'
            ).render(Context({
                'cell': cell, 'helen': ripley, 'user': user,
            }))

        self.assertEqual(
            '"cell_render" tag takes at least 3 arguments (cell, instance, user)',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm2:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell helen user=user %}'
            ).render(Context({
                'cell': cell, 'helen': ripley, 'user': user,
            }))

        self.assertEqual(
            '"cell_render" tag has a malformed arguments: <helen>.',
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm3:
            Template(
                r'{% load creme_cells %}'
                r'{% cell_render cell=cell object=helen user=user %}'
            ).render(Context({
                'cell': cell, 'helen': ripley, 'user': user,
            }))

        self.assertEqual(
            '"cell_render" tag has an invalid argument name: <object>.',
            str(cm3.exception),
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
