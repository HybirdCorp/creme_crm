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
    var element = this.createDynamicSelectTag();

    creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.create (static)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(widget.delegate._enabled, true);
    equal(element.is('[disabled]'), false);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual([1, 'a'], widget.choice(1));
    deepEqual([5, 'b'], widget.choice(5));
    deepEqual([3, 'c'], widget.choice(3));
});

QUnit.test('creme.widget.DynamicSelect.create (static, disabled)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);

    element.attr('disabled', '');
    equal(element.is('[disabled]'), true);

    var widget = creme.widget.create(element, {backend: this.backend});

    equal(element.hasClass('widget-ready'), true);

    equal(widget.delegate._enabled, false);
    equal(element.is('[disabled]'), true);

    element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);

    equal(element.is('[disabled]'), false);

    widget = creme.widget.create(element, {disabled: true});

    equal(widget.delegate._enabled, false);
    equal(element.is('[disabled]'), true);
});

QUnit.test('creme.widget.DynamicSelect.create (static, empty url)', function(assert) {
    var element = this.createDynamicSelectTag('');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual([1, 'a'], widget.choice(1));
    deepEqual([5, 'b'], widget.choice(5));
    deepEqual([3, 'c'], widget.choice(3));
});


QUnit.test('creme.widget.DynamicSelect.create (url)', function(assert) {
    var element = this.createDynamicSelectTag('mock/options');

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('a', $('option:nth(0)', element).text());

    equal('15', $('option:nth(1)', element).attr('value'));
    equal('b', $('option:nth(1)', element).text());

    equal('12.5', $('option:nth(2)', element).attr('value'));
    equal('c', $('option:nth(2)', element).text());

    deepEqual([1, 'a'], widget.choice(1));
    deepEqual([15, 'b'], widget.choice(15));
    deepEqual([12.5, 'c'], widget.choice(12.5));
});

QUnit.test('creme.widget.DynamicSelect.create (unknown url)', function(assert) {
    var element = this.createDynamicSelectTag('unknown');

    creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.destroy', function(assert) {
    var element = this.createDynamicSelectTag('mock/options');

    creme.widget.create(element, {backend: this.backend});
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    element.creme().widget().destroy();
    equal(element.creme().widget(), undefined);
    equal(element.hasClass('widget-active'), false);
    equal(element.hasClass('widget-ready'), false);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.choices', function() {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), "");

    deepEqual(widget.choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    deepEqual(widget.choice('1'), ['1', 'a']);
    deepEqual(widget.choice('5'), ['5', 'b']);
    deepEqual(widget.choice('3'), ['3', 'c']);
    equal(widget.choice('15'), undefined);
});

QUnit.test('creme.widget.DynamicSelect.choices (json)', function() {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', JSON.stringify({id: 1, name: 'a'}));
    this.appendOptionTag(element, 'b', JSON.stringify({id: 5, name: 'b'}));
    this.appendOptionTag(element, 'c', JSON.stringify({id: 3, name: 'c'}));

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), "");

    deepEqual(widget.choices(), [[JSON.stringify({id: 1, name: 'a'}), 'a'],
                                 [JSON.stringify({id: 5, name: 'b'}), 'b'],
                                 [JSON.stringify({id: 3, name: 'c'}), 'c']]);
    deepEqual(widget.choice(JSON.stringify({id: 1, name: 'a'})), [JSON.stringify({id: 1, name: 'a'}), 'a']);
    deepEqual(widget.choice(JSON.stringify({id: 5, name: 'b'})), [JSON.stringify({id: 5, name: 'b'}), 'b']);
    deepEqual(widget.choice(JSON.stringify({id: 3, name: 'c'})), [JSON.stringify({id: 3, name: 'c'}), 'c']);
    equal(widget.choice('15'), undefined);
});

