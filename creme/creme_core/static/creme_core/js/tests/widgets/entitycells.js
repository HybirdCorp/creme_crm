/* globals QUnitWidgetMixin */
(function($) {
QUnit.module("creme.widget.entity_cell.js", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitDialogMixin,
                                                           QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.entity_cell.js'});
    },

    beforeEach: function() {
        this.setMockBackendGET({});
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    },

    createHFilterHtml: function(options) {
        options = $.extend({
            id: 'test',
            required: true,
            value: [],
            regularfields: [],
            customfields: [],
            computedfields: [],
            relationfields: []
        }, options || {});

        var renderFieldUnderlays = function(fields) {
            fields = fields || [];

            if (fields.length === 0) {
                return '';
            }

            var res = (
                '<a href="" class="sub_selector_toggle">Toggle underlays</a>' +
                '<div class="underlay-container">' +
                     '<div class="underlay_wrapper">' +
                         '<div class="arrow"><div class="inside-arrow"></div></div>' +
                         '<div class="underlay-content">' +
                             '<span class="selector_close">×&nbsp;Fermer</span>' +
                             '<ul class="underlay_selector_list">${fields}</ul>' +
                         '</div>' +
                     '</div>' +
                     '<div class="underlay_mask"></div>' +
                '</div>').template({
                    fields: (fields || []).map(renderField).join('')
                });
            return res;
        };

        var renderField = function(field) {
            field = field || {};
            var label = '';

            if (Object.isEmpty(field.underlays)) {
                label = '<label>${label}</label>'.template({label: field.label || 'No label'});
            }

            return (
               '<li class="selector" data-column="${name}">' +
                   '<input type="checkbox" ${checked}>${label}' +
                   '${underlays}' +
               '</li>').template({
                   name: field.name,
                   checked: field.selected ? 'checked' : '',
                   label: label,
                   underlays: renderFieldUnderlays(field.underlays || [])
               });
        };

        return (
            '<div class="hfilter_widget" ${required} id="${id}">' +
                '<input class="inner_value" type="hidden" name="cells" value="${value}">' +
                '<div class="selectors">' +
                    '<div class="field_selectors">' +
                        '<div class="selector_filter">' +
                            '<input type="search" class="field_selector_filter" name="cells_field_selector_filter" data-type="fields">' +
                        '</div>' +
                        '<div class="basic_field_selectors">' +
                            '<ul class="selector_list">${regularfields}</ul>' +
                        '</div>' +
                        '<div class="custom_field_selectors inline_selectors">' +
                            '<ul class="selector_list">${customfields}</ul>' +
                        '</div>' +
                        '<div class="computed_field_selectors inline_selectors">' +
                            '<ul class="selector_list">${computedfields}</ul>' +
                        '</div>' +
                    '</div>' +
                    '<div class="relationship_selectors">' +
                        '<div class="selector_filter">' +
                            '<span class="filter_result"></span>' +
                            '<input type="search" class="field_selector_filter" name="cells_relationships_selector_filter" data-type="relationships">' +
                        '</div>' +
                        '<ul class="selector_list">${relationfields}</ul>' +
                    '</div>' +
                '</div>' +
                '<div class="preview">' +
                    '<h3 class="preview_title"></h3>' +
                    '<div class="selector_filter">' +
                        '<a href="" class="remove_all_columns">Remove All</a>' +
                    '</div>' +
                    '<table class="preview_table">' +
                        '<thead class="preview_table_header">' +
                            '<tr class="sortable_header"></tr>' +
                        '</thead>' +
                        '<tbody>' +
                            '<tr class="preview_row"></tr>' +
                            '<tr class="preview_row"></tr>' +
                        '</tbody>' +
                    '</table>' +
                '</div>' +
            '</div>').template({
                id: options.id,
                required: options.required ? 'required' : '',
                value: (options.value || []).join(','),
                regularfields: (options.regularfields || []).map(renderField).join(''),
                customfields: (options.customfields || []).map(renderField).join(''),
                computedfields: (options.computedfields || []).map(renderField).join(''),
                relationfields: (options.relationfields || []).map(renderField).join('')
            });
    }
}));

