/* global FunctionFaker */

(function($) {

var S2 = {};

QUnit.module("creme.form.Select2", new QUnitMixin(QUnitAjaxMixin,
                                                  QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/enum': backend.responseJSON(200, [
                {value: 1, label: 'a'},
                {value: 15, label: 'b'},
                {value: 12.5, label: 'c'}
             ]),
            'mock/enum/42': backend.responseJSON(200, [
                {value: 1, label: 'a'},
                {value: 15, label: 'b'},
                {value: 12.5, label: 'c'},
                {value: 42, label: 'd'}
             ]),
            'mock/enum/empty': backend.responseJSON(200, []),
            'mock/create': backend.response(200, (
                '<form action="mock/create">' +
                    '<input type="text" name="title"></input>' +
                    '<input type="submit" class="ui-creme-dialog-action"></input>' +
                '</form>'
            )),
            'mock/create/group': backend.response(200, (
                '<form action="mock/create/group">' +
                    '<input type="text" name="title"></input>' +
                    '<input type="text" name="group"></input>' +
                    '<input type="submit" class="ui-creme-dialog-action"></input>' +
                '</form>'
            )),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/create': function(url, data, options) {
                return backend.responseJSON(200, {
                    value: 99,
                    added: [
                        [99, data.title[0]]
                    ]
                });
            },
            'mock/create/group': function(url, data, options) {
                return backend.responseJSON(200, {
                    value: 99,
                    added: [
                        {value: 99, label: data.title[0], group: data.group[0]}
                    ]
                });
            }
        });

        /* Import synchronously (the 'true' at the end) the Options class of Select2 */
        $.fn.select2.amd.require([
            'select2/utils',
            'select2/options',
            'select2/data/enum'
        ], function(Utils, Options, EnumerableAdapter) {
            S2.Utils = Utils;
            S2.Options = Options;
            S2.EnumerableAdapter = EnumerableAdapter;
        }, undefined, true);
    },

    afterEach: function() {
        $('.select2-hidden-accessible').select2('destroy');
        $('.select2-container').remove();
    },

    createSelect: function(options) {
        options = options || [];

        var select = $('<select></select>').appendTo(this.qunitFixture('field'));
        var add = this.addSelectOption.bind(this);

        options.forEach(function(option) {
            add(select, option);
        });

        return select;
    },

    addSelectOption: function(select, options) {
        var groupOptions = (options.options || []);
        var item;

        if (Object.isEmpty(groupOptions)) {
            item = $('<option value="${value}" ${disabled} ${selected}>${label}</option>'.template({
                value: options.value,
                label: options.label,
                disabled: options.disabled ? 'disabled' : '',
                selected: options.selected ? 'selected' : ''
            }));
        } else {
            var add = this.addSelectOption.bind(this);
            item = $('<optgroup label="${label}"></optgroup>'.template(options));

            groupOptions.forEach(function(option) {
                add(item, option);
            });
        }

        _.pairs(options.attrs || {}).forEach(function(attr) {
            item.attr(attr[0], attr[1]);
        });

        select.append(item);
    }
}));

QUnit.parametrize('creme.form.Select2.localisation', [
    [{}, {
        noResults: gettext('No result'),
        loadingMore: gettext('Loading more results…'),
        errorLoading: gettext('The results could not be loaded.'),
        removeAllItems: gettext('Remove all items'),
        removeItem: gettext('Remove item'),
        search: gettext('Search')
    }],
    [{
        noResultsMsg: 'Rien',
        loadingMoreMsg: 'Ca vient...',
        errorLoadingMsg: 'Ca marche pas',
        removeAllItemsMsg: 'Enleve tout',
        removeItemMsg: 'Enleve',
        searchMsg: 'On cherche'
    }, {
        noResults: 'Rien',
        loadingMore: 'Ca vient...',
        errorLoading: 'Ca marche pas',
        removeAllItems: 'Enleve tout',
        removeItem: 'Enleve',
        search: 'On cherche'
    }]
], function(options, expected, assert) {
    var select2 = new creme.form.Select2($('select'));
    var locale = select2.localisation(options);

    equal(locale.noResults(), expected.noResults);
    equal(locale.loadingMore(), expected.loadingMore);
    equal(locale.errorLoading(), expected.errorLoading);
    equal(locale.removeAllItems(), expected.removeAllItems);
    equal(locale.removeItem(), expected.removeItem);
    equal(locale.search(), expected.search);
});