QUnit.test('creme.widget.DynamicSelect.groups', function(assert) {
    var element = this.createDynamicSelectTag();

    var group1 = this.appendOptionGroupTag(element, 'group1');
    this.appendOptionTag(group1, 'a', 1);
    this.appendOptionTag(group1, 'b', 5);

    var group2 = this.appendOptionGroupTag(element, 'group2');
    this.appendOptionTag(group2, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    deepEqual(widget.choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    deepEqual(widget.choice('1'), ['1', 'a']);
    deepEqual(widget.choice('5'), ['5', 'b']);
    deepEqual(widget.choice('3'), ['3', 'c']);
    equal(widget.choice('15'), undefined);

    deepEqual(widget.groups(), ['group1', 'group2']);
});

QUnit.test('creme.widget.DynamicSelect.url (static, empty url)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), "");

    var response = [];
    widget.model().one({
        'fetch-done': function() { response.push('ok'); },
        'fetch-error': function() { response.push('error'); }
    });

    widget.url('unknown');
    deepEqual(response, ['error']);

    equal(widget.url(), 'unknown');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.url (static, unknown url)', function(assert) {
    var element = this.createDynamicSelectTag('mock/options');

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), "mock/options");
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    var response = [];
    widget.model().one({
        'fetch-done': function() { response.push('ok'); },
        'fetch-error': function() { response.push('error'); }
    });

    widget.url('unknown');
    deepEqual(response, ['error']);

    equal(widget.url(), 'unknown');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.url (static)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), "");
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    widget.url('mock/options');

    equal(widget.url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    widget.url('mock/options/empty');

    equal(widget.url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.url (force empty url)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.reload({name: 'options', content: ''});

    deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    // invalid template (url is incomplete)
    widget.model().one({
        'fetch-done': this.mockListenerCalls('fetch-done'),
        'fetch-error': this.mockListenerCalls('fetch-error')
    });

    widget.url('');

    // model is never fetched
    deepEqual([], this.mockListenerCalls('fetch-done'));
    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());

    equal('', widget.url());
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

});

