/* globals FunctionFaker */
(function($) {

var MOCK_SINGLE_RESPONSE = {
        results: [{
            id: 'ctype.contact',
            label: 'Contacts',
            count: 1,
            results: [{
                url: '/mock/contact/1',
                label: 'Contact A'
            }]
        }]
    };

var MOCK_GROUP_BEST_RESPONSE = {
        best: {
            url: '/mock/contact/1',
            label: 'Contact A'
        },
        results: [{
            id: 'ctype.contact',
            label: 'Contacts',
            count: 2,
            results: [{
                url: '/mock/contact/1',
                label: 'Contact A'
            }, {
                url: '/mock/contact/2',
                label: 'Contact B',
                deleted: true
            }]
        }]
    };

var MOCK_N_GROUPS_BEST_RESPONSE = {
        best: {
            url: '/mock/contact/1',
            label: 'Contact A'
        },
        results: [{
            id: 'ctype.contact',
            label: 'Contacts',
            count: 2,
            results: [{
                url: '/mock/contact/1',
                label: 'Contact A'
            }, {
                url: '/mock/contact/2',
                label: 'Contact B'
            }]
        }, {
            id: 'ctype.organization',
            label: 'Organizations',
            count: 3,
            results: [{
                url: '/mock/organization/1',
                label: 'Organization A'
            }, {
                url: '/mock/organization/2',
                label: 'Organization B'
            }, {
                url: '/mock/organization/3',
                label: 'Organization C'
            }]
        }]
    };

QUnit.module("creme.search.js", new QUnitMixin(QUnitEventMixin,
                                               QUnitAjaxMixin,
                                               QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/search': function(url, data, options) {
                var search = data.value;

                switch (search) {
                    case 'single':
                        return backend.responseJSON(200, MOCK_SINGLE_RESPONSE);
                    case 'group+best':
                        return backend.responseJSON(200, MOCK_GROUP_BEST_RESPONSE);
                    case 'n-group+best':
                        return backend.responseJSON(200, MOCK_N_GROUPS_BEST_RESPONSE);
                    case 'failure':
                        return backend.response(400, 'Invalid search arguments');
                }

                return backend.responseJSON(200, {results: []});
            }
        });
    },

    afterEach: function() {
        $('.glasspane').detach();
    },

    createSearchBoxHtml: function() {
        return (
            '<div class="search-box">' +
                 '<input type="text" placeholder="${placeholder}">' +
                 '<span class="search-box-icon default">' +
                     '<img class="search-icon-loading" title="${loading}" alt="${loading}">' +
                     '<img class="search-icon-default" title="${placeholder}" alt="${placeholder}">' +
                 '</span>' +
                 '<div class="inline-search-results">' +
                     '<div class="search-results-group all-search-results">' +
                         '<span class="search-results-group-title"></span>' +
                         '<ul class="search-results">' +
                              '<li class="search-result"><a href="/mock/advancedsearch">${advanced}</a></li>' +
                         '</ul>' +
                     '</div>' +
                 '</div>' +
            '</div>').template({
                placeholder: gettext('Search'),
                loading: gettext('Loading…'),
                advanced: gettext('Advanced search')
            });
    }
}));

QUnit.test('creme.search.SearchBox', function(assert) {
    var search;

    this.assertRaises(function() {
        search = new creme.search.SearchBox();
    }, Error, 'Error: searchUrl is required');

    this.assertRaises(function() {
        search = new creme.search.SearchBox({
            searchUrl: 'mock/search'
        });
    }, Error, 'Error: advancedSearchUrl is required');

    search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    });

    assert.equal('mock/search', search.searchUrl);
    assert.equal('mock/advancedsearch', search.advancedSearchUrl);
    assert.equal(false, search.isLoading());
    assert.equal(false, search.isBound());
});