QUnit.parametrize('creme.form.Select2.localisation (inputTooLong)', [
    [{}, {input: 'abcd', maximum: 3}, ngettext('Please delete %d character', 'Please delete %d characters', 1).format(1)],
    [{}, {input: 'abcde', maximum: 3}, ngettext('Please delete %d character', 'Please delete %d characters', 2).format(2)],
    [{inputTooLongMsg: function() { return 'Trop long !'; }}, {input: 'abcde', maximum: 3}, 'Trop long !']
], function(options, args, expected, assert) {
    var select2 = new creme.form.Select2($('select'));
    var locale = select2.localisation(options);
    equal(locale.inputTooLong(args), expected);
});

QUnit.parametrize('creme.form.Select2.localisation (inputTooShort)', [
    [{}, {input: 'ab', minimum: 3}, ngettext('Please enter %d or more character', 'Please enter %d or more characters', 1).format(1)],
    [{}, {input: 'a', minimum: 3}, ngettext('Please enter %d or more character', 'Please enter %d or more characters', 2).format(2)],
    [{inputTooShortMsg: function() { return 'Trop court !'; }}, {input: 'a', minimum: 3}, 'Trop court !']
], function(options, args, expected, assert) {
    var select2 = new creme.form.Select2($('select'));
    var locale = select2.localisation(options);
    equal(locale.inputTooShort(args), expected);
});

QUnit.parametrize('creme.form.Select2.localisation (maximumSelectedMsg)', [
    [{}, {maximum: 1}, ngettext('You can only select %d item', 'You can only select %d items', 1).format(1)],
    [{}, {maximum: 3}, ngettext('You can only select %d item', 'You can only select %d items', 3).format(3)],
    [{maximumSelectedMsg: function() { return 'Trop de selections !'; }}, {maximum: 3}, 'Trop de selections !']
], function(options, args, expected, assert) {
    var select2 = new creme.form.Select2($('select'));
    var locale = select2.localisation(options);
    equal(locale.maximumSelected(args), expected);
});

QUnit.test('creme.form.Select2 (empty)', function(assert) {
    var select = this.createSelect();

    equal(false, select.is('.select2-hidden-accessible'));

    var select2 = new creme.form.Select2(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(select, select2.element);
});

QUnit.test('creme.form.Select2 (single)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select);

    deepEqual({
        multiple: false,
        sortable: false
    }, select2.options());

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.parametrize('creme.form.Select2 (single, group)', [
    [false, 1, 'Item A'],
    [false, 2, 'Item AB'],
    [true, 1, 'Item A'],
    [true, 2, 'Group A − Item AB']
], function(showGroup, value, expected, assert) {
    var select = $(
        '<select>' +
            '<option value="1">Item A</option>' +
            '<optgroup label="Group A">' +
                '<option value="2">Item AB</option>' +
            '</optgroup>' +
        '</select>'
    ).appendTo(this.qunitFixture('field'));

    var select2 = new creme.form.Select2(select, {
        selectionShowGroup: showGroup
    });

    deepEqual({
        multiple: false,
        selectionShowGroup: showGroup,
        sortable: false
    }, select2.options());

    select.val(value).trigger('change');

    equal(expected, select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.test('creme.form.Select2 (multiple)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A', selected: true}
    ]);

    select.attr('multiple', '');
    select.val([5, 1]);

    var select2 = new creme.form.Select2(select, {multiple: true});

    deepEqual({
        multiple: true,
        sortable: false
    }, select2.options());

    equal(2, select.next('.select2').find('.select2-selection__choice').length);
    equal(false, select.parent().is('.ui-sortable'), 'is NOT sortable'); // not sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2 (multiple, sortable)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A', selected: true}
    ]);

    select.attr('multiple', '');
    select.val([5, 1]);

    var select2 = new creme.form.Select2(select, {multiple: true, sortable: true});

    deepEqual({
        multiple: true,
        sortable: true
    }, select2.options());

    equal(2, select.next('.select2').find('.select2-selection__choice').length);
    equal(true, select.parent().is('.ui-sortable'), 'is sortable'); // sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);
});

