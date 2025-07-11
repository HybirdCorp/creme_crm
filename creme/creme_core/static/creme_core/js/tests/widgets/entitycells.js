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

    itemsDisplayStatus: function(element) {
        var state = {};

        element.find('.selector[data-column]').each(function() {
            state[$(this).data('column')] = {
                opacity: +($(this).css('opacity')),
                visible: $(this).is(':visible')
            };
        });

        return state;
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

    assert.equal(false, widget.isBound());
    assert.equal(undefined, widget.store);
    assert.equal(undefined, widget.div);

    assert.deepEqual({}, widget.column_titles);
    assert.deepEqual([], widget.columns);
    assert.deepEqual({}, widget.underlays);

    widget.bind(element);

    assert.equal(true, widget.isBound());

    assert.equal('', widget.store.val());
    assert.equal(false, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    assert.deepEqual([], widget.columns);

    assert.deepEqual({}, widget.underlays);
});

QUnit.test('creme.entity_cell.EntityCellsWidget (already bound)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id'
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    assert.equal(true, widget.isBound());
    assert.deepEqual({}, widget.column_titles);
    assert.deepEqual([], widget.columns);
    assert.deepEqual({}, widget.underlays);

    this.assertRaises(function() {
        widget.bind(element);
    }, Error, 'Error: EntityCellsWidget is already bound');
});

QUnit.test('creme.entity_cell.EntityCellsWidget (empty)', function(assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id'
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);

    assert.equal(true, widget.isBound());
    assert.deepEqual({}, widget.column_titles);
    assert.deepEqual([], widget.columns);
    assert.deepEqual({}, widget.underlays);
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

    assert.equal('', widget.store.val());
    assert.equal(false, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    assert.deepEqual([], widget.columns);

    assert.deepEqual({}, widget.underlays);
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

    assert.equal('regular_field-firstname,regular_field-email,regular_field-lastname', widget.store.val());
    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    assert.deepEqual([
        "regular_field-firstname",
        "regular_field-email",
        "regular_field-lastname"
    ], widget.columns);

    assert.deepEqual({}, widget.underlays);
});

