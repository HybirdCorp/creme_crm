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

QUnit.test('creme.search.SearchBox', function() {
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

    equal('mock/search', search.searchUrl);
    equal('mock/advancedsearch', search.advancedSearchUrl);
    equal(false, search.isLoading());
    equal(false, search.isBound());
});

QUnit.test('creme.search.SearchBox.bind', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    });

    search.bind(element);
    equal(false, search.isLoading());
    equal(false, search.isOpened());
    equal(true, search.isBound());

    equal(1, search._resultsRoot.length);
    equal(1, search._input.length);
    equal(1, search._icon.length);
    equal(1, search._allResultsGroup.length);
    equal(1, search._allResultsLink.length);

    this.assertRaises(function() {
        search.bind(element);
    }, Error, 'Error: SearchBox is already bound');
});

QUnit.test('creme.search.SearchBox.search (focus => open popover)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    equal(true, search.isBound());

    equal(false, search.isOpened());
    equal(0, element.find('.inline-search-results.showing').length);
    equal(0, $('.glasspane').length);

    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');
    element.find('input[type="text"]').trigger('focus');

    stop(1);

    setTimeout(function() {
        equal(true, search.isOpened());
        equal(1, element.find('.inline-search-results.showing').length);
        equal(1, $('.glasspane').length);
        start();
    }, 150);
});

QUnit.test('creme.search.SearchBox.search (click outside => close popover)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    equal(true, search.isBound());

    element.find('input[type="text"]').trigger('focus');

    stop(2);

    setTimeout(function() {
        equal(true, search.isOpened());
        equal(1, element.find('.inline-search-results.showing').length);
        equal(1, $('.glasspane').length);
        start();

        $('.glasspane').trigger('click');

        setTimeout(function() {
            equal(false, search.isOpened());
            equal(0, element.find('.inline-search-results.showing').length);
            equal(0, $('.glasspane').length);
            start();
        }, 100);
    }, 100);
});

QUnit.test('creme.search.SearchBox.search (length < default min length)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    equal(3, search.minSearchLength);

    deepEqual([], this.mockBackendUrlCalls('mock/search'));

    var input = search._input;

    input.val('ab').trigger('input');
    deepEqual([], this.mockBackendUrlCalls('mock/search'));

    input.val('abc').trigger('input');
    deepEqual([
        ['GET', {value: 'abc'}]
    ], this.mockBackendUrlCalls('mock/search'));

    input.val('abcd').trigger('input');
    deepEqual([
        ['GET', {value: 'abc'}],
        ['GET', {value: 'abcd'}]
    ], this.mockBackendUrlCalls('mock/search'));

    input.val('a').trigger('input');
    deepEqual([
        ['GET', {value: 'abc'}],
        ['GET', {value: 'abcd'}]
    ], this.mockBackendUrlCalls('mock/search'));
});

QUnit.test('creme.search.SearchBox.search (length < min length)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        minSearchLength: 7,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    equal(7, search.minSearchLength);

    input.val('abcdef').trigger('input');
    deepEqual([], this.mockBackendUrlCalls('mock/search'));

    input.val('abcdefg').trigger('input');
    deepEqual([
        ['GET', {value: 'abcdefg'}]
    ], this.mockBackendUrlCalls('mock/search'));
});

QUnit.test('creme.search.SearchBox.search (no result)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    deepEqual([], this.mockBackendUrlCalls('mock/search'));

    equal(gettext('Advanced search'), element.find('.search-result a').text());
    equal(1, element.find('.search-results-group').length);
    equal(1, element.find('.all-search-results').length);
    equal(0, element.find('.best-results-group').length);
    equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);

    input.val('abc').trigger('input');

    deepEqual([
        ['GET', {value: 'abc'}]
    ], this.mockBackendUrlCalls('mock/search'));

    equal(gettext('No result'), element.find('.search-result a').text());
    equal(1, element.find('.search-results-group').length);
    equal(1, element.find('.all-search-results').length);
    equal(0, element.find('.best-results-group').length);
    equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);
});