QUnit.parametrize('creme.form.Select2 (search + toggle create)', [
    ['', false],
    ['Item E', false],
    ['Item', true]
], function(term, expected, assert) {
    var select = this.createSelect([
        {value: 5, label: 'Item E'},
        {value: 1, label: 'Item A'}
    ]);

    var url = 'mock/create';
    select.attr('data-create-url', url);

    var select2 = new creme.form.Select2(select);

    deepEqual({
        createURL: url,
        multiple: false,
        sortable: false
    }, select2.options());

    select.select2('open');

    $('.select2-search__field').val(term).trigger('input');

    if (expected) {
        equal(1, $('.select2-results__create-title').size());
        equal(
            gettext('Create new item «%s»').format(term),
            $('.select2-results__create-title').text()
        );
    } else {
        equal(0, $('.select2-results__create-title').size());
    }
});

QUnit.test('creme.form.Select2 (create popup, submit)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'Item E'},
        {value: 1, label: 'Item A'}
    ]);

    var select2 = new creme.form.Select2(select, {
        createURL: 'mock/create'
    });

    deepEqual({
        createURL: 'mock/create',
        multiple: false,
        sortable: false
    }, select2.options());

    select.select2('open');

    var term = 'Item C';

    $('.select2-search__field').val(term).trigger('input');

    equal(1, $('.select2-results__create-title').size());
    equal(
        gettext('Create new item «%s»').format(term),
        $('.select2-results__create-title').text()
    );

    this.assertClosedDialog();

    $('.select2-results__create').trigger('click');

    var dialog = this.assertOpenedDialog();
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/create'));

    equal(term, dialog.find('[name="title"]').val());

    // Submit the new item
    this.findDialogButtonsByLabel(gettext('Save'), dialog).trigger('click');

    deepEqual([
        ['GET', {}],
        ['POST', {title: [term]}]
    ], this.mockBackendUrlCalls('mock/create'));

    this.assertClosedDialog();

    // New item is added
    deepEqual([
        {value: '5', label: 'Item E'},
        {value: '1', label: 'Item A'},
        {value: '99', label: term}
    ], select.find('option').map(function() {
        return {
            value: $(this).attr('value'),
            label: $(this).text()
        };
    }).get());
});

QUnit.parametrize('creme.form.Select2 (create popup, submit, group)', [
    [
        {title: 'Item C'},
        [
            {id: '1', text: 'Item A'},
            {
                text: 'Group A',
                children: [
                    {id: '2', text: 'Item AB'}
                ]
            },
            {id: '99', text: 'Item C'}
        ]
    ],
    [
        {title: 'Item D', group: 'Group D'},
        [
            {id: '1', text: 'Item A'},
            {
                text: 'Group A',
                children: [
                    {id: '2', text: 'Item AB'}
                ]
            },
            {
                text: 'Group D',
                children: [
                    {id: '99', text: 'Item D'}
                ]
            }
        ]
    ], [
        {title: 'Item AF', group: 'Group A'},
        [
            {id: '1', text: 'Item A'},
            {
                text: 'Group A',
                children: [
                    {id: '2', text: 'Item AB'},
                    {id: '99', text: 'Item AF'}
                ]
            }
        ]
    ]
], function(formData, expected, assert) {
    var select = $(
        '<select>' +
            '<option value="1">Item A</option>' +
            '<optgroup label="Group A">' +
                '<option value="2">Item AB</option>' +
            '</optgroup>' +
        '</select>'
    ).appendTo(this.qunitFixture('field'));

    var select2 = new creme.form.Select2(select, {
        createURL: 'mock/create/group'
    });

    deepEqual({
        createURL: 'mock/create/group',
        multiple: false,
        sortable: false
    }, select2.options());

    select.select2('open');

    var term = formData.title;

    $('.select2-search__field').val(term).trigger('input');

    equal(1, $('.select2-results__create-title').size());
    equal(
        gettext('Create new item «%s»').format(term),
        $('.select2-results__create-title').text()
    );

    this.assertClosedDialog();

    $('.select2-results__create').trigger('click');

    var dialog = this.assertOpenedDialog();
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/create/group'));

    dialog.find('[name="title"]').val(formData.title);
    dialog.find('[name="group"]').val(formData.group);

    // Submit the new item
    this.findDialogButtonsByLabel(gettext('Save'), dialog).trigger('click');

    deepEqual([
        ['GET', {}],
        ['POST', {title: [term], group: [formData.group || '']}]
    ], this.mockBackendUrlCalls('mock/create/group'));

    this.assertClosedDialog();

    // New item is added
    deepEqual(expected, select.children().map(function() {
        if ($(this).is('option')) {
            return {
                id: $(this).attr('value'),
                text: $(this).text()
            };
        } else {
            return {
                text: $(this).attr('label'),
                children: $(this).find('option').map(function() {
                    return {
                        id: $(this).attr('value'),
                        text: $(this).text()
                    };
                }).get()
            };
        }
    }).get());
});

