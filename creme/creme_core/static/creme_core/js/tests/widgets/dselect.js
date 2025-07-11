/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widget.dselect.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true});
    },

    beforeEach: function() {
        this.setMockBackendGET({
            'mock/options': this.backend.responseJSON(200, [[1, 'a'], [15, 'b'], [12.5, 'c']]),
            'mock/options/42': this.backend.responseJSON(200, [[1, 'a'], [15, 'b'], [12.5, 'c'], [42, 'd']]),
            'mock/options/empty': this.backend.responseJSON(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.widget.DynamicSelect.create (empty)', function(assert) {
    var element = $(this.createSelectHtml());

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.create (static)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.delegate._enabled, true);
    assert.equal(element.is('[disabled]'), false);

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    assert.deepEqual([1, 'a'], widget.choice(1));
    assert.deepEqual([5, 'b'], widget.choice(5));
    assert.deepEqual([3, 'c'], widget.choice(3));
});

QUnit.test('creme.widget.DynamicSelect.create (static, readonly)', function(assert) {
    var element = $(this.createSelectHtml({
        readonly: true,
        choices: [
            {value: '1', label: 'a'},
            {value: '2', label: 'b'}
        ]
    }));

    var widget = creme.widget.create(element, {
        backend: this.backend
    });

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.hasClass('is-readonly'), true);

    assert.equal(widget.delegate._enabled, true);
    assert.equal(element.is(':disabled'), false);

    element = $(this.createSelectHtml({
        choices: [
            {value: '1', label: 'a'},
            {value: '2', label: 'b'}
        ]
    }));

    widget = creme.widget.create(element, {
        backend: this.backend,
        readonly: true
    });

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.hasClass('is-readonly'), true);

    assert.equal(widget.delegate._enabled, true);
    assert.equal(element.is(':disabled'), false);
});

QUnit.test('creme.widget.DynamicSelect.create (static, disabled)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'}
        ]
    }));

    element.attr('disabled', '');
    assert.equal(element.is('[disabled]'), true);

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.delegate._enabled, false);
    assert.equal(element.is('[disabled]'), true);

    element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'}
        ]
    }));

    assert.equal(element.is('[disabled]'), false);

    widget = creme.widget.create(element, {disabled: true});

    assert.equal(widget.delegate._enabled, false);
    assert.equal(element.is('[disabled]'), true);
});

QUnit.test('creme.widget.DynamicSelect.create (static, empty url)', function(assert) {
    var element = $(this.createSelectHtml({
        url: '',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    assert.deepEqual([1, 'a'], widget.choice(1));
    assert.deepEqual([5, 'b'], widget.choice(5));
    assert.deepEqual([3, 'c'], widget.choice(3));
});


QUnit.test('creme.widget.DynamicSelect.create (url)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/options',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('a', $('option:nth(0)', element).text());

    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('b', $('option:nth(1)', element).text());

    assert.equal('12.5', $('option:nth(2)', element).attr('value'));
    assert.equal('c', $('option:nth(2)', element).text());

    assert.deepEqual([1, 'a'], widget.choice(1));
    assert.deepEqual([15, 'b'], widget.choice(15));
    assert.deepEqual([12.5, 'c'], widget.choice(12.5));
});

QUnit.test('creme.widget.DynamicSelect.create (unknown url)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'unknown'
    }));

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.destroy', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/options'
    }));

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

    element.creme().widget().destroy();
    assert.equal(element.creme().widget(), undefined);
    assert.equal(element.hasClass('widget-active'), false);
    assert.equal(element.hasClass('widget-ready'), false);

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.choices', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), "");

    assert.deepEqual(widget.choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    assert.deepEqual(widget.choice('1'), ['1', 'a']);
    assert.deepEqual(widget.choice('5'), ['5', 'b']);
    assert.deepEqual(widget.choice('3'), ['3', 'c']);
    assert.equal(widget.choice('15'), undefined);
});

QUnit.test('creme.widget.DynamicSelect.choices (json)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: JSON.stringify({id: 1, name: 'a'}), label: 'a'},
            {value: JSON.stringify({id: 5, name: 'b'}), label: 'b'},
            {value: JSON.stringify({id: 3, name: 'c'}), label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), "");

    assert.deepEqual(widget.choices(), [[JSON.stringify({id: 1, name: 'a'}), 'a'],
                                 [JSON.stringify({id: 5, name: 'b'}), 'b'],
                                 [JSON.stringify({id: 3, name: 'c'}), 'c']]);
    assert.deepEqual(widget.choice(JSON.stringify({id: 1, name: 'a'})), [JSON.stringify({id: 1, name: 'a'}), 'a']);
    assert.deepEqual(widget.choice(JSON.stringify({id: 5, name: 'b'})), [JSON.stringify({id: 5, name: 'b'}), 'b']);
    assert.deepEqual(widget.choice(JSON.stringify({id: 3, name: 'c'})), [JSON.stringify({id: 3, name: 'c'}), 'c']);
    assert.equal(widget.choice('15'), undefined);
});

