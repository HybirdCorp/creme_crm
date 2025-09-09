from copy import deepcopy
from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegistry,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.forms.header_filter import (
    EntityCellCustomFieldsWidget,
    EntityCellFunctionFieldsWidget,
    EntityCellRegularFieldsField,
    EntityCellRegularFieldsWidget,
    EntityCellRelationsWidget,
    EntityCellsField,
    EntityCellsWidget,
)
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    FakeAddress,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)

from .. import fake_constants
from ..base import CremeTestCase


class EntityCellsFieldTestCaseMixin:
    def _find_sub_widget(self, field, cell_class_type_id):
        available = []

        for sub_widget in field.widget.sub_widgets:
            current_type_id = sub_widget.type_id

            if current_type_id == cell_class_type_id:
                return sub_widget

            available.append(current_type_id)

        self.fail(f'Sub-widget "{cell_class_type_id}" not found in {available}.')

    def assertCellInChoices(self, cell_key, choices):
        for choice_cell_key, choice_cell in choices:
            if cell_key == choice_cell_key:
                if choice_cell.key != cell_key:
                    self.fail(
                        'The cell has been found, but choice Id does not match the cell key.'
                    )

                return

        self.fail(
            f'The choice for cell-key="{cell_key}" has not been found in '
            f'{[choice_cell_key for choice_cell_key, choice_cell in choices]}'
        )

    def assertCellNotInChoices(self, cell_key, choices):
        for choice_cell_key, choice_cell in choices:
            if cell_key == choice_cell_key:
                self.fail(
                    f'The choice for cell-key="{cell_key}" has been unexpectedly found.'
                )


class EntityCellRegularFieldsWidgetTestCase(CremeTestCase):
    def test_get_context1(self):
        widget = EntityCellRegularFieldsWidget()
        self.assertTupleEqual((), widget.choices)

        name = 'my_sub_widget'
        self.assertDictEqual(
            {
                'widget': {
                    'attrs': {},
                    'choices': [],
                    'hide_alone_subfield': True,
                    'is_hidden': False,
                    'name': name,
                    'only_leaves': False,
                    'required': False,
                    'template_name': 'creme_core/forms/widgets/entity-cells/regular-fields.html',
                    'value': None,
                },
            },
            widget.get_context(name=name, value=None, attrs=None),
        )

    def test_get_context2(self):
        choices = [
            (cell.key, cell) for cell in [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellRegularField.build(FakeContact, 'address'),
                EntityCellRegularField.build(FakeContact, 'address__zipcode'),
                EntityCellRegularField.build(FakeContact, 'address__city'),
            ]
        ]
        widget = EntityCellRegularFieldsWidget(choices=choices)
        self.assertListEqual(choices, widget.choices)

        name = 'sub_widget'
        attrs = {'class': 'regular-fields'}
        context = widget.get_context(name=name, value=None, attrs=attrs)['widget']
        self.assertEqual(name, context['name'])
        self.assertDictEqual(attrs, context['attrs'])

        choices = context['choices']
        self.assertEqual(3, len(choices))

        lname_label = _('Last name')
        lname_index = self.assertIndex(
            ('regular_field-last_name', lname_label, []),
            choices,
        )

        fname_label = _('First name')
        fname_index = self.assertIndex(
            ('regular_field-first_name', fname_label, []),
            choices,
        )

        if lname_label < fname_label:
            self.assertLess(lname_index, fname_index)
        else:
            self.assertLess(fname_index, lname_index)

        indices = {0, 1, 2}
        indices.discard(fname_index)
        indices.discard(lname_index)
        self.assertEqual(1, len(indices))

        address_choice = choices[indices.pop()]
        self.assertEqual('regular_field-address', address_choice[0])
        self.assertEqual(_('Billing address'),    address_choice[1])
        self.assertCountEqual(
            [
                ('regular_field-address__zipcode', _('Zip code')),
                ('regular_field-address__city',    _('City')),
            ],
            address_choice[2],
        )

    # TODO: test render