QUnit.test('creme.form.Select2 (create popup, cancel)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'Item E'},
        {value: 1, label: 'Item A'}
    ]);

    var select2 = new creme.form.Select2(select, {
        createURL: 'mock/create'
    });

    deepEqual({
        createURL: 'mock/create',
        multiple: false,
        sortable: false
    }, select2.options());

    select.select2('open');

    $('.select2-search__field').val('Item C').trigger('input');

    equal(1, $('.select2-results__create-title').size());
    equal(
        gettext('Create new item «%s»').format('Item C'),
        $('.select2-results__create-title').text()
    );

    this.assertClosedDialog();

    $('.select2-results__create').trigger('click');

    var dialog = this.assertOpenedDialog();
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/create'));
    equal('Item C', dialog.find('[name="title"]').val());

    // Cancel the creation
    this.findDialogButtonsByLabel(gettext('Cancel'), dialog).trigger('click');

    this.assertClosedDialog();

    // Nothing changes
    deepEqual([['GET', {}]], this.mockBackendUrlCalls('mock/create'));
    deepEqual([
        {value: '5', label: 'Item E'},
        {value: '1', label: 'Item A'}
    ], select.find('option').map(function() {
        return {
            value: $(this).attr('value'),
            label: $(this).text()
        };
    }).get());
});


QUnit.test('creme.form.Select2 (enum)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 8, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select, {
        enumURL: 'mock/enum',
        enumDebounce: 0
    });

    deepEqual({
        multiple: false,
        sortable: false,
        enumURL: 'mock/enum',
        enumDebounce: 0
    }, select2.options());

    equal(5, select.val());

    select.select2('open');

    deepEqual([['GET', {limit: 51}]], this.mockBackendUrlCalls('mock/enum'));

    // <select> state is still the same, loaded entries are only in the dropdown
    equal(5, select.val());
    deepEqual([
        {value: '5', label: 'E'},
        {value: '8', label: 'A'}
    ], select.find('option').map(function() {
        return {
            value: $(this).attr('value'),
            label: $(this).text()
        };
    }).get());

    equal(3, $('.select2-dropdown .select2-results__option').length);

    // select an item from the dropdown
    $('.select2-dropdown .select2-results__option:first').trigger('mouseup');

    // the item is selected and appended to the <select> if needed
    equal(1, select.val());
    deepEqual([
        {value: '5', label: 'E'},
        {value: '8', label: 'A'},
        {value: '1', label: 'a'}
    ], select.find('option').map(function() {
        return {
            value: $(this).attr('value'),
            label: $(this).text()
        };
    }).get());

    // closed popup
    equal(0, $('.select2-dropdown').length);
});

QUnit.test('creme.form.Select2 (enum, debounce)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 8, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select, {
        enumURL: 'mock/enum',
        enumDebounce: 100
    });

    deepEqual({
        multiple: false,
        sortable: false,
        enumURL: 'mock/enum',
        enumDebounce: 100
    }, select2.options());

    equal(5, select.val());

    deepEqual([], this.mockBackendUrlCalls('mock/enum'));
    equal(0, $('.select2-dropdown .select2-results__option').length);

    select.select2('open');

    stop(1);

    deepEqual([], this.mockBackendUrlCalls('mock/enum'));
    equal(1, $('.select2-dropdown .select2-results__option').length);
    equal(gettext('Searching…'), $('.select2-dropdown .select2-results__option').text());

    setTimeout(function() {
        deepEqual([['GET', {limit: 51}]], this.mockBackendUrlCalls('mock/enum'));

        deepEqual([
            'a', 'b', 'c'
        ], $('.select2-dropdown .select2-results__option').map(function() {
            return $(this).text();
        }).get().sort());

        start();
    }.bind(this), 200);
});