QUnit.parametrize('creme.entity_cell.EntityCellsWidget (regular, filtered)', [
    [
        'name', {
            'regular_field-email': {opacity: 0.4, visible: true},
            'regular_field-firstname': {opacity: 1.0, visible: true},  // match "First Name"
            'regular_field-lastname': {opacity: 1.0, visible: true}   // match "Last Name"
         }
    ],
    [
        'mail', {
            'regular_field-email': {opacity: 1.0, visible: true},    // match "Email"
            'regular_field-firstname': {opacity: 0.4, visible: true},
            'regular_field-lastname': {opacity: 0.4, visible: true}
         }
    ],
    [
        'él', {
            'regular_field-email': {opacity: 1.0, visible: true},    // match "Électronique"
            'regular_field-firstname': {opacity: 0.4, visible: true},
            'regular_field-lastname': {opacity: 0.4, visible: true}
        }
    ],
    [
        'pre', {
            'regular_field-email': {opacity: 0.4, visible: true},
            'regular_field-firstname': {opacity: 1.0, visible: true},  // match "Prénom"
            'regular_field-lastname': {opacity: 0.4, visible: true}
        }
    ]
], function(term, expected, assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email / Courrier Électronique'},
            {name: 'regular_field-firstname', label: 'First Name / Prénom'},
            {name: 'regular_field-lastname', label: 'Last Name'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element); ;
    var filter = element.find('.field_selector_filter[data-type="fields"]');

    assert.deepEqual({
        "regular_field-email": "Email / Courrier Électronique",
        "regular_field-firstname": "First Name / Prénom",
        "regular_field-lastname": "Last Name"
    }, widget.column_titles);

    assert.equal(1, filter.length);
    assert.equal('', filter.val());

    assert.deepEqual({
        'regular_field-email': {opacity: 1.0, visible: true},
        'regular_field-firstname': {opacity: 1.0, visible: true},
        'regular_field-lastname': {opacity: 1.0, visible: true}
    }, this.itemsDisplayStatus(element));

    filter.val(term).trigger('propertychange');

    var done = assert.async();

    // waiting for animation end
    setTimeout(function() {
        var state = this.itemsDisplayStatus(element);
        assert.deepEqual(expected, state);
        done();
    }.bind(this), 500);
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

    assert.equal('regular_field-email,regular_field-lastname', widget.store.val());
    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name"
    }, widget.column_titles);
    assert.deepEqual([
        "regular_field-email",
        "regular_field-lastname"
    ], widget.columns);

    assert.deepEqual({}, widget.underlays);

    // unselect 'email'
    element.find('.selector_list .selector[data-column="regular_field-email"] > label').trigger('click');

    assert.equal('regular_field-lastname', widget.store.val());
    assert.deepEqual([
        "regular_field-lastname"
    ], widget.columns);

    // select 'firstname'
    element.find('.selector_list .selector[data-column="regular_field-firstname"] > label').trigger('click');

    assert.equal('regular_field-lastname,regular_field-firstname', widget.store.val());
    assert.deepEqual([
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

    assert.equal('regular_field-email,regular_field-billing_address__name', widget.store.val());
    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-billing_address"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-billing_address__name"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-billing_address__country"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-billing_address__city"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-phone"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address",
        "regular_field-email": "Email",
        "regular_field-phone": "Phone"
    }, widget.column_titles);
    assert.deepEqual([
        'regular_field-email',
        'regular_field-billing_address__name'
    ], widget.columns);


    // underlay is closed
    assert.equal(0, element.find('.selector_list > .underlay[data-column="regular_field-billing_address"]').length);
    assert.deepEqual({}, widget.underlays);

    // open underlay
    element.find('.selector_list > .selector[data-column="regular_field-billing_address"] .sub_selector_toggle').trigger('click');

    // new underlay added to cache
    assert.equal(1, element.find('.selector_list > .underlay[data-column="regular_field-billing_address"]').length, 'underlay shown');
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

    assert.equal('regular_field-email,regular_field-lastname,custom_field-field_a', widget.store.val());

    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="custom_field-field_a"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="custom_field-field_b"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "custom_field-field_a": 'Field A',
        "custom_field-field_b": 'Field B'
    }, widget.column_titles);
    assert.deepEqual([
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

    assert.equal('regular_field-email,regular_field-lastname,function_field-get_pretty_properties', widget.store.val());

    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="function_field-get_pretty_properties"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "function_field-get_pretty_properties": 'Properties'
    }, widget.column_titles);
    assert.deepEqual([
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

    assert.equal('regular_field-email,regular_field-lastname,relation-persons-object_competitor', widget.store.val());

    assert.equal(true, element.find('.selector[data-column="regular_field-email"] > input').is(':checked'));
    assert.equal(false, element.find('.selector[data-column="regular_field-firstname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="regular_field-lastname"] > input').is(':checked'));
    assert.equal(true, element.find('.selector[data-column="relation-persons-object_competitor"] > input').is(':checked'));

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "relation-persons-object_competitor": 'Has for competitor'
    }, widget.column_titles);
    assert.deepEqual([
        'regular_field-email',
        'regular_field-lastname',
        'relation-persons-object_competitor'
    ], widget.columns);
});