QUnit.test('creme.widget.DynamicSelect.groups', function(assert) {
    var element = $(this.createSelectHtml());

    var group1 = this.appendOptionGroupTag(element, 'group1');
    this.appendOptionTag(group1, 'a', 1);
    this.appendOptionTag(group1, 'b', 5);

    var group2 = this.appendOptionGroupTag(element, 'group2');
    this.appendOptionTag(group2, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.deepEqual(widget.choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    assert.deepEqual(widget.choice('1'), ['1', 'a']);
    assert.deepEqual(widget.choice('5'), ['5', 'b']);
    assert.deepEqual(widget.choice('3'), ['3', 'c']);
    assert.equal(widget.choice('15'), undefined);

    assert.deepEqual(widget.groups(), ['group1', 'group2']);
});

QUnit.test('creme.widget.DynamicSelect.url (static, empty url)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), "");

    var response = [];
    widget.model().one({
        'fetch-done': function() { response.push('ok'); },
        'fetch-error': function() { response.push('error'); }
    });

    widget.url('unknown');
    assert.deepEqual(response, ['error']);

    assert.equal(widget.url(), 'unknown');
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.url (static, unknown url)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/options'
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), "mock/options");
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

    var response = [];
    widget.model().one({
        'fetch-done': function() { response.push('ok'); },
        'fetch-error': function() { response.push('error'); }
    });

    widget.url('unknown');
    assert.deepEqual(response, ['error']);

    assert.equal(widget.url(), 'unknown');
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.url (static)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), "");
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    widget.url('mock/options');

    assert.equal(widget.url(), 'mock/options');
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

    widget.url('mock/options/empty');

    assert.equal(widget.url(), 'mock/options/empty');
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.url (force empty url)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.reload({name: 'options', content: ''});

    assert.deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true
         }]
    ], this.mockBackendCalls());

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

    // invalid template (url is incomplete)
    widget.model().one({
        'fetch-done': this.mockListenerCalls('fetch-done'),
        'fetch-error': this.mockListenerCalls('fetch-error')
    });

    widget.url('');

    // model is never fetched
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));
    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true
         }]
    ], this.mockBackendCalls());

    assert.equal('', widget.url());
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

});