QUnit.test('creme.search.SearchBox.bind', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    });

    search.bind(element);
    assert.equal(false, search.isLoading());
    assert.equal(false, search.isOpened());
    assert.equal(true, search.isBound());

    assert.equal(1, search._resultsRoot.length);
    assert.equal(1, search._input.length);
    assert.equal(1, search._icon.length);
    assert.equal(1, search._allResultsGroup.length);
    assert.equal(1, search._allResultsLink.length);

    this.assertRaises(function() {
        search.bind(element);
    }, Error, 'Error: SearchBox is already bound');
});

QUnit.test('creme.search.SearchBox.search (focus => open popover)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    assert.equal(true, search.isBound());

    assert.equal(false, search.isOpened());
    assert.equal(0, element.find('.inline-search-results.showing').length);
    assert.equal(0, $('.glasspane').length);

    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');

    var done = assert.async();

    setTimeout(function() {
        assert.equal(true, search.isOpened());
        assert.equal(1, element.find('.inline-search-results.showing').length);
        assert.equal(1, $('.glasspane').length);
        done();
    }, 150);
});

QUnit.test('creme.search.SearchBox.search (click outside => close popover)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        focusDebounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    assert.equal(true, search.isBound());

    element.find('input[type="text"]').trigger('focus');

    assert.equal(true, search.isOpened());
    assert.equal(1, $('.glasspane').length);

    $('.glasspane').trigger('click');

    assert.equal(false, search.isOpened());
    assert.equal(0, $('.glasspane').length);
});

QUnit.test('creme.search.SearchBox.search (length < default min length)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    assert.equal(3, search.minSearchLength);

    assert.deepEqual([], this.mockBackendUrlCalls('mock/search'));

    var input = search._input;

    input.val('ab').trigger('input');
    assert.deepEqual([], this.mockBackendUrlCalls('mock/search'));

    input.val('abc').trigger('input');
    assert.deepEqual([
        ['GET', {value: 'abc'}]
    ], this.mockBackendUrlCalls('mock/search'));

    input.val('abcd').trigger('input');
    assert.deepEqual([
        ['GET', {value: 'abc'}],
        ['GET', {value: 'abcd'}]
    ], this.mockBackendUrlCalls('mock/search'));

    input.val('a').trigger('input');
    assert.deepEqual([
        ['GET', {value: 'abc'}],
        ['GET', {value: 'abcd'}]
    ], this.mockBackendUrlCalls('mock/search'));
});

QUnit.test('creme.search.SearchBox.search (length < min length)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        minSearchLength: 7,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    assert.equal(7, search.minSearchLength);

    input.val('abcdef').trigger('input');
    assert.deepEqual([], this.mockBackendUrlCalls('mock/search'));

    input.val('abcdefg').trigger('input');
    assert.deepEqual([
        ['GET', {value: 'abcdefg'}]
    ], this.mockBackendUrlCalls('mock/search'));
});

QUnit.test('creme.search.SearchBox.search (no result)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    assert.deepEqual([], this.mockBackendUrlCalls('mock/search'));

    assert.equal(gettext('Advanced search'), element.find('.search-result a').text());
    assert.equal(1, element.find('.search-results-group').length);
    assert.equal(1, element.find('.all-search-results').length);
    assert.equal(0, element.find('.best-results-group').length);
    assert.equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);

    input.val('abc').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'abc'}]
    ], this.mockBackendUrlCalls('mock/search'));

    assert.equal(gettext('No result'), element.find('.search-result a').text());
    assert.equal(1, element.find('.search-results-group').length);
    assert.equal(1, element.find('.all-search-results').length);
    assert.equal(0, element.find('.best-results-group').length);
    assert.equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);
});

QUnit.test('creme.search.SearchBox.search (failure)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    input.val('failure').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'failure'}]
    ], this.mockBackendUrlCalls('mock/search'));

    assert.equal(gettext('Advanced search'), element.find('.search-result a').text());
    assert.equal(1, element.find('.search-results-group').length);
    assert.equal(1, element.find('.all-search-results').length);
    assert.equal(0, element.find('.best-results-group').length);
    assert.equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);
});