QUnit.test('creme.widget.DynamicSelect.url (template, ok)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.model().bind({
        'fetch-done': this.mockListener('fetch-done'),
        'fetch-error': this.mockListener('fetch-error')
    });

    widget.reload({name: 'options', content: ''});

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined}
        ]
    ], this.mockListenerCalls('fetch-done').map(function(d) { return d[1]; }));
    deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());

    this.resetMockListenerCalls();

    widget.url('mock/${name}/42');

    equal(4, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));
    equal('42', $('option:nth(3)', element).attr('value'));

    deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'd', value: 42, disabled: false, selected: false, visible: true, group: undefined, help: undefined}
        ]
    ], this.mockListenerCalls('fetch-done').map(function(d) { return d[1]; }));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}],
        ['mock/options/42', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());
});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => unknown)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.reload({name: 'options', content: '/unknown'}, this.mockListener('done'), this.mockListener('error'));

    equal(widget.url(), 'mock/options/unknown');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual([], this.mockListenerCalls('done'));
    deepEqual([
        [404, '']
    ], this.mockListenerCalls('error').map(function(d) { return [d[1].status, d[1].message]; }));
    deepEqual([], this.mockBackendCalls());
});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => ok)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.reload({name: 'options', content: ''}, this.mockListener('done'), this.mockListener('error'));

    deepEqual([
        [{label: 'a', value: 1, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'b', value: 15, disabled: false, selected: false, visible: true, group: undefined, help: undefined},
         {label: 'c', value: 12.5, disabled: false, selected: false, visible: true, group: undefined, help: undefined}]
    ], this.mockListenerCalls('done').map(function(d) { return d[1]; }));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual([
        ['mock/options', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());

    equal(widget.url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

});

QUnit.test('creme.widget.DynamicSelect.reload (valid template => empty data)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.reload({name: 'options', content: '/empty'}, this.mockListener('done'), this.mockListener('error'));
    deepEqual([[element, []]], this.mockListenerCalls('done'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual([
        ['mock/options/empty', 'GET', {fields: ['id', 'unicode'], sort: 'unicode'}, {delay: 500, enableUriSearch: false, dataType: 'json', sync: true}]
    ], this.mockBackendCalls());

    equal(widget.url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.reload (incomplete template => clear)', function(assert) {
    var element = this.createDynamicSelectTag('mock/${name}${content}');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(widget.url(), null);

    widget.reload({name: 'options'}, this.mockListener('done'), this.mockListener('error'));
    deepEqual([], this.mockListenerCalls('done'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual([], this.mockBackendCalls());

    equal(widget.url(), null);
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.update (undefined)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update(undefined);
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    widget.update(null);
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.update (add)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({added: [[15, 'd'], [6, 'e']]});
    equal(5, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('15', $('option:nth(3)', element).attr('value'));
    equal('6', $('option:nth(4)', element).attr('value'));

    widget.update('{"added":[[17, "f"], [35, "g"]]}');
    equal(7, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('15', $('option:nth(3)', element).attr('value'));
    equal('6', $('option:nth(4)', element).attr('value'));
    equal('17', $('option:nth(5)', element).attr('value'));
    equal('35', $('option:nth(6)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.update (remove)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);
    this.appendOptionTag(element, 'd', 33.5);
    this.appendOptionTag(element, 'e', 12);

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({removed: [[1, 'a'], [33.5, 'd']]});
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    widget.update({removed: [[152, 'x'], [112, 'y']]});
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    widget.update({removed: [[5, 'b'], [3, 'c'], [12, 'e']]});
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    widget.update({removed: [[5, 'b'], [3, 'c'], [12, 'e']]});
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

QUnit.test('creme.widget.DynamicSelect.update (add/remove)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.update({added: [[6, 'bb']], removed: [5]});
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('6', $('option:nth(2)', element).attr('value'));
    equal('bb', $('option:nth(2)', element).text());
});

QUnit.test('creme.widget.DynamicSelect.val (static)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual(['1', 'a'], widget.firstchoice());
    equal('1', widget.val());

    widget.val(3);
    equal('3', widget.val(), 'existing choice');

    widget.val(15);
    equal('1', widget.val(), 'unknown choice');
});

QUnit.test('creme.widget.DynamicSelect.val (static, json)', function(assert) {
    var element = this.createDynamicSelectTag().attr('datatype', 'json');
    this.appendOptionTag(element, 'a', JSON.stringify({'a': 1}));
    this.appendOptionTag(element, 'b', JSON.stringify({'b': 5}));
    this.appendOptionTag(element, 'c', JSON.stringify({'c': 3}));

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(3, $('option', element).length);
    equal(JSON.stringify({'a': 1}), $('option:nth(0)', element).attr('value'));
    equal(JSON.stringify({'b': 5}), $('option:nth(1)', element).attr('value'));
    equal(JSON.stringify({'c': 3}), $('option:nth(2)', element).attr('value'));

    deepEqual([JSON.stringify({'a': 1}), 'a'], widget.firstchoice());
    equal('json', widget.options().datatype);
    equal(JSON.stringify({'a': 1}), widget.val());

    widget.val({'c': 3});
    equal(JSON.stringify({'c': 3}), widget.val(), 'existing choice');
    deepEqual({'c': 3}, widget.cleanedval(), 'cleaned');

    widget.val(JSON.stringify({'b': 5}));
    equal(JSON.stringify({'b': 5}), widget.val(), 'existing choice');
    deepEqual({'b': 5}, widget.cleanedval(), 'cleaned');

    widget.val(15);
    equal(JSON.stringify({'a': 1}), widget.val(), 'unknown choice');
    deepEqual({'a': 1}, widget.cleanedval(), 'cleaned');
});

QUnit.test('creme.widget.DynamicSelect.val (static, multiple)', function(assert) {
    var element = this.createDynamicSelectTag().attr('multiple', 'multiple');
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {multiple: true, backend: this.backend});
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual(['1', 'a'], widget.firstchoice());
    equal(true, widget.options().multiple);
    deepEqual([], widget.val());

    widget.val(3);
    deepEqual(['3'], widget.val());

    widget.val('3,4,5');
    deepEqual(['5', '3'], widget.val());

    widget.val(15);
    deepEqual([], widget.val());
});

QUnit.test('creme.widget.DynamicSelect.val (static, multiple, json)', function(assert) {
    var element = this.createDynamicSelectTag().attr('multiple', 'multiple')
                                       .attr('datatype', 'json');

    this.appendOptionTag(element, 'a', JSON.stringify({'a': 1}));
    this.appendOptionTag(element, 'b', JSON.stringify({'b': 5}));
    this.appendOptionTag(element, 'c', JSON.stringify({'c': 3}));

    var widget = creme.widget.create(element, {multiple: true, backend: this.backend});
    equal(3, $('option', element).length);
    equal(JSON.stringify({'a': 1}), $('option:nth(0)', element).attr('value'));
    equal(JSON.stringify({'b': 5}), $('option:nth(1)', element).attr('value'));
    equal(JSON.stringify({'c': 3}), $('option:nth(2)', element).attr('value'));

    deepEqual([JSON.stringify({'a': 1}), 'a'], widget.firstchoice());
    equal(true, widget.options().multiple);
    equal('json', widget.options().datatype);
    deepEqual([], widget.val());

    widget.val({'c': 3});
    deepEqual([JSON.stringify({'c': 3})], widget.val());
    deepEqual([{'c': 3}], widget.cleanedval(), 'cleaned');

    widget.val(JSON.stringify([{'b': 5}, {'c': 3}]));
    deepEqual([JSON.stringify({'b': 5}), JSON.stringify({'c': 3})], widget.val());
    deepEqual([{'b': 5}, {'c': 3}], widget.cleanedval(), 'cleaned');

    widget.val(15);
    deepEqual([], widget.val());
});

QUnit.test('creme.widget.DynamicSelect.val (reload)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);


    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']])
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    deepEqual(widget.selected(), ['5', 'b']);

    widget.url('mock/options');
    deepEqual(widget.selected(), ['5', 'D']);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('24', $('option:nth(1)', element).attr('value'));
    equal('5', $('option:nth(2)', element).attr('value'));
    equal('12.5', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.val (reload, not exists)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    this.setMockBackendGET({
        'mock/options': this.backend.responseJSON(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']])
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(3);
    deepEqual(widget.selected(), ['3', 'c']);

    widget.url('mock/options');
    deepEqual(widget.selected(), ['1', 'a']);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('24', $('option:nth(1)', element).attr('value'));
    equal('5', $('option:nth(2)', element).attr('value'));
    equal('12.5', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.reset', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    deepEqual(widget.selected(), ['5', 'b']);

    widget.reset();
    deepEqual(widget.selected(), ['1', 'a']);
});

QUnit.test('creme.widget.DynamicSelect.filter (script)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    element.attr('filter', 'item.value < 4');

    var widget = creme.widget.create(element, {backend: this.backend});
    equal('item.value < 4', widget.element.attr('filter'));
    equal('item.value < 4', widget.filter());

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (script update)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);

    var widget = creme.widget.create(element, {backend: this.backend});
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    widget.filter('item.value < 4');

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.filter('item.value > 4');

    equal(1, $('option', element).length);
    equal('5', $('option:nth(0)', element).attr('value'));

    widget.filter("item.label !== 'c'");

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (template)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);
    this.appendOptionTag(element, 'd', 7);
    this.appendOptionTag(element, 'e', 4);

    var widget = creme.widget.create(element, {backend: this.backend});
    deepEqual([], widget.dependencies());

    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < ${max}');
    deepEqual(['max'], widget.dependencies());

    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    equal(4, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('4', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.filter (context)', function(assert) {
    var element = this.createDynamicSelectTag();
    this.appendOptionTag(element, 'a', 1);
    this.appendOptionTag(element, 'b', 5);
    this.appendOptionTag(element, 'c', 3);
    this.appendOptionTag(element, 'd', 7);
    this.appendOptionTag(element, 'e', 4);

    var widget = creme.widget.create(element, {dependencies: ['max'], backend: this.backend});
    deepEqual(['max'], widget.dependencies());

    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < (context.max ? context.max : 10000)');
    deepEqual(['max'], widget.dependencies());

    equal(5, $('option', element).length, '');
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    equal(4, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('4', $('option:nth(3)', element).attr('value'));
});

QUnit.test('creme.widget.DynamicSelect.options (render label)', function(assert) {
    var element = this.createDynamicSelectTag();
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

    equal('1', $('option:nth(0)', element).html());
    equal('A', $('option:nth(1)', element).html());
    equal('<span>A</span><span class="hidden">group A</span>', $('option:nth(2)', element).html());
    equal('<span>A</span><span class="group-help">this is A</span>', $('option:nth(3)', element).html());
    equal('<span>A</span><span class="group-help">this is A</span><span class="hidden">group A</span>', $('option:nth(4)', element).html());
});

}(jQuery));