class EntityCellCustomFieldsWidgetTestCase(CremeTestCase):
    def test_get_context1(self):
        widget = EntityCellCustomFieldsWidget()
        self.assertTupleEqual((), widget.choices)

        name = 'my_sub_widget'
        self.assertDictEqual(
            {
                'widget': {
                    'attrs': {},
                    'choices': [],
                    'is_hidden': False,
                    'name': name,
                    'required': False,
                    'template_name': 'creme_core/forms/widgets/entity-cells/custom-fields.html',
                    'value': None,
                },
            },
            widget.get_context(name=name, value=None, attrs=None),
        )

    def test_get_context2(self):
        model = FakeContact
        create_cfield = partial(CustomField.objects.create, content_type=model)
        cfield1 = create_cfield(name='Size (cm)',   field_type=CustomField.INT)
        cfield2 = create_cfield(name='Weight (kg)', field_type=CustomField.FLOAT)

        choices = [
            (cell.key, cell) for cell in [
                EntityCellCustomField(customfield=cfield1),
                EntityCellCustomField(customfield=cfield2),
            ]
        ]
        widget = EntityCellCustomFieldsWidget(choices=choices)
        self.assertListEqual(choices, widget.choices)

        name = 'sub_widget'
        attrs = {'class': 'custom-fields'}
        context = widget.get_context(name=name, value=None, attrs=attrs)['widget']
        self.assertEqual(name, context['name'])
        self.assertDictEqual(attrs, context['attrs'])
        self.assertListEqual(
            [
                (f'custom_field-{cfield1.id}', cfield1.name),
                (f'custom_field-{cfield2.id}', cfield2.name),
            ],
            context['choices'],
        )

    # TODO: test render


class EntityCellFunctionFieldsWidgetTestCase(CremeTestCase):
    def test_get_context1(self):
        widget = EntityCellFunctionFieldsWidget()
        self.assertTupleEqual((), widget.choices)

        name = 'my_sub_widget'
        self.assertDictEqual(
            {
                'widget': {
                    'attrs': {},
                    'choices': [],
                    'is_hidden': False,
                    'name': name,
                    'required': False,
                    'template_name': 'creme_core/forms/widgets/entity-cells/function-fields.html',
                    'value': None,
                },
            },
            widget.get_context(name=name, value=None, attrs=None),
        )

    def test_get_context2(self):
        model = FakeContact
        func_field = function_field_registry.get(model, 'get_pretty_properties')

        cell = EntityCellFunctionField(model=model, func_field=func_field)
        choices = [(cell.key, cell)]
        widget = EntityCellFunctionFieldsWidget(choices=choices)
        self.assertListEqual(choices, widget.choices)

        name = 'sub_widget'
        attrs = {'class': 'function-fields'}
        context = widget.get_context(name=name, value=None, attrs=attrs)['widget']
        self.assertEqual(name, context['name'])
        self.assertDictEqual(attrs, context['attrs'])
        self.assertListEqual(
            [(cell.key, str(cell))],
            context['choices'],
        )

    # TODO: test render


class EntityCellRelationsWidgetTestCase(CremeTestCase):
    def test_get_context1(self):
        widget = EntityCellRelationsWidget()
        self.assertTupleEqual((), widget.choices)

        name = 'my_sub_widget'
        self.assertDictEqual(
            {
                'widget': {
                    'attrs': {},
                    'choices': [],
                    'is_hidden': False,
                    'name': name,
                    'required': False,
                    'template_name': 'creme_core/forms/widgets/entity-cells/relationships.html',
                    'value': None,
                },
            },
            widget.get_context(name=name, value=None, attrs=None),
        )

    def test_get_context2(self):
        model = FakeContact

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        likes = RelationType.objects.builder(
            id='test-subject_like', predicate='Is liking',
        ).symmetric(id='test-object_like', predicate='Is liked by').get_or_create()[0]

        choices = [
            (cell.key, cell) for cell in [
                EntityCellRelation(model=model, rtype=loves),
                EntityCellRelation(model=model, rtype=likes),
            ]
        ]
        widget = EntityCellRelationsWidget(choices=choices)
        self.assertListEqual(choices, widget.choices)

        name = 'rel_widget'
        attrs = {'class': 'relationships'}
        context = widget.get_context(name=name, value=None, attrs=attrs)['widget']
        self.assertEqual(name, context['name'])
        self.assertDictEqual(attrs, context['attrs'])
        self.assertListEqual(
            [
                (f'relation-{likes.id}', likes.predicate),
                (f'relation-{loves.id}', loves.predicate),
            ],
            context['choices'],
        )

    # TODO: test render