QUnit.test('creme.search.SearchBox.search (1 result)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('single').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'single'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    assert.equal(1, all_group.length);
    assert.equal(0, best_group.length);
    assert.equal(1, others_group.length);

    assert.equal(gettext('All results (%s)').format(1), all_group.find('.search-result a').text());

    assert.equal(gettext('Contacts'), others_group.find('.search-results-group-title').text());
    assert.equal(1, others_group.find('.search-result a').length);
    assert.equal(gettext('Contact A'), $(others_group.find('.search-result a').get(0)).text());
});

QUnit.test('creme.search.SearchBox.search (1 result group + best result)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('group+best').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    assert.equal(1, all_group.length);
    assert.equal(1, best_group.length);
    assert.equal(1, others_group.length);

    assert.equal(gettext('All results (%s)').format(2), all_group.find('.search-result a').text());

    assert.equal(gettext('Best result'), best_group.find('.search-results-group-title').text());
    assert.equal(1, best_group.find('.search-result a').length);
    assert.equal(gettext('Contact A'), best_group.find('.search-result a').text());

    assert.equal(gettext('Contacts'), others_group.find('.search-results-group-title').text());
    assert.equal(2, others_group.find('.search-result a').length);

    var contactA = $(others_group.find('.search-result a').get(0));
    assert.equal(gettext('Contact A'), contactA.text());
    assert.equal(contactA.hasClass('is_deleted'), false);

    var contactB = $(others_group.find('.search-result a').get(1));
    assert.equal(gettext('Contact B'), contactB.text());
    assert.equal(contactB.hasClass('is_deleted'), true);
});

QUnit.test('creme.search.SearchBox.search (N result groups + best result)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('n-group+best').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'n-group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    assert.equal(1, all_group.length);
    assert.equal(1, best_group.length);
    assert.equal(2, others_group.length);

    assert.equal(gettext('All results (%s)').format(5), all_group.find('.search-result a').text());

    assert.equal(gettext('Best result'), best_group.find('.search-results-group-title').text());
    assert.equal(1, best_group.find('.search-result a').length);
    assert.equal(gettext('Contact A'), best_group.find('.search-result a').text());

    var contacts_group = $(others_group.get(0));
    var orgas_group = $(others_group.get(1));

    assert.equal(gettext('Contacts'), contacts_group.find('.search-results-group-title').text());
    assert.equal(2, contacts_group.find('.search-result a').length);
    assert.equal(gettext('Contact A'), $(contacts_group.find('.search-result a').get(0)).text());
    assert.equal(gettext('Contact B'), $(contacts_group.find('.search-result a').get(1)).text());

    assert.equal(gettext('Organizations'), orgas_group.find('.search-results-group-title').text());
    assert.equal(3, orgas_group.find('.search-result a').length);
    assert.equal(gettext('Organization A'), $(orgas_group.find('.search-result a').get(0)).text());
    assert.equal(gettext('Organization B'), $(orgas_group.find('.search-result a').get(1)).text());
    assert.equal(gettext('Organization C'), $(orgas_group.find('.search-result a').get(2)).text());
});

QUnit.test('creme.search.SearchBox.search (multiple queries, cancel old ones)', function(assert) {
    var self = this;
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    this.backend.options.delay = 300;

    search._input.val('n-group+best').trigger('input');

    search._input.val('').trigger('input'); // "cancel" search
    search._input.val('group+best').trigger('input');

    search._input.val('').trigger('input'); // "cancel" search
    search._input.val('group+best').trigger('input');

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    assert.equal(1, all_group.length);
    assert.equal(0, best_group.length);
    assert.equal(0, others_group.length);

    var done = assert.async();

    setTimeout(function() {
        assert.deepEqual([
            ['GET', {value: 'n-group+best'}],
            ['GET', {value: 'group+best'}],
            ['GET', {value: 'group+best'}]
        ], self.mockBackendUrlCalls('mock/search'));

        all_group = element.find('.all-search-results');
        best_group = element.find('.best-results-group');
        others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

        assert.equal(1, all_group.length);
        assert.equal(1, best_group.length);
        assert.equal(1, others_group.length);

        done();
    }, 400);
});