QUnit.test('creme.entity_cell.EntityCellsWidget (bind)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    });

    equal(false, widget.isBound());
    equal(undefined, widget.store);
    equal(undefined, widget.div);

    deepEqual({}, widget.column_titles);
    deepEqual([], widget.columns);
    deepEqual({}, widget.underlays);

    widget.bind(element);

    equal(true, widget.isBound());

    equal('', widget.store.val());
    equal(false, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    deepEqual([], widget.columns);

    deepEqual({}, widget.underlays);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (already bound)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id'
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    equal(true, widget.isBound());
    deepEqual({}, widget.column_titles);
    deepEqual([], widget.columns);
    deepEqual({}, widget.underlays);

    this.assertRaises(function() {
        widget.bind(element);
    }, Error, 'Error: EntityCellsWidget is already bound');
});

QUnit.test('creme.entity_cell.EntityCellsWidget (empty)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id'
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    equal(true, widget.isBound());
    deepEqual({}, widget.column_titles);
    deepEqual([], widget.columns);
    deepEqual({}, widget.underlays);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (regular, no selection)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    }).bind(element);

    equal('', widget.store.val());
    equal(false, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    deepEqual([], widget.columns);

    deepEqual({}, widget.underlays);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (regular, ordering)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-firstname', 'regular_field-email', 'regular_field-lastname'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    }).bind(element);

    equal('regular_field-firstname,regular_field-email,regular_field-lastname', widget.store.val());
    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    deepEqual([
        "regular_field-firstname",
        "regular_field-email",
        "regular_field-lastname"
    ], widget.columns);

    deepEqual({}, widget.underlays);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (regular, filtered)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element); ;
    var filter = element.find('.field_selector_filter[data-type="fields"]');

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);

    equal(1, filter.length);
    equal('', filter.val());

    equal(1.0, element.find('.selector[data-column="regular_field-email"]').css('opacity'));
    equal(1.0, element.find('.selector[data-column="regular_field-firstname"]').css('opacity'));
    equal(1.0, element.find('.selector[data-column="regular_field-lastname"]').css('opacity'));

    filter.val('name').trigger('propertychange');

    stop(2);

    // waiting for animation end
    setTimeout(function() {
        equal(0.4, element.find('.selector[data-column="regular_field-email"]').css('opacity'), '"email" item is filtered');
        equal(1.0, element.find('.selector[data-column="regular_field-firstname"]').css('opacity'));
        equal(1.0, element.find('.selector[data-column="regular_field-lastname"]').css('opacity'));

        filter.val('mail').trigger('propertychange');
        start();
    }, 500);

    // waiting for animation end
    setTimeout(function() {
        equal(1.0, element.find('.selector[data-column="regular_field-email"]').css('opacity'));
        equal(0.4, element.find('.selector[data-column="regular_field-firstname"]').css('opacity'), '"firstname" item is filtered');
        equal(0.4, element.find('.selector[data-column="regular_field-lastname"]').css('opacity'), '"lastname" item is filtered');
        start();
    }, 1000);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (regular)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    }).bind(element);

    equal('regular_field-email,regular_field-lastname', widget.store.val());
    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    deepEqual([
        "regular_field-email",
        "regular_field-lastname"
    ], widget.columns);

    deepEqual({}, widget.underlays);

    // unselect 'email'
    element.find('.selector_list .selector[data-column="regular_field-email"] > label').trigger('click');

    equal('regular_field-lastname', widget.store.val());
    deepEqual([
        "regular_field-lastname"
    ], widget.columns);

    // select 'firstname'
    element.find('.selector_list .selector[data-column="regular_field-firstname"] > label').trigger('click');

    equal('regular_field-lastname,regular_field-firstname', widget.store.val());
    deepEqual([
        "regular_field-lastname",
        "regular_field-firstname"
    ], widget.columns);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (regular, open underlay)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-billing_address__name'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {
                name: 'regular_field-billing_address',
                underlays: [
                    {name: 'regular_field-billing_address__name', label: 'Address'},
                    {name: 'regular_field-billing_address__country', label: 'Country'},
                    {name: 'regular_field-billing_address__city', label: 'City'}
                ]
            },
            {name: 'regular_field-phone', label: 'Phone'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [
            {'regular_field-email': 'abc@unknown.com'},
            {'regular_field-billing_address__name': ''},
            {'regular_field-billing_address__country': ''}
            // no default value for billing_address__city
        ]
    }).bind(element);

    equal('regular_field-email,regular_field-billing_address__name', widget.store.val());
    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-billing_address"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-billing_address__name"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-billing_address__country"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-billing_address__city"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-phone"] > input').is(':checked'));

    deepEqual({
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address",
        "regular_field-email": "Email",
        "regular_field-phone": "Phone"
    }, widget.column_titles);
    deepEqual([
        'regular_field-email',
        'regular_field-billing_address__name'
    ], widget.columns);


    // underlay is closed
    equal(0, element.find('.selector_list > .underlay[data-column="regular_field-billing_address"]').length);
    deepEqual({}, widget.underlays);

    // open underlay
    element.find('.selector_list > .selector[data-column="regular_field-billing_address"] .sub_selector_toggle').trigger('click');

    // new underlay added to cache
    equal(1, element.find('.selector_list > .underlay[data-column="regular_field-billing_address"]').length, 'underlay shown');
    this.equalOuterHtml(element.find('.selector_list .underlay[data-column="regular_field-billing_address"]'),
                        widget.underlays['regular_field-billing_address']);
});