class EntityCellsWidgetTestCase(CremeTestCase):
    def test_sub_widgets(self):
        widget = EntityCellsWidget(model=FakeContact)
        self.assertListEqual([], [*widget.sub_widgets])

        widget.sub_widgets = [
            EntityCellRegularFieldsWidget(),
            EntityCellRelationsWidget(),
        ]
        sub_widgets = [*widget.sub_widgets]
        self.assertEqual(2, len(sub_widgets))
        self.assertIsInstance(sub_widgets[0], EntityCellRegularFieldsWidget)
        self.assertIsInstance(sub_widgets[1], EntityCellRelationsWidget)

    def test_context01(self):
        widget = EntityCellsWidget(model=FakeContact)
        widget.user = self.get_root_user()

        name = 'my_cells'

        with self.assertNoException():
            context = widget.get_context(name=name, value=[], attrs=None)['widget']

        self.assertEqual(name, context.get('name'))
        self.assertIs(False, context.get('is_hidden'))
        self.assertIsNone(context.get('value', -1))
        self.assertDictEqual({}, context.get('attrs'))
        self.assertEqual(
            'creme_core/forms/widgets/entity-cells/widget.html',
            context.get('template_name'),
        )
        self.assertListEqual([], context.get('samples'))

    def test_context02(self):
        model = FakeContact
        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=model,
        )
        ffield = function_field_registry.get(model, 'get_pretty_properties')

        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(
            first_name='Kadode', last_name='Koyama', email='koyama@isobeyan.jp',
        )
        contact2 = create_contact(first_name='Oran',   last_name='Nakagawa')

        widget = EntityCellsWidget(model=FakeContact)
        widget.user = user
        widget.sub_widgets = [
            EntityCellRegularFieldsWidget(
                choices=[
                    (cell.key, cell) for cell in [
                        EntityCellRegularField.build(FakeContact, 'first_name'),
                        EntityCellRegularField.build(FakeContact, 'last_name'),
                        EntityCellRegularField.build(FakeContact, 'email'),
                    ]
                ],
            ),
            EntityCellCustomFieldsWidget(
                choices=[
                    (cell.key, cell) for cell in [
                        EntityCellCustomField(customfield=cfield),
                    ]
                ],
            ),
            EntityCellFunctionFieldsWidget(
                choices=[
                    (cell.key, cell) for cell in [
                        EntityCellFunctionField(model=model, func_field=ffield),
                    ]
                ],
            ),
            EntityCellRelationsWidget(
                choices=[
                    (cell.key, cell) for cell in [
                        EntityCellRelation(model=model, rtype=loves),
                    ]
                ],
            ),
        ]

        name = 'my_cells'
        value = [
            EntityCellRegularField.build(model, 'last_name'),
            EntityCellRelation(model=model, rtype=loves),
            EntityCellCustomField(customfield=cfield),
            EntityCellFunctionField(model=model, func_field=ffield),
        ]

        with self.assertNoException():
            context = widget.get_context(name=name, value=value, attrs=None)['widget']

        self.assertEqual(name, context.get('name'))
        self.assertIs(False, context.get('is_hidden'))

        value = (
            f'regular_field-last_name,'
            f'relation-{loves.id},'
            f'custom_field-{cfield.id},'
            f'function_field-{ffield.name}'
        )
        self.assertEqual(value, context.get('value'))
        self.assertDictEqual({}, context.get('attrs'))
        self.assertEqual(
            'creme_core/forms/widgets/entity-cells/widget.html',
            context.get('template_name'),
        )
        self.maxDiff = None
        self.assertListEqual(
            [
                {
                    'regular_field-first_name':      contact2.first_name,
                    'regular_field-last_name':       contact2.last_name,
                    'regular_field-email':           '',
                    f'custom_field-{cfield.id}':     '',
                    f'function_field-{ffield.name}': '',
                    f'relation-{loves.id}':          '',
                }, {
                    'regular_field-first_name':      contact1.first_name,
                    'regular_field-last_name':       contact1.last_name,
                    'regular_field-email':
                        f'<a href="mailto:{contact1.email}">{contact1.email}</a>',
                    f'custom_field-{cfield.id}':     '',
                    f'function_field-{ffield.name}': '',
                    f'relation-{loves.id}':          '',
                },
            ],
            context.get('samples'),
        )

        rfield_ctxt = context.get('regular_field')
        self.assertIsInstance(rfield_ctxt, dict)
        self.assertCountEqual(
            [
                ('regular_field-last_name',  _('Last name'),     []),
                ('regular_field-first_name', _('First name'),    []),
                ('regular_field-email',      _('Email address'), []),
            ],
            rfield_ctxt.pop('choices', ()),
        )
        self.assertDictEqual(
            {
                'name': name,
                'is_hidden': False,
                'required': False,
                'value': value,
                'attrs': {},
                'template_name': 'creme_core/forms/widgets/entity-cells/regular-fields.html',
                'hide_alone_subfield': True,
                'only_leaves': False,
            },
            rfield_ctxt,
        )

        self.assertIn('custom_field',   context)
        self.assertIn('function_field', context)
        self.assertIn('relation',       context)

    # TODO: test render