QUnit.parametrize('creme.entity_cell.EntityCellsWidget (relation, filtered)', [
    [
        'is', {
            summary: gettext('%s result(s) on %s').format(3, 4),
            items: {
                'relation-persons-object_competitor': {opacity: 1.0, visible: false},
                'relation-persons-subject_subsidiary': {opacity: 1.0, visible: true},
                'relation-persons-small': {opacity: 1.0, visible: true},
                'relation-persons-big': {opacity: 1.0, visible: true}
            }
        }
    ],
    [
        'rê', {
            summary: gettext('%s result(s) on %s').format(1, 4),
            items: {
                'relation-persons-object_competitor': {opacity: 1.0, visible: false},
                'relation-persons-subject_subsidiary': {opacity: 1.0, visible: false},
                'relation-persons-small': {opacity: 1.0, visible: true},   // match 'Frêle'
                'relation-persons-big': {opacity: 1.0, visible: false}
            }
        }
    ],
    [
        'à', {
            summary: gettext('%s result(s) on %s').format(3, 4),
            items: {
                'relation-persons-object_competitor': {opacity: 1.0, visible: true},  // match 'Has'
                'relation-persons-subject_subsidiary': {opacity: 1.0, visible: true}, // à
                'relation-persons-small': {opacity: 1.0, visible: true}, // match 'Small'
                'relation-persons-big': {opacity: 1.0, visible: false}
            }
        }
    ]
], function(term, expected, assert) {
    var element = $(this.createHFilterHtml({
        id: 'test-id',
        regularfields: [
            {name: 'regular_field-email', label: 'Email'}
        ],
        relationfields: [
            {name: 'relation-persons-object_competitor', label: 'Has for competitor / Est compétiteur de'},
            {name: 'relation-persons-subject_subsidiary', label: 'Is subsidiary / Est subordonné à'},
            {name: 'relation-persons-small', label: 'Is small / Frêle'},
            {name: 'relation-persons-big', label: 'Is big / Énorme'}
        ]
    })).appendTo(this.qunitFixture());

    var widget = new creme.entity_cell.EntityCellsWidget().bind(element);
    var filter = element.find('.field_selector_filter[data-type="relationships"]');
    var filter_result = element.find('.relationship_selectors .filter_result');
    var relationships = element.find('.relationship_selectors');

    assert.deepEqual({
        "regular_field-email": "Email",
        "relation-persons-object_competitor": 'Has for competitor / Est compétiteur de',
        "relation-persons-subject_subsidiary": 'Is subsidiary / Est subordonné à',
        "relation-persons-small": 'Is small / Frêle',
        "relation-persons-big": 'Is big / Énorme'
    }, widget.column_titles);

    assert.equal(1, filter.length);
    assert.equal(1, filter_result.length);

    assert.equal('', filter.val());
    assert.equal('', filter_result.text());

    assert.deepEqual({
        'relation-persons-object_competitor': {opacity: 1.0, visible: true},
        'relation-persons-subject_subsidiary': {opacity: 1.0, visible: true},
        'relation-persons-small': {opacity: 1.0, visible: true},
        'relation-persons-big': {opacity: 1.0, visible: true}
    }, this.itemsDisplayStatus(relationships));

    filter.val(term).trigger('propertychange');

    assert.equal(expected.summary, filter_result.text());
    assert.deepEqual(expected.items, this.itemsDisplayStatus(relationships));

    filter.val('').trigger('propertychange');

    assert.equal('', filter_result.text());
    assert.deepEqual({
        'relation-persons-object_competitor': {opacity: 1.0, visible: true},
        'relation-persons-subject_subsidiary': {opacity: 1.0, visible: true},
        'relation-persons-small': {opacity: 1.0, visible: true},
        'relation-persons-big': {opacity: 1.0, visible: true}
    }, this.itemsDisplayStatus(relationships));
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

    assert.equal('regular_field-email,regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    assert.equal(gettext('Preview and order of the %s columns').format(3), element.find('.preview_title').text());

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address"
    }, widget.column_titles);
    assert.deepEqual([
        "regular_field-email",
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    assert.deepEqual({}, widget.underlays);

    element.find('.remove_all_columns').trigger('click');

    assert.equal('', widget.store.val());
    assert.equal(gettext('Preview'), element.find('.preview_title').text());

    assert.deepEqual([], widget.columns);
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

    assert.equal('regular_field-email,regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    assert.equal(gettext('Preview and order of the %s columns').format(3), element.find('.preview_title').text());

    assert.deepEqual({
        "regular_field-email": "Email",
        "regular_field-firstname": "First name",
        "regular_field-lastname": "Last name",
        "regular_field-billing_address": "Toggle underlays",
        "regular_field-billing_address__city": "Toggle underlays — City",
        "regular_field-billing_address__country": "Toggle underlays — Country",
        "regular_field-billing_address__name": "Toggle underlays — Address"
    }, widget.column_titles);
    assert.deepEqual([
        "regular_field-email",
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    assert.deepEqual({}, widget.underlays);

    // unselect 'email' column
    element.find('.preview th[data-column="regular_field-email"] .preview_column_toggle').trigger('click');

    assert.equal('regular_field-lastname,regular_field-billing_address__name', widget.store.val());
    assert.equal(gettext('Preview and order of the %s columns').format(2), element.find('.preview_title').text());

    assert.deepEqual([
        "regular_field-lastname",
        'regular_field-billing_address__name'
    ], widget.columns);

    // unselect 'billing address name' column
    element.find('.preview th[data-column="regular_field-billing_address__name"] .preview_column_toggle').trigger('click');
    assert.equal(gettext('Preview of the column'), element.find('.preview_title').text());

    assert.deepEqual([
        "regular_field-lastname"
    ], widget.columns);
});
}(jQuery));