QUnit.test('creme.search.SearchBox.keys (enter)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('single').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'single'}]
    ], this.mockBackendUrlCalls('mock/search'));
    assert.deepEqual([], this.mockRedirectCalls());

    search._input.trigger($.Event("keydown", {keyCode: 13}));

    assert.deepEqual([
        '/mock/contact/1'
    ], this.mockRedirectCalls());
});

QUnit.test('creme.search.SearchBox.keys (up/down)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('group+best').trigger('input');

    assert.deepEqual([
        ['GET', {value: 'group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    assert.equal(1, all_group.length);
    assert.equal(1, best_group.length);
    assert.equal(1, others_group.length);

    var best_item = best_group.find('.search-result');
    var a_item = $(others_group.find('.search-result').get(0));
    var b_item = $(others_group.find('.search-result').get(1));

    assert.equal(true, best_item.is('.search-result-selected'));
    assert.equal(false, a_item.is('.search-result-selected'));
    assert.equal(false, b_item.is('.search-result-selected'));

    // key down
    search._input.trigger($.Event("keydown", {keyCode: 40}));
    assert.equal(false, best_item.is('.search-result-selected'));
    assert.equal(true, a_item.is('.search-result-selected'));
    assert.equal(false, b_item.is('.search-result-selected'));

    // key down
    search._input.trigger($.Event("keydown", {keyCode: 40}));
    assert.equal(false, best_item.is('.search-result-selected'));
    assert.equal(false, a_item.is('.search-result-selected'));
    assert.equal(true, b_item.is('.search-result-selected'));

    // key up
    search._input.trigger($.Event("keydown", {keyCode: 38}));
    assert.equal(false, best_item.is('.search-result-selected'));
    assert.equal(true, a_item.is('.search-result-selected'));
    assert.equal(false, b_item.is('.search-result-selected'));
});

QUnit.test('creme.search.SearchBox.keys (escape => close popover)', function(assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        focusDebounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    assert.equal(true, search.isBound());

    element.find('input[type="text"]').trigger('focus');

    assert.equal(true, search.isOpened());
    assert.equal(1, element.find('.inline-search-results.showing').length);
    assert.equal(1, $('.glasspane').length);

    element.find('input[type="text"]').trigger($.Event("keydown", {keyCode: 27}));

    assert.equal(false, search.isOpened());
    assert.equal(0, element.find('.inline-search-results.showing').length);
    assert.equal(0, $('.glasspane').length);
});

QUnit.parameterize('creme.search.SearchBox.search (debounce)', [
    [{
        debounceDelay: 0,
        secondTypingDelay: 100
    }, {
        calls: {
            firstTyping: [['sin']],
            secondTyping: [['sin'], ['sing']]
        }
    }],
    [{
        debounceDelay: 200,
        secondTypingDelay: 100
    }, {
        // The second input 'sing' occurs BEFORE the debounce delay, so 'sin' is ignored
        calls: {
            firstTyping: [],
            secondTyping: [['sing']]
        }
    }],
    [{
        debounceDelay: 100,
        secondTypingDelay: 200
    }, {
        calls: {
            firstTyping: [['sin']],
            secondTyping: [['sin'], ['sing']]
        }
    }]
], function(params, expected, assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: params.debounceDelay,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    });

    var faker = new FunctionFaker();
    search._startSearch = faker.wrap();

    search.bind(element);

    // type 'sin'
    search._input.val('sin').trigger('input');

    // type 'sing' 100ms later
    setTimeout(function() {
        search._input.val('sing').trigger('input');
    }, params.secondTypingDelay);

    var done = assert.async(2);

    // Before first debounce
    setTimeout(function() {
        assert.deepEqual(expected.calls.firstTyping, faker.calls());
        done();
    }, params.debounceDelay + 50);

    // Before second debounce
    setTimeout(function() {
        assert.deepEqual(expected.calls.secondTyping, faker.calls());
        done();
    }, params.secondTypingDelay + params.debounceDelay + 50);
});

QUnit.parameterize('creme.search.SearchBox.search (async)', [
    [{
        backendDelay: 0,
        debounceDelay: 200,
        secondTypingDelay: 100
    }, {
        // The second input 'sing' occurs BEFORE the debounce delay, so 'sin' is ignored
        queries: {
            beforeFirstFetch: [],
            afterFirstFetch: [],
            afterSecondFetch: [
                ['GET', {value: 'sing'}]
            ]
        }
    }],
    [{
        backendDelay: 300,
        debounceDelay: 200,
        secondTypingDelay: 100
    }, {
        // The second input 'sing' occurs BEFORE the debounce delay, so 'sin' is ignored
        queries: {
            beforeFirstFetch: [],
            afterFirstFetch: [],
            afterSecondFetch: [
                ['GET', {value: 'sing'}]
            ]
        }
    }],
    [{
        backendDelay: 0,
        debounceDelay: 100,
        secondTypingDelay: 300
    }, {
        // The second input 'sing' occurs AFTER the debounce delay, so 'sin' is here
        queries: {
            beforeFirstFetch: [],
            afterFirstFetch: [
                ['GET', {value: 'sin'}]
            ],
            afterSecondFetch: [
                ['GET', {value: 'sin'}],
                ['GET', {value: 'sing'}]
            ]
        }
    }],
    [{
        backendDelay: 200,
        debounceDelay: 100,
        secondTypingDelay: 300
    }, {
        // The second input 'sing' occurs AFTER the debounce delay, so 'sin' is here
        queries: {
            beforeFirstFetch: [],
            afterFirstFetch: [
                ['GET', {value: 'sin'}]
            ],
            afterSecondFetch: [
                ['GET', {value: 'sin'}],
                ['GET', {value: 'sing'}]
            ]
        }
    }],
    [{
        backendDelay: 500,
        debounceDelay: 100,
        secondTypingDelay: 200
    }, {
        // The second input 'sing' occurs AFTER the debounce delay, so 'sin' is here
        queries: {
            beforeFirstFetch: [],
            afterFirstFetch: [
                ['GET', {value: 'sin'}]
            ],
            afterSecondFetch: [
                ['GET', {value: 'sin'}],
                ['GET', {value: 'sing'}]
            ]
        }
    }]
], function(params, expected, assert) {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: params.debounceDelay,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    this.backend.options.sync = false;
    this.backend.options.delay = params.backendDelay;

    // search._debugTimestamp = new Date().getTime();

    // type 'sin'
    search._input.val('sin').trigger('input');

    // type 'sing' 100ms later
    setTimeout(function() {
        search._input.val('sing').trigger('input');
    }, params.secondTypingDelay);

    var done = assert.async(3);

    // Before first fetch response
    setTimeout(function() {
        console.log('before first debounce', params.debounceDelay - 50);
        assert.deepEqual(expected.queries.beforeFirstFetch, this.mockBackendUrlCalls('mock/search'));
        done();
    }.bind(this), params.debounceDelay - 50);

    // After first fetch response : debounce + backend
    setTimeout(function() {
        console.log('after first fetch max delay', params.debounceDelay + params.backendDelay + 100);
        assert.deepEqual(expected.queries.afterFirstFetch, this.mockBackendUrlCalls('mock/search'));
        done();
    }.bind(this), params.debounceDelay + params.backendDelay + 50);

    // After second fetch response : second input + debounce + backend
    var secondFetchDelay = params.secondTypingDelay + params.debounceDelay + params.backendDelay + 50;
    setTimeout(function() {
        console.log('after second fetch max delay', secondFetchDelay);
        assert.deepEqual(expected.queries.afterSecondFetch, this.mockBackendUrlCalls('mock/search'));
        done();
    }.bind(this), secondFetchDelay);
});

}(jQuery));