QUnit.test('creme.entity_cell.EntityCellsWidget.select (custom)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname', 'custom_field-field_a'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ],
        customfields: [
            {name: 'custom_field-field_a', label: 'Field A'},
            {name: 'custom_field-field_b', label: 'Field B'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    equal('regular_field-email,regular_field-lastname,custom_field-field_a', widget.store.val());

    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="custom_field-field_a"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="custom_field-field_b"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "custom_field-field_a": 'Field A',
        "custom_field-field_b": 'Field B'
    }, widget.column_titles);
    deepEqual([
        'regular_field-email',
        'regular_field-lastname',
        'custom_field-field_a'
    ], widget.columns);
});

QUnit.test('creme.entity_cell.EntityCellsWidget.select (computed)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname', 'function_field-get_pretty_properties'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ],
        computedfields: [
            {name: 'function_field-get_pretty_properties', label: 'Properties'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    equal('regular_field-email,regular_field-lastname,function_field-get_pretty_properties', widget.store.val());

    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="function_field-get_pretty_properties"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "function_field-get_pretty_properties": 'Properties'
    }, widget.column_titles);
    deepEqual([
        'regular_field-email',
        'regular_field-lastname',
        'function_field-get_pretty_properties'
    ], widget.columns);
});

QUnit.test('creme.entity_cell.EntityCellsWidget.select (relations)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname', 'relation-persons-object_competitor'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'}
        ],
        relationfields: [
            {name: 'relation-persons-object_competitor', label: 'Has for competitor'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    equal('regular_field-email,regular_field-lastname,relation-persons-object_competitor', widget.store.val());

    equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    equal(true, element.find('.selector[data-column="relation-persons-object_competitor"] > input').is(':checked'));

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "relation-persons-object_competitor": 'Has for competitor'
    }, widget.column_titles);
    deepEqual([
        'regular_field-email',
        'regular_field-lastname',
        'relation-persons-object_competitor'
    ], widget.columns);
});