QUnit.test('creme.form.Select2 (enum, pinned)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 8, label: 'Pinned', attrs: {'data-pinned': ''}}
    ]);

    var select2 = new creme.form.Select2(select, {
        enumURL: 'mock/enum',
        enumDebounce: 0
    });

    deepEqual({
        multiple: false,
        sortable: false,
        enumURL: 'mock/enum',
        enumDebounce: 0
    }, select2.options());

    equal(5, select.val());

    select.select2('open');

    deepEqual([['GET', {limit: 51}]], this.mockBackendUrlCalls('mock/enum'));
    deepEqual([
        'Pinned', 'a', 'b', 'c'
    ], $('.select2-dropdown .select2-results__option').map(function() {
        return $(this).text();
    }).get().sort());

    equal(1, $('.select2-dropdown .select2-results__option .select2-results__pin').length);
});

QUnit.parametrize('creme.form.Select2 (enum + more)', [
    [50, false],
    [4, false],
    [3, true]
], function(limit, expected, assert) {
    var select = this.createSelect().appendTo(this.qunitFixture('field'));
    var select2 = new creme.form.Select2(select, {  // eslint-disable-line no-unused-vars
        enumURL: 'mock/enum',
        enumDebounce: 0,
        enumLimit: limit
    });

    var responseData = [
        {value: 1, label: 'a'},
        {value: 2, label: 'b'},
        {value: 3, label: 'c'},
        {value: 4, label: 'd'}
    ];

    // set custom response
    this.setMockBackendGET({
        'mock/enum': this.backend.responseJSON(200, responseData)
    });

    select.select2('open');

    equal(Math.min(limit, responseData.length), $('.select2-dropdown .select2-results__option').length);
    equal(expected, $('.select2-dropdown .select2-results__more').length > 0);
});

QUnit.test('creme.form.Select2 (enum + more + reload)', function(assert) {
    var select = this.createSelect().appendTo(this.qunitFixture('field'));
    var select2 = new creme.form.Select2(select, {  // eslint-disable-line no-unused-vars
        enumURL: 'mock/enum',
        enumDebounce: 0,
        enumLimit: 3
    });

    var responseData = [
        {value: 1, label: 'a'},
        {value: 2, label: 'b'},
        {value: 3, label: 'c'},
        {value: 4, label: 'd'},
        {value: 5, label: 'e'},
        {value: 6, label: 'f'},
        {value: 7, label: 'g'},
        {value: 8, label: 'h'},
        {value: 9, label: 'i'},
        {value: 10, label: 'j'},
        {value: 11, label: 'k'}
    ];

    // set custom response
    this.setMockBackendGET({
        'mock/enum': this.backend.responseJSON(200, responseData)
    });

    select.select2('open');

    equal(3, $('.select2-dropdown .select2-results__option').length);
    equal(1, $('.select2-dropdown .select2-results__more').length);

    $('.select2-dropdown .select2-results__more').trigger('click');

    equal(6, $('.select2-dropdown .select2-results__option').length);
    equal(1, $('.select2-dropdown .select2-results__more').length);

    $('.select2-dropdown .select2-results__more').trigger('click');

    equal(9, $('.select2-dropdown .select2-results__option').length);
    equal(1, $('.select2-dropdown .select2-results__more').length);

    $('.select2-dropdown .select2-results__more').trigger('click');

    // all options are now displayed
    equal(11, $('.select2-dropdown .select2-results__option').length);
    equal(0, $('.select2-dropdown .select2-results__more').length);
});

QUnit.test('creme.form.Select2.refresh', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select.select2('close');

    this.addSelectOption(select, {value: 8, label: 'G'});
    this.addSelectOption(select, {value: 2, label: 'B', selected: true});
    this.addSelectOption(select, {value: 3, label: 'C'});

    select2.refresh();

    equal('B', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');

    deepEqual([
        {text: 'E', role: 'option', selected: false},
        {text: 'A', role: 'option', selected: false},
        {text: 'G', role: 'option', selected: false},
        {text: 'B', role: 'option', selected: true},
        {text: 'C', role: 'option', selected: false}
    ], $('.select2-dropdown .select2-results__option').map(function() {
        return {
            text: $(this).text(),
            role: $(this).attr('role'),
            selected: $(this).attr('aria-selected') === 'true'
        };
    }).get());
});