QUnit.test('creme.search.SearchBox.search (failure)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    var input = search._input;

    input.val('failure').trigger('input');

    deepEqual([
        ['GET', {value: 'failure'}]
    ], this.mockBackendUrlCalls('mock/search'));

    equal(gettext('Advanced search'), element.find('.search-result a').text());
    equal(1, element.find('.search-results-group').length);
    equal(1, element.find('.all-search-results').length);
    equal(0, element.find('.best-results-group').length);
    equal(0, element.find('.search-results-group:not(.all-search-results):not(.best-results-group)').length);
});

QUnit.test('creme.search.SearchBox.search (1 result)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('single').trigger('input');

    deepEqual([
        ['GET', {value: 'single'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    equal(1, all_group.length);
    equal(0, best_group.length);
    equal(1, others_group.length);

    equal(gettext('All results (%s)').format(1), all_group.find('.search-result a').text());

    equal(gettext('Contacts'), others_group.find('.search-results-group-title').text());
    equal(1, others_group.find('.search-result a').length);
    equal(gettext('Contact A'), $(others_group.find('.search-result a').get(0)).text());
});

QUnit.test('creme.search.SearchBox.search (1 result group + best result)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('group+best').trigger('input');

    deepEqual([
        ['GET', {value: 'group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    equal(1, all_group.length);
    equal(1, best_group.length);
    equal(1, others_group.length);

    equal(gettext('All results (%s)').format(2), all_group.find('.search-result a').text());

    equal(gettext('Best result'), best_group.find('.search-results-group-title').text());
    equal(1, best_group.find('.search-result a').length);
    equal(gettext('Contact A'), best_group.find('.search-result a').text());

    equal(gettext('Contacts'), others_group.find('.search-results-group-title').text());
    equal(2, others_group.find('.search-result a').length);

    var contactA = $(others_group.find('.search-result a').get(0));
    equal(gettext('Contact A'), contactA.text());
    equal(contactA.hasClass('is_deleted'), false);

    var contactB = $(others_group.find('.search-result a').get(1));
    equal(gettext('Contact B'), contactB.text());
    equal(contactB.hasClass('is_deleted'), true);
});

QUnit.test('creme.search.SearchBox.search (N result groups + best result)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('n-group+best').trigger('input');

    deepEqual([
        ['GET', {value: 'n-group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    equal(1, all_group.length);
    equal(1, best_group.length);
    equal(2, others_group.length);

    equal(gettext('All results (%s)').format(5), all_group.find('.search-result a').text());

    equal(gettext('Best result'), best_group.find('.search-results-group-title').text());
    equal(1, best_group.find('.search-result a').length);
    equal(gettext('Contact A'), best_group.find('.search-result a').text());

    var contacts_group = $(others_group.get(0));
    var orgas_group = $(others_group.get(1));

    equal(gettext('Contacts'), contacts_group.find('.search-results-group-title').text());
    equal(2, contacts_group.find('.search-result a').length);
    equal(gettext('Contact A'), $(contacts_group.find('.search-result a').get(0)).text());
    equal(gettext('Contact B'), $(contacts_group.find('.search-result a').get(1)).text());

    equal(gettext('Organizations'), orgas_group.find('.search-results-group-title').text());
    equal(3, orgas_group.find('.search-result a').length);
    equal(gettext('Organization A'), $(orgas_group.find('.search-result a').get(0)).text());
    equal(gettext('Organization B'), $(orgas_group.find('.search-result a').get(1)).text());
    equal(gettext('Organization C'), $(orgas_group.find('.search-result a').get(2)).text());
});

QUnit.test('creme.search.SearchBox.search (multiple queries, cancel old ones)', function() {
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

    equal(1, all_group.length);
    equal(0, best_group.length);
    equal(0, others_group.length);

    stop(1);

    setTimeout(function() {
        deepEqual([
            ['GET', {value: 'n-group+best'}],
            ['GET', {value: 'group+best'}],
            ['GET', {value: 'group+best'}]
        ], self.mockBackendUrlCalls('mock/search'));

        all_group = element.find('.all-search-results');
        best_group = element.find('.best-results-group');
        others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

        equal(1, all_group.length);
        equal(1, best_group.length);
        equal(1, others_group.length);

        start();
    }, 400);
});

QUnit.test('creme.search.SearchBox.keys (enter)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('single').trigger('input');

    deepEqual([
        ['GET', {value: 'single'}]
    ], this.mockBackendUrlCalls('mock/search'));
    deepEqual([], this.mockRedirectCalls());

    search._input.trigger($.Event("keydown", {keyCode: 13}));

    deepEqual([
        '/mock/contact/1'
    ], this.mockRedirectCalls());
});

QUnit.test('creme.search.SearchBox.keys (up/down)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        debounceDelay: 0,
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    search._input.val('group+best').trigger('input');

    deepEqual([
        ['GET', {value: 'group+best'}]
    ], this.mockBackendUrlCalls('mock/search'));

    var all_group = element.find('.all-search-results');
    var best_group = element.find('.best-results-group');
    var others_group = element.find('.search-results-group:not(.all-search-results):not(.best-results-group)');

    equal(1, all_group.length);
    equal(1, best_group.length);
    equal(1, others_group.length);

    var best_item = best_group.find('.search-result');
    var a_item = $(others_group.find('.search-result').get(0));
    var b_item = $(others_group.find('.search-result').get(1));

    equal(true, best_item.is('.search-result-selected'));
    equal(false, a_item.is('.search-result-selected'));
    equal(false, b_item.is('.search-result-selected'));

    // key down
    search._input.trigger($.Event("keydown", {keyCode: 40}));
    equal(false, best_item.is('.search-result-selected'));
    equal(true, a_item.is('.search-result-selected'));
    equal(false, b_item.is('.search-result-selected'));

    // key down
    search._input.trigger($.Event("keydown", {keyCode: 40}));
    equal(false, best_item.is('.search-result-selected'));
    equal(false, a_item.is('.search-result-selected'));
    equal(true, b_item.is('.search-result-selected'));

    // key up
    search._input.trigger($.Event("keydown", {keyCode: 38}));
    equal(false, best_item.is('.search-result-selected'));
    equal(true, a_item.is('.search-result-selected'));
    equal(false, b_item.is('.search-result-selected'));
});

QUnit.test('creme.search.SearchBox.keys (escape => close popover)', function() {
    var element = $(this.createSearchBoxHtml()).appendTo(this.qunitFixture());
    var search = new creme.search.SearchBox({
        searchUrl: 'mock/search',
        advancedSearchUrl: 'mock/advancedsearch'
    }).bind(element);

    equal(true, search.isBound());

    element.find('input[type="text"]').trigger('focus');

    stop(2);

    setTimeout(function() {
        equal(true, search.isOpened());
        equal(1, element.find('.inline-search-results.showing').length);
        equal(1, $('.glasspane').length);
        start();

        element.find('input[type="text"]').trigger($.Event("keydown", {keyCode: 27}));

        setTimeout(function() {
            equal(false, search.isOpened());
            equal(0, element.find('.inline-search-results.showing').length);
            equal(0, $('.glasspane').length);
            start();
        }, 100);
    }, 100);
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

    stop(2);

    // Before first debounce
    setTimeout(function() {
        deepEqual(expected.calls.firstTyping, faker.calls());
        start();
    }, params.debounceDelay + 50);

    // Before second debounce
    setTimeout(function() {
        deepEqual(expected.calls.secondTyping, faker.calls());
        start();
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

    stop(3);

    // Before first fetch response
    setTimeout(function() {
        console.log('before first debounce', params.debounceDelay - 50);
        deepEqual(expected.queries.beforeFirstFetch, this.mockBackendUrlCalls('mock/search'));
        start();
    }.bind(this), params.debounceDelay - 50);

    // After first fetch response : debounce + backend
    setTimeout(function() {
        console.log('after first fetch max delay', params.debounceDelay + params.backendDelay + 100);
        deepEqual(expected.queries.afterFirstFetch, this.mockBackendUrlCalls('mock/search'));
        start();
    }.bind(this), params.debounceDelay + params.backendDelay + 50);

    // After second fetch response : second input + debounce + backend
    var secondFetchDelay = params.secondTypingDelay + params.debounceDelay + params.backendDelay + 50;
    setTimeout(function() {
        console.log('after second fetch max delay', secondFetchDelay);
        deepEqual(expected.queries.afterSecondFetch, this.mockBackendUrlCalls('mock/search'));
        start();
    }.bind(this), secondFetchDelay);
});

}(jQuery));