QUnit.test('creme.entity_cell.EntityCellsWidget (relation, filtered)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email'}
        ],
        relationfields: [
            {name: 'relation-persons-object_competitor', label: 'Has for competitor'},
            {name: 'relation-persons-subject_subsidiary', label: 'Is subsidiary'},
            {name: 'relation-persons-small', label: 'Is small'},
            {name: 'relation-persons-big', label: 'Is big'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);
    var filter = element.find('.field_selector_filter[data-type="relationships"]');
    var filter_result = element.find('.relationship_selectors .filter_result');

    deepEqual({
        "regular_field-email": "Email",
        "relation-persons-object_competitor": 'Has for competitor',
        "relation-persons-subject_subsidiary": 'Is subsidiary',
        "relation-persons-small": 'Is small',
        "relation-persons-big": 'Is big'
    }, widget.column_titles);

    equal(1, filter.length);
    equal(1, filter_result.length);

    equal('', filter.val());

    equal('', filter_result.text());
    equal(true, element.find('.selector[data-column="relation-persons-object_competitor"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-subject_subsidiary"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-small"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-big"]').is(':visible'));

    filter.val('is').trigger('propertychange');

    equal(gettext('%s result(s) on %s').format(3, 4), filter_result.text());
    equal(false, element.find('.selector[data-column="relation-persons-object_competitor"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-subject_subsidiary"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-small"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-big"]').is(':visible'));

    filter.val('competitor').trigger('propertychange');

    equal(gettext('%s result(s) on %s').format(1, 4), filter_result.text());
    equal(true, element.find('.selector[data-column="relation-persons-object_competitor"]').is(':visible'));
    equal(false, element.find('.selector[data-column="relation-persons-subject_subsidiary"]').is(':visible'));
    equal(false, element.find('.selector[data-column="relation-persons-small"]').is(':visible'));
    equal(false, element.find('.selector[data-column="relation-persons-big"]').is(':visible'));

    filter.val('').trigger('propertychange');

    equal('', filter_result.text());
    equal(true, element.find('.selector[data-column="relation-persons-object_competitor"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-subject_subsidiary"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-small"]').is(':visible'));
    equal(true, element.find('.selector[data-column="relation-persons-big"]').is(':visible'));
});


QUnit.test('creme.entity_cell.EntityCellsWidget.preview (remove all columns)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname', 'regular_field-billing_address__name'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'},
            {
                name: 'regular_field-billing_address',
                underlays: [
                    {name: 'regular_field-billing_address__name', label: 'Address'},
                    {name: 'regular_field-billing_address__country', label: 'Country'},
                    {name: 'regular_field-billing_address__city', label: 'City'}
                ]
            }
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    }).bind(element);

    equal('regular_field-email,regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    equal(gettext('Preview and order of the %s columns').format(3), element.find('.preview_title').text());

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address"
    }, widget.column_titles);
    deepEqual([
        "regular_field-email",
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    deepEqual({}, widget.underlays);

    element.find('.remove_all_columns').trigger('click');

    equal('', widget.store.val());
    equal(gettext('Preview'), element.find('.preview_title').text());

    deepEqual([], widget.columns);
});

QUnit.test('creme.entity_cell.EntityCellsWidget.preview (remove column)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        value: ['regular_field-email', 'regular_field-lastname', 'regular_field-billing_address__name'],
        regularfields: [
            {name: 'regular_field-email', label: 'Email'},
            {name: 'regular_field-firstname', label: 'First name'},
            {name: 'regular_field-lastname', label: 'Last name'},
            {
                name: 'regular_field-billing_address',
                underlays: [
                    {name: 'regular_field-billing_address__name', label: 'Address'},
                    {name: 'regular_field-billing_address__country', label: 'Country'},
                    {name: 'regular_field-billing_address__city', label: 'City'}
                ]
            }
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget({
        samples: [{'regular_field-email': 'abc@unknown.com'}]
    }).bind(element);

    equal('regular_field-email,regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    equal(gettext('Preview and order of the %s columns').format(3), element.find('.preview_title').text());

    deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address"
    }, widget.column_titles);
    deepEqual([
        "regular_field-email",
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    deepEqual({}, widget.underlays);

    // unselect 'email' column
    element.find('.preview th[data-column="regular_field-email"] .preview_column_toggle').trigger('click');

    equal('regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    equal(gettext('Preview and order of the %s columns').format(2), element.find('.preview_title').text());

    deepEqual([
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    // unselect 'billing address name' column
    element.find('.preview th[data-column="regular_field-billing_address__name"] .preview_column_toggle').trigger('click');
    equal(gettext('Preview of the column'), element.find('.preview_title').text());

    deepEqual([
        "regular_field-lastname"
    ], widget.columns);
});
}(jQuery));