QUnit.test('creme.form.Select2.refresh (group)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {
            label: 'Group I',
            options: [
                {value: 1, label: 'A'}
            ]
        }
    ]);

    var select2 = new creme.form.Select2(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');

    deepEqual([
        {text: 'E', role: 'option', selected: true},
        {text: 'Group I', role: 'group', selected: false},
        {text: 'A', role: 'option', selected: false}
    ], $('.select2-dropdown .select2-results__option').map(function() {
        return {
            text: $(this).find('> strong').html() || $(this).text(),
            role: $(this).attr('role'),
            selected: $(this).attr('aria-selected') === 'true'
        };
    }).get());

    select.select2('close');

    this.addSelectOption(select.find('optgroup'), {value: 8, label: 'G'});
    this.addSelectOption(select.find('optgroup'), {value: 2, label: 'B', selected: true});
    this.addSelectOption(select, {
        label: 'Group II',
        options: [{value: 3, label: 'C'}]
    });

    select2.refresh();

    equal('B', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');

    deepEqual([
        {text: 'E', role: 'option', selected: false},
        {text: 'Group I', role: 'group', selected: false},
        {text: 'A', role: 'option', selected: false},
        {text: 'G', role: 'option', selected: false},
        {text: 'B', role: 'option', selected: true},
        {text: 'Group II', role: 'group', selected: false},
        {text: 'C', role: 'option', selected: false}
    ], $('.select2-dropdown .select2-results__option').map(function() {
        return {
            text: $(this).find('> strong').html() || $(this).text(),
            role: $(this).attr('role'),
            selected: $(this).attr('aria-selected') === 'true'
        };
    }).get());
});