QUnit.test('creme.widget.DynamicSelect.url (template, ok)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.model().bind({
        'fetch-done': this.mockListener('fetch-done'),
        'fetch-error': this.mockListener('fetch-error')
    });

    widget.reload({name: 'options', content: ''});

    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

    assert.deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined}
        ]
    ], this.mockListenerCalls('fetch-done').map(function(d) { return d[1]; }));
    assert.deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true
         }]
    ], this.mockBackendCalls());

    this.resetMockListenerCalls();

    widget.url('mock/${name}/42');

    assert.equal(4, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));
    assert.equal('42', $('option:nth(3)', element).attr('value'));

    assert.deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'd', value: 42, disabled: false, selected: false, visible: true, group: undefined, help: undefined}
        ]
    ], this.mockListenerCalls('fetch-done').map(function(d) { return d[1]; }));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true}
        ],
        ['mock/options/42', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true}
        ]
    ], this.mockBackendCalls());
});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => unknown)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.reload({name: 'options', content: '/unknown'}, this.mockListener('done'), this.mockListener('error'));

    assert.equal(widget.url(), 'mock/options/unknown');
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    assert.deepEqual([], this.mockListenerCalls('done'));
    assert.deepEqual([
        [404, '']
    ], this.mockListenerCalls('error').map(function(d) { return [d[1].status, d[1].message]; }));
    assert.deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => ok)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.reload({name: 'options', content: ''}, this.mockListener('done'), this.mockListener('error'));

    assert.deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined}]
    ], this.mockListenerCalls('done').map(function(d) { return d[1]; }));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true
        }]
    ], this.mockBackendCalls());

    assert.equal(widget.url(), 'mock/options');
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('15', $('option:nth(1)', element).attr('value'));
    assert.equal('12.5', $('option:nth(2)', element).attr('value'));

});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => empty data)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.reload({name: 'options', content: '/empty'}, this.mockListener('done'), this.mockListener('error'));
    assert.deepEqual([[element, []]], this.mockListenerCalls('done'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual([
        ['mock/options/empty', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {
            delay: 500, enableUriSearch: false, dataType: 'json', forcecache: false, sync: true
         }]
    ], this.mockBackendCalls());

    assert.equal(widget.url(), 'mock/options/empty');
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.reload (incomplete template => clear)', function(assert) {
    var element = $(this.createSelectHtml({
        url: 'mock/${name}${content}',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(widget.url(), null);

    widget.reload({name: 'options'}, this.mockListener('done'), this.mockListener('error'));
    assert.deepEqual([], this.mockListenerCalls('done'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual([], this.mockBackendCalls());

    assert.equal(widget.url(), null);
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.update (undefined)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update(undefined);
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    widget.update(null);
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.update (add)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({added: [[15, 'd'], [6, 'e']]});
    assert.equal(5, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('15', $('option:nth(3)', element).attr('value'));
    assert.equal('6', $('option:nth(4)', element).attr('value'));

    widget.update('{"added":[[17, "f"], [35, "g"]]}');
    assert.equal(7, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('15', $('option:nth(3)', element).attr('value'));
    assert.equal('6', $('option:nth(4)', element).attr('value'));
    assert.equal('17', $('option:nth(5)', element).attr('value'));
    assert.equal('35', $('option:nth(6)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.update (remove)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 33.5, label: 'd'},
            {value: 12, label: 'e'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({removed: [[1, 'a'], [33.5, 'd']]});
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('5', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));
    assert.equal('12', $('option:nth(2)', element).attr('value'));

    widget.update({removed: [[152, 'x'], [112, 'y']]});
    assert.equal(3, $('option', element).length);
    assert.equal(element.is(':disabled'), false);
    assert.equal('5', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));
    assert.equal('12', $('option:nth(2)', element).attr('value'));

    widget.update({removed: [[5, 'b'], [3, 'c'], [12, 'e']]});
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);

    widget.update({removed: [[5, 'b'], [3, 'c'], [12, 'e']]});
    assert.equal(0, $('option', element).length);
    assert.equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.update (add/remove)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({added: [[6, 'bb']], removed: [5]});
    assert.equal(3, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));
    assert.equal('6', $('option:nth(2)', element).attr('value'));
    assert.equal('bb', $('option:nth(2)', element).text());
});

QUnit.parametrize('creme.widget.DynamicSelect.val (static)', [true, false], function(autocomplete, assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {
        backend: this.backend,
        autocomplete: autocomplete,
        noEmpty: true
    });
    assert.equal(3, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    assert.deepEqual(['1', 'a'], widget.firstchoice());
    assert.equal('1', widget.val());

    widget.val(3);
    assert.equal('3', widget.val(), 'existing choice');

    widget.val(15);
    assert.equal('1', widget.val(), 'unknown choice');

    widget.val(null);
    assert.equal('1', widget.val(), 'empty');

    widget.noEmpty(false);

    widget.val(15);
    assert.equal(null, widget.val(), 'unknown choice');

    widget.val(null);
    assert.equal(null, widget.val(), 'empty');
});

QUnit.parametrize('creme.widget.DynamicSelect.val (static, json)', [true, false], function(autocomplete, assert) {
    var element = $(this.createSelectHtml({
        datatype: 'json',
        choices: [
            {value: JSON.stringify({'a': 1}), label: 'a'},
            {value: JSON.stringify({'b': 5}), label: 'b'},
            {value: JSON.stringify({'c': 3}), label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {
        backend: this.backend,
        autocomplete: autocomplete,
        noEmpty: true
    });
    assert.equal(3, $('option', element).length);
    assert.equal(JSON.stringify({'a': 1}), $('option:nth(0)', element).attr('value'));
    assert.equal(JSON.stringify({'b': 5}), $('option:nth(1)', element).attr('value'));
    assert.equal(JSON.stringify({'c': 3}), $('option:nth(2)', element).attr('value'));

    assert.deepEqual([JSON.stringify({'a': 1}), 'a'], widget.firstchoice());
    assert.equal('json', widget.options().datatype);
    assert.equal(JSON.stringify({'a': 1}), widget.val());

    widget.val({'c': 3});
    assert.equal(JSON.stringify({'c': 3}), widget.val(), 'existing choice');
    assert.deepEqual({'c': 3}, widget.cleanedval(), 'cleaned');

    widget.val(JSON.stringify({'b': 5}));
    assert.equal(JSON.stringify({'b': 5}), widget.val(), 'existing choice');
    assert.deepEqual({'b': 5}, widget.cleanedval(), 'cleaned');

    widget.val(15);
    assert.equal(JSON.stringify({'a': 1}), widget.val(), 'unknown choice');
    assert.deepEqual({'a': 1}, widget.cleanedval(), 'cleaned');

    widget.val(null);
    assert.equal(JSON.stringify({'a': 1}), widget.val(), 'empty choice');
    assert.deepEqual({'a': 1}, widget.cleanedval(), 'cleaned');

    widget.noEmpty(false);

    widget.val(15);
    assert.equal(null, widget.val(), 'unknown choice');
    assert.deepEqual(null, widget.cleanedval(), 'cleaned');

    widget.val(null);
    assert.equal(null, widget.val(), 'empty choice');
    assert.deepEqual(null, widget.cleanedval(), 'cleaned');
});

QUnit.parametrize('creme.widget.DynamicSelect.val (static, multiple)', [
    true, false
], [
    true, false
], function(noEmpty, autocomplete, assert) {
    var element = $(this.createSelectHtml({
        multiple: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {
        multiple: true,
        backend: this.backend,
        autocomplete: autocomplete,
        noEmpty: noEmpty
    });
    assert.equal(3, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    assert.deepEqual(['1', 'a'], widget.firstchoice());
    assert.equal(true, widget.options().multiple);
    assert.deepEqual([], widget.val());

    widget.val(3);
    assert.deepEqual(['3'], widget.val());

    widget.val(5);
    assert.deepEqual(['5'], widget.val());

    widget.val(null);
    assert.deepEqual([], widget.val());

    widget.val('3,4,5');
    assert.deepEqual(['5', '3'], widget.val());

    widget.val([3, 4, 5]);
    assert.deepEqual(['5', '3'], widget.val());

    widget.val(15);
    assert.deepEqual([], widget.val());
});

QUnit.parametrize('creme.widget.DynamicSelect.val (static, multiple, json)', [
    true, false
], [
    true, false
], function(noEmpty, autocomplete, assert) {
    var element = $(this.createSelectHtml({
        multiple: true,
        datatype: 'json',
        choices: [
            {value: JSON.stringify({'a': 1}), label: 'a'},
            {value: JSON.stringify({'b': 5}), label: 'b'},
            {value: JSON.stringify({'c': 3}), label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {
        multiple: true,
        backend: this.backend,
        autocomplete: autocomplete,
        noEmpty: noEmpty
    });
    assert.equal(3, $('option', element).length);
    assert.equal(JSON.stringify({'a': 1}), $('option:nth(0)', element).attr('value'));
    assert.equal(JSON.stringify({'b': 5}), $('option:nth(1)', element).attr('value'));
    assert.equal(JSON.stringify({'c': 3}), $('option:nth(2)', element).attr('value'));

    assert.deepEqual([JSON.stringify({'a': 1}), 'a'], widget.firstchoice());
    assert.equal(true, widget.options().multiple);
    assert.equal('json', widget.options().datatype);
    assert.deepEqual([], widget.val());

    widget.val({'c': 3});
    assert.deepEqual([JSON.stringify({'c': 3})], widget.val());
    assert.deepEqual([{'c': 3}], widget.cleanedval(), 'cleaned');

    widget.val(null);
    assert.deepEqual([], widget.val());
    assert.deepEqual([], widget.cleanedval(), 'cleaned');

    widget.val(JSON.stringify([{'b': 5}, {'c': 3}]));
    assert.deepEqual([JSON.stringify({'b': 5}), JSON.stringify({'c': 3})], widget.val());
    assert.deepEqual([{'b': 5}, {'c': 3}], widget.cleanedval(), 'cleaned');

    widget.val(15);
    assert.deepEqual([], widget.val());
});

QUnit.test('creme.widget.DynamicSelect.val (reload)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']])
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    assert.deepEqual(widget.selected(), ['5', 'b']);

    widget.url('mock/options');
    assert.deepEqual(widget.selected(), ['5', 'D']);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('24', $('option:nth(1)', element).attr('value'));
    assert.equal('5', $('option:nth(2)', element).attr('value'));
    assert.equal('12.5', $('option:nth(3)', element).attr('value'));
});

QUnit.parameterize('creme.widget.DynamicSelect.val (reload, cache)', [
    ['full', 0],
    ['force', 1],
    ['ignore', 2]
], function(cacheMode, expected, assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'}
        ]
    }));

    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [[1, 'a']])
    });

    var backend = new creme.ajax.CacheBackend(this.backend, {sync: true});

    // Pre-fill the backend cache
    backend.get('mock/options', {fields: ['id', 'unicode'], sort: 'unicode'}, _.noop, _.noop, {dataType: 'json'});
    assert.equal(this.mockBackendUrlCalls('mock/options').length, 1);

    this.resetMockBackendCalls();
    assert.equal(this.mockBackendUrlCalls('mock/options').length, 0);

    var widget = creme.widget.create(element, {
        backend: backend,
        cache: cacheMode
    });

    assert.equal(cacheMode, widget.cacheMode());

    widget.url('mock/options');
    widget.url('mock/options');

    assert.equal(this.mockBackendUrlCalls('mock/options').length, expected);
});

QUnit.test('creme.widget.DynamicSelect.val (reload, not exists)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']])
    });

    var widget = creme.widget.create(element, {
        backend: this.backend,
        noEmpty: true
    });

    widget.val(3);
    assert.deepEqual(widget.selected(), ['3', 'c']);

    widget.url('mock/options');
    assert.deepEqual(widget.selected(), ['1', 'a']);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('24', $('option:nth(1)', element).attr('value'));
    assert.equal('5', $('option:nth(2)', element).attr('value'));
    assert.equal('12.5', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.reset', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    assert.deepEqual(widget.selected(), ['5', 'b']);

    widget.reset();
    assert.deepEqual(widget.selected(), ['1', 'a']);
});

QUnit.test('creme.widget.DynamicSelect.filter (script)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    element.attr('filter', 'item.value < 4');

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal('item.value < 4', widget.element.attr('filter'));
    assert.equal('item.value < 4', widget.filter());

    assert.equal(2, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (script update)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.equal(3, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));

    widget.filter('item.value < 4');

    assert.equal(2, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));

    widget.filter('item.value > 4');

    assert.equal(1, $('option', element).length);
    assert.equal('5', $('option:nth(0)', element).attr('value'));

    widget.filter("item.label !== 'c'");

    assert.equal(2, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (template)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 7, label: 'd'},
            {value: 4, label: 'e'}
        ]
    }));

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.deepEqual([], widget.dependencies());

    assert.equal(5, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('7', $('option:nth(3)', element).attr('value'));
    assert.equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < ${max}');
    assert.deepEqual(['max'], widget.dependencies());

    assert.equal(5, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('7', $('option:nth(3)', element).attr('value'));
    assert.equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    assert.equal(2, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    assert.equal(4, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('4', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (context)', function(assert) {
    var element = $(this.createSelectHtml({
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 7, label: 'd'},
            {value: 4, label: 'e'}
        ]
    }));

    var widget = creme.widget.create(element, {dependencies: ['max'], backend: this.backend});
    assert.deepEqual(['max'], widget.dependencies());

    assert.equal(5, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('7', $('option:nth(3)', element).attr('value'));
    assert.equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < (context.max ? context.max : 10000)');
    assert.deepEqual(['max'], widget.dependencies());

    assert.equal(5, $('option', element).length, '');
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('7', $('option:nth(3)', element).attr('value'));
    assert.equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    assert.equal(2, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    assert.equal(4, $('option', element).length);
    assert.equal('1', $('option:nth(0)', element).attr('value'));
    assert.equal('5', $('option:nth(1)', element).attr('value'));
    assert.equal('3', $('option:nth(2)', element).attr('value'));
    assert.equal('4', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.options (render label)', function(assert) {
    var element = $(this.createSelectHtml());

    var widget = creme.widget.create(element, {backend: this.backend});

    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [
            {value: 1},
            {value: 24, label: 'A'},
            {value: 5, label: 'A', group: 'group A'},
            {value: 8, label: 'A', help: 'this is A'},
            {value: 12.5, label: 'A', group: 'group A', help: 'this is A'}
        ])
    });

    widget.url('mock/options');

    assert.equal('1', $('option:nth(0)', element).html());
    assert.equal('A', $('option:nth(1)', element).html());
    assert.equal('<span>A</span><span class="hidden">group A</span>', $('option:nth(2)', element).html());
    assert.equal('<span>A</span><span class="group-help">this is A</span>', $('option:nth(3)', element).html());
    assert.equal('<span>A</span><span class="group-help">this is A</span><span class="hidden">group A</span>', $('option:nth(4)', element).html());
});

}(jQuery));