class EntityCellsFieldTestCase(EntityCellsFieldTestCaseMixin, CremeTestCase):
    def test_clean_empty_required(self):
        field = EntityCellsField(required=True, model=FakeContact)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')

    def test_clean_empty_not_required(self):
        field = EntityCellsField(required=False, model=FakeContact)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_regularfields01(self):
        field = EntityCellsField()
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        fname1 = 'created'
        value = f'regular_field-{fname1}'
        self.assertCellInChoices(value, choices=choices)
        self.assertCellNotInChoices('regular_field-entity_type', choices=choices)
        self.assertCellInChoices('regular_field-user',           choices=choices)
        self.assertCellInChoices('regular_field-user__username', choices=choices)
        self.assertCellNotInChoices('regular_field-user__is_staff', choices=choices)

        self.assertListEqual(
            [EntityCellRegularField.build(CremeEntity, fname1)],
            field.clean(value),
        )

        fname2 = 'unknown'
        msg = _('This value is invalid: %(value)s')
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-{fname2}',
            messages=msg % {'value': fname2},
            codes='invalid_value',
        )
        self.assertFormfieldError(
            field=field,
            value='regular_field-entity_type',
            messages=msg % {'value': 'entity_type'},
            codes='invalid_value',
        )

    def test_regularfields02(self):
        field = EntityCellsField(model=FakeContact)
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-created', choices=choices)
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices('regular_field-first_name', choices=choices)
        self.assertCellInChoices('regular_field-sector', choices=choices)
        self.assertCellInChoices('regular_field-civility', choices=choices)
        self.assertCellInChoices('regular_field-address', choices=choices)

        self.assertCellInChoices('regular_field-sector__title', choices=choices)
        self.assertCellNotInChoices('regular_field-sector__is_custom', choices=choices)
        self.assertCellInChoices('regular_field-civility__shortcut', choices=choices)

        self.assertCellInChoices('regular_field-address__city', choices=choices)
        self.assertCellInChoices('regular_field-address__country', choices=choices)

        self.assertCellInChoices('regular_field-image',             choices=choices)
        self.assertCellInChoices('regular_field-image__name',       choices=choices)
        self.assertCellInChoices('regular_field-image__user',       choices=choices)
        self.assertCellInChoices('regular_field-image__categories', choices=choices)
        self.assertCellNotInChoices('regular_field-image__user__username',   choices=choices)
        self.assertCellNotInChoices('regular_field-image__categories__name', choices=choices)

        # ----
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'sector__title'),
                EntityCellRegularField.build(FakeContact, 'address__city'),
                EntityCellRegularField.build(FakeContact, 'image__user'),
                EntityCellRegularField.build(FakeContact, 'image__categories'),
            ],
            field.clean(
                'regular_field-first_name,'
                'regular_field-sector__title,'
                'regular_field-address__city,'
                'regular_field-image__user,'
                'regular_field-image__categories'
            )
        )

        msg = _('This value is invalid: %(value)s')
        self.assertFormfieldError(
            field=field,
            value='regular_field-sector__is_custom',
            messages=msg % {'value': 'sector__is_custom'},
            codes='invalid_value',
        )
        self.assertFormfieldError(
            field=field,
            value='regular_field-image__user__username',
            messages=msg % {'value': 'image__user__username'},
            codes='invalid_value',
        )
        self.assertFormfieldError(
            field=field,
            value='regular_field-image__categories__name',
            messages=msg % {'value': 'image__categories__name'},
            codes='invalid_value',
        )

    def test_regularfields03(self):
        "Property <model>."
        field = EntityCellsField()
        self.assertIs(field.model,        CremeEntity)
        self.assertIs(field.widget.model, CremeEntity)

        field.model = FakeContact
        self.assertEqual(FakeContact, field.model)

        widget = field.widget
        self.assertIs(widget.model, FakeContact)

        fname = 'last_name'
        value = f'regular_field-{fname}'
        self.assertCellInChoices(
            value,
            choices=self._find_sub_widget(field, 'regular_field').choices,
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname)],
            field.clean(value)
        )

    def test_regularfields04(self):
        "Hidden fields."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'description'  # NB: in CremeEntity
        hidden_addr_fname = 'city'
        hidden_img_fname1 = 'exif_date'
        hidden_img_fname2 = 'description'  # NB: in CremeEntity

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_addr_fname, {FieldsConfig.HIDDEN: True})],
        )
        create_fconf(
            content_type=FakeImage,
            descriptions=[
                (hidden_img_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_img_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        field = EntityCellsField(model=FakeContact)
        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellNotInChoices(f'regular_field-{hidden_fname1}', choices=choices)
        self.assertCellNotInChoices(f'regular_field-{hidden_fname2}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellNotInChoices(
            f'regular_field-address__{hidden_addr_fname}',
            choices=choices,
        )

        self.assertCellInChoices('regular_field-image__categories', choices=choices)
        self.assertCellNotInChoices(
            f'regular_field-image__{hidden_img_fname1}',
            choices=choices,
        )
        self.assertCellNotInChoices(
            f'regular_field-image__{hidden_img_fname2}',
            choices=choices,
        )

        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            field.clean('regular_field-last_name'),
        )

        msg = _('This value is invalid: %(value)s')
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-{hidden_fname1}',
            messages=msg % {'value': hidden_fname1},
            codes='invalid_value',
        )
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-address__{hidden_addr_fname}',
            messages=msg % {'value': f'address__{hidden_addr_fname}'},
            codes='invalid_value',
        )

    def test_regularfields05(self):
        "Hidden fields + selected cells."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'description'  # Nb: in CremeEntity
        hidden_addr_fname = 'city'
        hidden_img_fname1 = 'exif_date'
        hidden_img_fname2 = 'description'  # NB: in CremeEntity

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_addr_fname, {FieldsConfig.HIDDEN: True})],
        )
        create_fconf(
            content_type=FakeImage,
            descriptions=[
                (hidden_img_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_img_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        field = EntityCellsField()
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, hidden_fname2),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_addr_fname}'),
            EntityCellRegularField.build(FakeContact, f'image__{hidden_img_fname1}'),
            EntityCellRegularField.build(FakeContact, f'image__{hidden_img_fname2}'),
        ]
        field.non_hiddable_cells = cells
        field.model = FakeContact
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname1}', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname2}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellInChoices(
            f'regular_field-address__{hidden_addr_fname}',
            choices=choices,
        )

        self.assertCellInChoices(
            f'regular_field-image__{hidden_img_fname1}',
            choices=choices,
        )
        self.assertCellInChoices(
            f'regular_field-image__{hidden_img_fname2}',
            choices=choices,
        )

        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellRegularField.build(FakeContact, hidden_fname1),
                EntityCellRegularField.build(FakeContact, f'address__{hidden_addr_fname}'),
            ],
            field.clean(
                'regular_field-last_name,'
                f'regular_field-{hidden_fname1},'
                f'regular_field-address__{hidden_addr_fname}'
            )
        )

    def test_regularfields06(self):
        """Hidden fields + selected cells.
        (<non_hiddable_cells> called after setting content type).
        """
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'city'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname2, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(model=FakeContact)
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_fname2}'),
        ]
        field.non_hiddable_cells = cells
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname1}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellInChoices(f'regular_field-address__{hidden_fname2}', choices=choices)

    def test_regularfields_only_leaves(self):
        class OnlyLeavesRegularFields(EntityCellRegularFieldsField):
            only_leaves = True

        class OnlyLeavesEntityCellsField(EntityCellsField):
            field_classes = {OnlyLeavesRegularFields}

        field = OnlyLeavesEntityCellsField(model=FakeContact)

        fname1 = 'first_name'
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname1)],
            field.clean(f'regular_field-{fname1}'),
        )

        fname2 = 'sector__title'
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname2)],
            field.clean(f'regular_field-{fname2}'),
        )

        fname3 = 'sector'
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-{fname3}',
            messages=_(
                'This field has sub-field & cannot be selected: %(value)s'
            ) % {'value': fname3},
            codes='not_leaf',
        )

    def test_customfields01(self):
        create_cf = partial(
            CustomField.objects.create, content_type=FakeContact,
        )
        cf1 = create_cf(field_type=CustomField.BOOL, name='Pilots?')
        cf2 = create_cf(field_type=CustomField.STR,  name='Dog tag')
        cf3 = create_cf(
            field_type=CustomField.BOOL, name='Operational?',
            content_type=FakeOrganisation,
        )

        field1 = EntityCellsField(model=FakeContact)

        choices1 = self._find_sub_widget(field1, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices1)
        self.assertCellInChoices(f'custom_field-{cf2.id}', choices=choices1)
        self.assertCellNotInChoices(f'custom_field-{cf3.id}', choices=choices1)

        # ---
        field2 = EntityCellsField()
        field2.model = FakeContact

        choices2 = self._find_sub_widget(field2, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices2)

        # ----
        self.assertListEqual(
            [EntityCellCustomField(cf1), EntityCellCustomField(cf2)],
            field2.clean(f'custom_field-{cf1.id},custom_field-{cf2.id}')
        )

        value = '1024'
        self.assertFormfieldError(
            field=field2,
            value=f'custom_field-{value}',
            messages=_('This value is invalid: %(value)s') % {'value': value},
            codes='invalid_value',
        )

    def test_customfields02(self):
        "Deleted fields."
        create_cf = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(model=FakeContact)

        choices = self._find_sub_widget(field, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices)
        self.assertCellNotInChoices(f'custom_field-{cf2.id}', choices=choices)

        self.assertListEqual(
            [EntityCellCustomField(cf1)],
            field.clean(f'custom_field-{cf1.id}'),
        )
        self.assertFormfieldError(
            field=field,
            value=f'custom_field-{cf2.id}',
            messages=_('This value is invalid: %(value)s') % {'value': cf2.id},
            codes='invalid_value',
        )

    def test_customfields03(self):
        "Deleted fields  + selected cells."
        create_cf = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(model=FakeContact)
        field.non_hiddable_cells = [EntityCellCustomField(cf2)]

        choices = self._find_sub_widget(field, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices)
        self.assertCellInChoices(f'custom_field-{cf2.id}', choices=choices)

        # ----
        self.assertListEqual(
            [EntityCellCustomField(cf1), EntityCellCustomField(cf2)],
            field.clean(f'custom_field-{cf1.id},custom_field-{cf2.id}')
        )

    def test_functionfields(self):
        field = EntityCellsField(model=FakeContact)
        name1 = 'get_pretty_properties'
        value = f'function_field-{name1}'
        self.assertCellInChoices(
            value, choices=self._find_sub_widget(field, 'function_field').choices,
        )
        self.assertListEqual(
            [EntityCellFunctionField.build(FakeContact, name1)],
            field.clean(value),
        )

        name2 = 'invalid'
        self.assertFormfieldError(
            field=field,
            value=f'function_field-{name2}',
            messages=_('This value is invalid: %(value)s') % {'value': name2},
            codes='invalid_value',
        )

    def test_relations(self):
        rtype1 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
        )
        rtype2 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_OBJ_EMPLOYED_BY,
        )
        rtype3 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_SUB_BILL_ISSUED,
        )

        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='whatever').get_or_create()[0]

        field1 = EntityCellsField(model=FakeContact)

        choices1 = self._find_sub_widget(field1, 'relation').choices
        self.assertCellInChoices(f'relation-{rtype1.id}', choices=choices1)
        self.assertCellNotInChoices(f'relation-{rtype2.id}', choices=choices1)
        self.assertCellNotInChoices(f'relation-{rtype3.id}', choices=choices1)
        self.assertCellNotInChoices(f'relation-{disabled_rtype.id}', choices=choices1)

        # ---
        field2 = EntityCellsField()
        field2.model = FakeContact

        choices2 = self._find_sub_widget(field2, 'relation').choices
        self.assertCellInChoices(f'relation-{rtype1.id}', choices=choices2)
        self.assertCellNotInChoices(f'relation-{rtype2.id}', choices=choices2)

        self.assertListEqual(
            [EntityCellRelation(model=FakeContact, rtype=rtype1)],
            field2.clean(f'relation-{rtype1.id}')
        )
        self.assertFormfieldError(
            field=field2,
            value=f'relation-{rtype2.id}',
            messages=_(
                'This type of relationship is not compatible with «%(model)s».'
            ) % {'model': 'Test Contact'},
            codes='incompatible',
        )
        self.assertFormfieldError(
            field=field2,
            value=f'relation-{disabled_rtype.id}',
            messages=_('This type of relationship is disabled.'),
            codes='disabled',
        )

        # Non hiddable cells ---
        field3 = EntityCellsField()
        initial_cells = [
            EntityCellRelation(model=FakeContact, rtype=rtype1),
            EntityCellRelation(model=FakeContact, rtype=disabled_rtype),
        ]
        field3.non_hiddable_cells = initial_cells
        field3.model = FakeContact
        self.assertListEqual(initial_cells, field3.non_hiddable_cells)

        choices3 = self._find_sub_widget(field3, 'relation').choices
        self.assertCellInChoices(f'relation-{rtype1.id}',         choices=choices3)
        self.assertCellInChoices(f'relation-{disabled_rtype.id}', choices=choices3)
        self.assertCellNotInChoices(f'relation-{rtype2.id}', choices=choices3)

        with self.assertNoException():
            cleaned_cells = field3.clean(f'relation-{disabled_rtype.id}')
        self.assertListEqual(
            [EntityCellRelation(model=FakeContact, rtype=disabled_rtype)],
            cleaned_cells,
        )

    def test_ok01(self):
        "One regular field."
        field = EntityCellsField(model=FakeContact)
        fname = 'first_name'
        cell = self.get_alone_element(field.clean(f'regular_field-{fname}'))
        self.assertEqual(EntityCellRegularField.build(FakeContact, fname), cell)
        self.assertIs(cell.is_hidden, False)

    def assertCellOK(self, cell, expected_cls, expected_value):
        self.assertIsInstance(cell, expected_cls)
        self.assertEqual(expected_value, cell.value)

    def test_ok02(self):
        "All types of columns."
        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        customfield = CustomField.objects.create(
            name='Size (cm)', field_type=CustomField.INT, content_type=FakeContact,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        field = EntityCellsField(model=FakeContact)
        cells = field.clean(
            f'relation-{loves.id},'
            f'regular_field-last_name,'
            f'function_field-{funcfield.name},'
            f'custom_field-{customfield.id},'
            f'regular_field-first_name'
        )

        self.assertEqual(5, len(cells))
        self.assertCellOK(cells[0], EntityCellRelation,     loves.id)
        self.assertCellOK(cells[1], EntityCellRegularField, 'last_name')
        self.assertCellOK(cells[2], EntityCellFunctionField, funcfield.name)
        self.assertCellOK(cells[3], EntityCellCustomField,   str(customfield.id))
        self.assertCellOK(cells[4], EntityCellRegularField, 'first_name')

    def test_error(self):
        "Invalid type id."
        self.assertFormfieldError(
            field=EntityCellsField(model=FakeContact, required=False),
            value='unknown-donotcare',
            messages='The type of cell in invalid: %(type_id)s.' % {'type_id': 'unknown'},
            codes='invalid_type',
        )

    def test_cell_registry01(self):
        field = EntityCellsField()

        registry1 = field.cell_registry
        self.assertIsInstance(registry1, EntityCellRegistry)
        self.assertIn(EntityCellRegularField.type_id,  registry1)
        self.assertIn(EntityCellCustomField.type_id,   registry1)
        self.assertIn(EntityCellFunctionField.type_id, registry1)
        self.assertIn(EntityCellRelation.type_id,      registry1)

        registry2 = EntityCellRegistry()
        registry2(EntityCellRegularField)
        registry2(EntityCellRelation)

        field.cell_registry = registry2
        self.assertIs(registry2, field.cell_registry)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-created', choices=choices)

        self._find_sub_widget(field, 'regular_field')

        def assertNoSubWidget(widget_class):
            for sub_widget in field.widget.sub_widgets:
                if isinstance(sub_widget, widget_class):
                    self.fail(f'Sub-widget unexpectedly found: {widget_class}.')

        assertNoSubWidget(EntityCellCustomFieldsWidget)
        assertNoSubWidget(EntityCellFunctionFieldsWidget)

        self.assertFormfieldError(
            field=field,
            value='function_field-get_pretty_properties',
            messages='The type of cell in invalid: %(type_id)s.' % {'type_id': 'function_field'},
            codes='invalid_type',
        )

    def test_cell_registry02(self):
        "Set non_hiddable cells BEFORE."
        fname = 'first_name'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(fname, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(model=FakeContact)
        field.non_hiddable_cells = [
            EntityCellRegularField.build(FakeContact, fname),
        ]

        registry = EntityCellRegistry()
        registry(EntityCellRegularField)
        registry(EntityCellRelation)

        field.cell_registry = registry

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices(f'regular_field-{fname}', choices=choices)

    def test_copy01(self):
        "Attribute <non_hiddable_cells>."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        field1.non_hiddable_cells = [
            EntityCellRegularField.build(FakeContact, 'first_name'),
        ]
        self.assertListEqual([], field2.non_hiddable_cells)

    def test_copy02(self):
        "Attribute <_sub_fields> (container)."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        registry = EntityCellRegistry()
        registry(EntityCellRegularField)
        registry(EntityCellRelation)

        field1.cell_registry = registry

        ffield_name = 'get_pretty_properties'
        value = f'function_field-{ffield_name}'
        self.assertFormfieldError(
            field=field1, value=value,
            messages='The type of cell in invalid: %(type_id)s.' % {'type_id': 'function_field'},
            codes='invalid_type',
        )
        self.assertListEqual(
            [EntityCellFunctionField.build(FakeContact, ffield_name)],
            field2.clean(value),
        )

    def test_copy03(self):
        "Attribute <_sub_fields> (content) & sub-widgets' choices."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        field1.model = FakeOrganisation
        self.assertIsNot(field1._sub_fields[0], field2._sub_fields[0])
        self.assertIsNot(field1._sub_fields[0].widget, field2._sub_fields[0].widget)
        self.assertIsNot(field1.widget, field2.widget)
        self.assertIsNot(field1.widget._sub_widgets[0], field2.widget._sub_widgets[0])

        self.assertEqual(FakeOrganisation, field1.model)
        self.assertEqual(FakeOrganisation, field1.widget.model)
        self.assertEqual(FakeContact,      field2.model)
        self.assertEqual(FakeContact,      field2.widget.model)

        contact_fname = 'first_name'
        contact_value = f'regular_field-{contact_fname}'
        msg = _('This value is invalid: %(value)s')
        self.assertFormfieldError(
            field=field1,
            value=contact_value,
            messages=msg % {'value': contact_fname},
            codes='invalid_value',
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, contact_fname)],
            field2.clean(contact_value)
        )

        choices1 = self._find_sub_widget(field1, 'regular_field').choices
        choices2 = self._find_sub_widget(field2, 'regular_field').choices
        self.assertCellInChoices(contact_value, choices=choices2)
        self.assertCellNotInChoices(contact_value, choices=choices1)

        orga_fname = 'capital'
        orga_value = f'regular_field-{orga_fname}'
        self.assertFormfieldError(
            field=field2,
            value=orga_value,
            messages=msg % {'value': orga_fname},
            codes='invalid_value',
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, orga_fname)],
            field1.clean(orga_value),
        )
        self.assertCellInChoices(orga_value, choices=choices1)
        self.assertCellNotInChoices(orga_value, choices=choices2)