QUnit.test('creme.form.Select2.refresh (replace)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select.select2('close');

    select.find('option').remove();
    this.addSelectOption(select, {value: 8, label: 'G'});
    this.addSelectOption(select, {value: 2, label: 'B', selected: true});
    this.addSelectOption(select, {value: 3, label: 'C'});

    select2.refresh();

    equal('B', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(3, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2.destroy', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(select, select2.element);
    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select2.destroy();

    equal(false, select.is('.select2-hidden-accessible'));
    equal(undefined, select2.element);
    equal('', select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.test('creme.form.Select2.destroy (sortable)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    select.attr('multiple', '');
    select.val([1, 5]);

    var select2 = new creme.form.Select2(select, {multiple: true, sortable: true});

    equal(true, select.is('.select2-hidden-accessible'));
    equal(select, select2.element);
    equal(true, select.parent().is('.ui-sortable')); // sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select2.destroy();

    equal(false, select.is('.select2-hidden-accessible'));
    equal(undefined, select2.element);
    equal(0, $('.select2-dropdown .select2-results__option').length);
    equal(false, select.parent().is('.ui-sortable')); // sortable
});

QUnit.test('creme.form.Select2.destroy (already deactivated)', function(assert) {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]).appendTo(this.qunitFixture('field'));
    var select2 = new creme.form.Select2(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select2.destroy();
    select2.destroy();
    select2.destroy();

    equal(false, select.is('.select2-hidden-accessible'));
    equal('', select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.parametrize('creme.Select2EnumerableAdapter (options)', [
    [{}, {debounce: 100, limit: 50, cache: false}],
    [{'enum': {url: 'mock/enum', limit: 157}}, {url: 'mock/enum', debounce: 100, limit: 157, cache: false}],
    [{'enum': {url: 'mock/enum', cache: true, debounce: 0}}, {url: 'mock/enum', debounce: 0, limit: 50, cache: true}]
], function(options, expected, assert) {
    var select = this.createSelect().appendTo(this.qunitFixture('field'));
    var adapter = new S2.EnumerableAdapter(select, new S2.Options(options));

    deepEqual(expected, adapter.enumOptions);
});

QUnit.parametrize('creme.Select2EnumerableAdapter (query)', [false, true], [
    [
        {
            term: 'test',
            limit: 100,
            url: 'mock/enum'
        },
        {
            query: {
                limit: 101,
                term: 'test'
            },
            callbackCalls: [
                [
                    {
                        more: false,
                        results: [
                            {id: 1, text: 'a', disabled: false, selected: false},
                            {id: 15, text: 'b', disabled: false, selected: false},
                            {id: 12.5, text: 'c', disabled: false, selected: false}
                        ]
                    }
                ]
            ]
        }
    ],
    [
        {
            term: 'test',
            limit: 1,
            url: 'mock/enum'
        },
        {
            query: {
                limit: 2,
                term: 'test'
            },
            callbackCalls: [
                [
                    {
                        more: true,
                        results: [
                            {id: 1, text: 'a', disabled: false, selected: false}
                        ]
                    }
                ]
            ]
        }
    ],
    [
        {
            term: 'test',
            limit: 100,
            url: 'mock/error'
        },
        {
            query: {
                limit: 101,
                term: 'test'
            },
            callbackCalls: []
        }
    ]
], function(cache, params, expected, assert) {
    var select = this.createSelect().appendTo(this.qunitFixture('field'));
    var callback = new FunctionFaker();
    var adapter = new S2.EnumerableAdapter(select, new S2.Options({
        'enum': {
            url: params.url,
            debounce: 0,
            limit: params.limit,
            cache: cache
        }
    }));

    deepEqual([], this.mockBackendUrlCalls(params.url));
    deepEqual([], callback.calls());

    // ignore events triggered by the adapter
    this.withFakeMethod({instance: adapter, method: 'trigger'}, function(faker) {
        adapter.query(params, callback.wrap());
    });

    deepEqual([['GET', expected.query]], this.mockBackendUrlCalls(params.url));
    deepEqual(expected.callbackCalls, callback.calls());
});

QUnit.parametrize('creme.Select2EnumerableAdapter (query + groups)', [
    [
        [
            {value: 1, label: 'I.a', group: 'Group I'},
            {value: 2, label: 'I.b', group: 'Group I'}
        ],
        {
            more: false,
            results: [
                {
                    text: 'Group I',
                    children: [
                        {id: 1, text: 'I.a', group: 'Group I', disabled: false, selected: false},
                        {id: 2, text: 'I.b', group: 'Group I', disabled: false, selected: false}
                    ]
                }
            ]
        }
    ],
    [
        [
            {value: 1, label: 'I.a', group: 'Group I'},
            {value: 2, label: 'I.b', group: 'Group I'},
            {value: 3, label: 'II.c', group: 'Group II'},
            {value: 4, label: 'II.d', group: 'Group II'},
            {value: 5, label: 'III.e', group: 'Group III'},
            {value: 6, label: 'I.f', group: 'Group I'},
            {value: 7, label: 'g'},
            {value: 8, label: 'h'}
        ],
        {
            more: true,
            results: [
                {id: 7, text: 'g', disabled: false, selected: false},
                {id: 8, text: 'h', disabled: false, selected: false},
                {
                    text: 'Group I',
                    children: [
                        {id: 1, text: 'I.a', group: 'Group I', disabled: false, selected: false},
                        {id: 2, text: 'I.b', group: 'Group I', disabled: false, selected: false},
                        {id: 6, text: 'I.f', group: 'Group I', disabled: false, selected: false}
                    ]
                },
                {
                    text: 'Group II',
                    children: [
                        {id: 3, text: 'II.c', group: 'Group II', disabled: false, selected: false},
                        {id: 4, text: 'II.d', group: 'Group II', disabled: false, selected: false}
                    ]
                },
                {
                    text: 'Group III',
                    children: [
                        {id: 5, text: 'III.e', group: 'Group III', disabled: false, selected: false}
                    ]
                }
            ]
        }
    ]
], function(responseData, expected, assert) {
    var select = this.createSelect().appendTo(this.qunitFixture('field'));
    var callback = new FunctionFaker();
    var adapter = new S2.EnumerableAdapter(select, new S2.Options({
        'enum': {
            url: 'mock/enum/groups',
            debounce: 0
        }
    }));

    // set custom response
    this.setMockBackendGET({
        'mock/enum/groups': this.backend.responseJSON(200, responseData)
    });

    // ignore events triggered by the adapter
    this.withFakeMethod({instance: adapter, method: 'trigger'}, function(faker) {
        adapter.query({term: '', limit: 6}, callback.wrap());
    });

    equal(1, callback.calls().length);
    deepEqual(expected, callback.calls()[0][0]);
});

}(jQuery));
