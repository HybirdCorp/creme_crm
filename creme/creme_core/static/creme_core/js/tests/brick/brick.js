(function($) {

QUnit.module("creme.bricks", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitBrickMixin));

QUnit.test('creme.bricks.Brick (empty)', function(assert) {
    var brick = new creme.bricks.Brick();

    assert.deepEqual({
        overlayDelay: 200,
        deferredStateSaveDelay: 1000
    }, brick._options);

    assert.deepEqual({}, brick.state());
    assert.ok(brick._overlay.is(creme.dialog.Overlay), 'overlay');
    assert.ok(brick._pager.is(creme.list.Pager), 'pager');
    assert.ok(brick._table.is(creme.bricks.BrickTable), 'table');
    assert.equal(undefined, brick._id);
    assert.equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    assert.equal(false, brick.isBound());
    assert.equal(false, brick.isLoading());
    assert.equal(false, brick.readOnly());
});

QUnit.test('creme.bricks.Brick.bind', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick-creme_core-01" data-brick-id="creme_core-01"></div>');

    assert.equal(false, brick.isBound());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal('brick-creme_core-01', brick._id);
    assert.equal('brick-creme_core-01', brick.id());
    assert.equal('creme_core-01', brick.type_id());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (no id)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div></div>');

    assert.equal(false, brick.isBound());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(undefined, brick._id);
    assert.equal(undefined, brick.id());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (no state url)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div></div>');

    this.setBrickStateUrl(null);

    assert.equal(false, brick.isBound());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal('', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (initial collapse/reduced state)', function(assert) {
    var collapsed = $('<div class="is-collapsed"></div>');
    var reduced = $('<div class="is-content-reduced"></div>');
    var both = $('<div class="is-collapsed is-content-reduced"></div>');

    var brick = new creme.bricks.Brick().bind(collapsed);
    assert.equal(true, brick.isBound());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: true,
        reduced: false
    }, brick.state());

    brick = new creme.bricks.Brick().bind(reduced);
    assert.equal(true, brick.isBound());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: false,
        reduced: true
    }, brick.state());

    brick = new creme.bricks.Brick().bind(both);
    assert.equal(true, brick.isBound());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.deepEqual({
        collapsed: true,
        reduced: true
    }, brick.state());
});


QUnit.test('creme.bricks.Brick.bind (already bound)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    assert.equal(false, brick.isBound());

    brick.bind(element);

    assert.equal(true, brick.isBound());

    this.assertRaises(function() {
        brick.bind(element);
    }, Error, 'Error: brick component is already bound');
});

QUnit.test('creme.bricks.Brick.bind (events)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    brick.on('before-bind', this.mockListener('before-bind'))
         .on('bind', this.mockListener('bind'))
         .on('setup-actions', this.mockListener('setup-actions'));

    element.on('brick-before-bind', this.mockListener('brick-before-bind'))
           .on('brick-bind', this.mockListener('brick-bind'))
           .on('brick-setup-actions', this.mockListener('brick-setup-actions'));

    assert.deepEqual([], this.mockListenerCalls('before-bind'));
    assert.deepEqual([], this.mockListenerCalls('bind'));

    assert.deepEqual([], this.mockListenerJQueryCalls('brick-before-bind'));
    assert.deepEqual([], this.mockListenerJQueryCalls('brick-bind'));

    brick.bind(element);

    assert.deepEqual([['before-bind', element]], this.mockListenerCalls('before-bind'));
    assert.deepEqual([['bind', element]], this.mockListenerCalls('bind'));
    assert.deepEqual([['setup-actions', brick._actionBuilders]], this.mockListenerCalls('setup-actions'));

    assert.deepEqual([['brick-before-bind', [brick, element]]], this.mockListenerJQueryCalls('brick-before-bind'));
    assert.deepEqual([['brick-bind', [brick, element]]], this.mockListenerJQueryCalls('brick-bind'));
    assert.deepEqual([['brick-setup-actions', [brick, brick._actionBuilders]]], this.mockListenerJQueryCalls('brick-setup-actions'));
});

QUnit.test('creme.bricks.Brick.unbind', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    assert.equal(false, brick.isBound());

    brick.bind(element);
    assert.equal(true, brick.isBound());

    brick.unbind();
    assert.equal(false, brick.isBound());
});

QUnit.test('creme.bricks.Brick.unbind (not bound)', function(assert) {
    var brick = new creme.bricks.Brick();

    assert.equal(false, brick.isBound());

    this.assertRaises(function() {
        brick.unbind();
    }, Error, 'Error: brick component is not bound');
});


QUnit.test('creme.bricks.Brick.unbind (events)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    brick.on('before-unbind', this.mockListener('before-unbind'))
         .on('unbind', this.mockListener('unbind'));

    element.on('brick-before-unbind', this.mockListener('brick-before-unbind'))
           .on('brick-unbind', this.mockListener('brick-unbind'));

    brick.bind(element);

    assert.deepEqual([], this.mockListenerCalls('before-unbind'));
    assert.deepEqual([], this.mockListenerCalls('unbind'));

    assert.deepEqual([], this.mockListenerJQueryCalls('brick-before-unbind'));
    assert.deepEqual([], this.mockListenerJQueryCalls('brick-unbind'));

    brick.unbind();

    assert.deepEqual([['before-unbind', element]], this.mockListenerCalls('before-unbind'));
    assert.deepEqual([['unbind', element]], this.mockListenerCalls('unbind'));

    assert.deepEqual([['brick-before-unbind', [brick, element]]], this.mockListenerJQueryCalls('brick-before-unbind'));
    assert.deepEqual([['brick-unbind', [brick, element]]], this.mockListenerJQueryCalls('brick-unbind'));
});

QUnit.test('creme.bricks.Brick.trigger', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    brick.on('testit', this.mockListener('testit'));
    element.on('brick-testit', this.mockListener('brick-testit'));

    brick.trigger('testit', [12, 'b']);
    assert.deepEqual([['testit', 12, 'b']], this.mockListenerCalls('testit'));
    assert.deepEqual([], this.mockListenerJQueryCalls('brick-testit'));

    brick.bind(element);

    brick.trigger('testit', [73, 'ab']);
    assert.deepEqual([
        ['testit', 12, 'b'],
        ['testit', 73, 'ab']
    ], this.mockListenerCalls('testit'));
    assert.deepEqual([['brick-testit', [brick, 73, 'ab']]], this.mockListenerJQueryCalls('brick-testit'));

    brick.trigger('testit');
    assert.deepEqual([
        ['testit', 12, 'b'],
        ['testit', 73, 'ab'],
        ['testit']
    ], this.mockListenerCalls('testit'));
    assert.deepEqual([
        ['brick-testit', [brick, 73, 'ab']],
        ['brick-testit', [brick]]
    ], this.mockListenerJQueryCalls('brick-testit'));
});

QUnit.test('creme.bricks.Brick.isLoading', function(assert) {
    var Brick = creme.bricks.Brick;

    assert.equal(false, new Brick().readOnly());
    assert.equal(false, new Brick().bind($('<div></div>')).isLoading());
    assert.equal(true, new Brick().bind($('<div class="is-loading"></div>')).isLoading());
});

QUnit.test('creme.bricks.Brick.readOnly', function(assert) {
    var Brick = creme.bricks.Brick;

    assert.equal(false, new Brick().readOnly());
    assert.equal(false, new Brick().bind($('<div></div>')).readOnly());
    assert.equal(false, new Brick().bind($('<div data-brick-readonly></div>')).readOnly());
    assert.equal(false, new Brick().bind($('<div data-brick-readonly="boo"></div>')).readOnly());
    assert.equal(false, new Brick().bind($('<div data-brick-readonly="false"></div>')).readOnly());
    assert.equal(true, new Brick().bind($('<div data-brick-readonly="true"></div>')).readOnly());
});

QUnit.test('creme.bricks.Brick.dependencies', function(assert) {
    var Brick = creme.bricks.Brick;

    assert.deepEqual([], new Brick().dependencies().keys());
    assert.deepEqual([], new Brick().bind($('<div></div>')).dependencies().keys());
    assert.deepEqual([], new Brick().bind($('<div data-brick-deps></div>')).dependencies().keys());
    assert.deepEqual([], new Brick().bind($('<div data-brick-deps="not json"></div>')).dependencies().keys());
    assert.deepEqual(['a', 'b', 'c'],
              new Brick().bind($('<div data-brick-deps="[&quot;a&quot;,&quot;b&quot;,&quot;c&quot;]"></div>'))
                         .dependencies().keys());
});

QUnit.test('creme.bricks.Brick.reloadingInfo', function(assert) {
    var Brick = creme.bricks.Brick;

    assert.deepEqual({}, new Brick().reloadingInfo());
    assert.deepEqual({}, new Brick().bind($('<div></div>')).reloadingInfo());
    assert.deepEqual({}, new Brick().bind($('<div data-brick-reloading-info></div>')).reloadingInfo());
    assert.deepEqual({}, new Brick().bind($('<div data-brick-reloading-info="not json"></div>')).reloadingInfo());
    assert.deepEqual({a: 12}, new Brick().bind($('<div data-brick-reloading-info="{&quot;a&quot;:12}"></div>')).reloadingInfo());
});

QUnit.test('creme.bricks.Brick.title', function(assert) {
    var Brick = creme.bricks.Brick;

    assert.equal(undefined, new Brick().title());
    assert.equal(undefined, new Brick().bind($('<div>' +
            '<div class="brick-header">' +
                '<div class="brick-title">This is a title</div>' +
            '</div>' +
        '</div>')).title());

    assert.equal('This is a alt title', new Brick().bind($('<div>' +
            '<div class="brick-header">' +
                '<div class="brick-title" title="This is a alt title">This is a title</div>' +
            '</div>' +
        '</div>')).title());
});

QUnit.test('creme.bricks.Brick.setState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    var state_none = { collapsed: false, reduced: false };
    var state_collapsed = { collapsed: true, reduced: false };
    var state_reduced = { collapsed: false, reduced: true };
    var state_both = { collapsed: true, reduced: true };

    brick.bind(element);
    assert.deepEqual(state_none, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.setState(state_collapsed);
    assert.deepEqual(state_collapsed, brick.state());
    assert.equal(true, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.setState(state_reduced);
    assert.deepEqual(state_reduced, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(true, element.is('.is-content-reduced'));

    brick.setState(state_both);
    assert.deepEqual(state_both, brick.state());
    assert.equal(true, element.is('.is-collapsed'));
    assert.equal(true, element.is('.is-content-reduced'));
});

QUnit.test('creme.bricks.Brick.toggleState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    var state_none = { collapsed: false, reduced: false };
    var state_collapsed = { collapsed: true, reduced: false };
    var state_reduced = { collapsed: false, reduced: true };
    var state_both = { collapsed: true, reduced: true };

    brick.bind(element);
    assert.deepEqual(state_none, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.toggleState('collapsed');
    assert.deepEqual(state_collapsed, brick.state());
    assert.equal(true, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.toggleState('collapsed');
    assert.deepEqual(state_none, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    assert.deepEqual(state_reduced, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(true, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    assert.deepEqual(state_none, brick.state());
    assert.equal(false, element.is('.is-collapsed'));
    assert.equal(false, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    brick.toggleState('collapsed');
    assert.deepEqual(state_both, brick.state());
    assert.equal(true, element.is('.is-collapsed'));
    assert.equal(true, element.is('.is-content-reduced'));
});

QUnit.test('creme.bricks.Brick.saveState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    assert.equal(false, brick.isBound());
    assert.equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    brick.saveState();
    assert.equal(0, this.backend.counts.POST);

    brick.bind(element);
    assert.equal(true, brick.isBound());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.equal(0, this.backend.counts.POST);

    brick.saveState();
    assert.equal(1, this.backend.counts.POST);
});

QUnit.test('creme.bricks.Brick.saveState (no save stateURL)', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    this.setBrickStateUrl(null);

    brick.bind(element);
    assert.equal(true, brick.isBound());
    assert.equal("", brick._stateSaveURL, 'stateSaveURL');
    assert.equal(0, this.backend.counts.POST);

    brick.saveState();
    assert.equal(0, this.backend.counts.POST);
});


QUnit.test('creme.bricks.Brick.deferredSaveState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 100
                });
    var element = $('<div></div>');

    assert.equal(false, brick.isBound());
    assert.equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    brick.saveState();
    assert.equal(0, this.backend.counts.POST);

    brick.bind(element);
    assert.equal(true, brick.isBound());
    assert.equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    assert.equal(0, this.backend.counts.POST);

    brick.toggleState('collapsed');
    assert.equal(0, this.backend.counts.POST);

    var done = assert.async();

    setTimeout(function() {
        assert.equal(1, this.backend.counts.POST);
        done();
    }.bind(this), 200);
});

QUnit.test('creme.bricks.Brick.setLoadingState', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-loading-indicator-title"></div></div>');

    element.on('brick-loading-start', this.mockListener('loading-start'));
    element.on('brick-loading-complete', this.mockListener('loading-complete'));

    brick.setLoadingState(true, 'Loading test...');
    assert.equal(false, brick.isBound());
    assert.equal(false, brick.isLoading());
    assert.equal(undefined, brick._defaultLoadingMessage);
    assert.deepEqual([], this.mockListenerCalls('loading-start'));
    assert.deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.bind(element);
    brick.setLoadingState(true, 'Loading test...');
    assert.equal(true, brick.isBound());
    assert.equal(true, brick.isLoading());
    assert.equal('Loading test...', $('.brick-loading-indicator-title', element).html());
    assert.deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    assert.deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.setLoadingState(true, 'Loading test...'); // twice, state not changed
    assert.equal(true, brick.isLoading());
    assert.deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    assert.deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.setLoadingState(false);
    assert.equal(false, brick.isLoading());
    assert.equal('', $('.brick-loading-indicator-title', element).html());
    assert.deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    assert.deepEqual([['brick-loading-complete']], this.mockListenerJQueryCalls('loading-complete'));

    brick.setLoadingState(false); // twice, state not changed
    assert.equal(false, brick.isLoading());
    assert.equal('', $('.brick-loading-indicator-title', element).html());
    assert.deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    assert.deepEqual([['brick-loading-complete']], this.mockListenerJQueryCalls('loading-complete'));
});

QUnit.test('creme.bricks.Brick.setLoadingState (default message)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-loading-indicator-title">Default loading...</div></div>');

    brick.bind(element);
    brick.setLoadingState(true);
    assert.equal(true, brick.isBound());
    assert.equal(true, brick.isLoading());
    assert.equal('Default loading...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(false);
    assert.equal(false, brick.isLoading());
    assert.equal('Default loading...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(true, 'Loading test...'); // twice, state not changed
    assert.equal(true, brick.isLoading());
    assert.equal('Loading test...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(false);
    assert.equal(false, brick.isLoading());
    assert.equal('Default loading...', $('.brick-loading-indicator-title', element).html());
});

QUnit.test('creme.bricks.Brick.setDownloadStatus', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-header"></div></div>');

    brick.setDownloadStatus(10);
    assert.equal(undefined, element.find('.brick-header').attr('data-loading-progress'));

    brick.bind(element);
    assert.equal(undefined, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(0);
    assert.equal(0, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(50);
    assert.equal(50, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(100);
    assert.equal(100, element.find('.brick-header').attr('data-loading-progress'));
});

QUnit.test('creme.bricks.Brick.setSelectionState (no title data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    assert.equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.setSelectionState (no plural data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title" data-title-format="%d entry"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    assert.equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('5 entry', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.setSelectionState (plural data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title" data-title-format="%d entry on %d" data-plural-format="%d entries on %d"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState();
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(-10, -5);
    assert.equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    assert.equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    assert.equal('5 entries on 10', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.redirect', function(assert) {
    var brick = new creme.bricks.Brick();

    brick.redirect('mock/redirected');
    assert.deepEqual(['mock/redirected'], this.mockRedirectCalls());

    brick.redirect('${location}/redirected');
    assert.deepEqual(['mock/redirected',
               window.location.href.replace(/.*?:\/\/[^\/]*/g, '') + '/redirected'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.refresh (widget not ready)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick"></div>').appendTo(this.qunitFixture());

    brick.refresh();
    assert.deepEqual([], this.mockBackendCalls());

    brick.bind(element);
    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    assert.deepEqual([], this.mockBackendCalls());
    assert.deepEqual([], this.mockListenerCalls('refresh-done'));
    assert.deepEqual([], this.mockListenerCalls('refresh-cancel'));
    assert.deepEqual([['fail', 'Missing or invalid source brick']], this.mockListenerCalls('refresh-error'));
});

QUnit.test('creme.bricks.Brick.refresh (no reload url)', function(assert) {
    this.setBrickAllRefreshUrl(null);

    var element = $(
        '<div class="brick ui-creme-widget" widget="brick" id="brick-creme_core-test" data-brick-id="creme_core-test"></div>'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal('brick-creme_core-test', brick.id());
    assert.equal('creme_core-test', brick.type_id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    assert.deepEqual([], this.mockBackendCalls());
    assert.deepEqual([], this.mockListenerCalls('refresh-done'));
    assert.deepEqual([], this.mockListenerCalls('refresh-cancel'));
    assert.deepEqual([
        ['fail', Error('Unable to send request with empty url'),
            new creme.ajax.AjaxResponse(400, 'Unable to send request with empty url')
        ]
    ], this.mockListenerCalls('refresh-error'));  // request failure
});

QUnit.test('creme.bricks.Brick.refresh (empty reload url)', function(assert) {
    this.setBrickAllRefreshUrl('');

    var element = $(
        '<div class="brick ui-creme-widget" widget="brick" id="brick-creme_core-test" data-brick-id="creme_core-test"></div>'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal('brick-creme_core-test', brick.id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    assert.deepEqual([], this.mockBackendCalls());
    assert.deepEqual([], this.mockListenerCalls('refresh-done'));
    assert.deepEqual([], this.mockListenerCalls('refresh-cancel'));
    assert.deepEqual([
        ['fail', Error('Unable to send request with empty url'),
            new creme.ajax.AjaxResponse(400, 'Unable to send request with empty url')
        ]
    ], this.mockListenerCalls('refresh-error'));  // request failure
});

QUnit.test('creme.bricks.Brick.refresh (no id)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick"></div>').appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal(undefined, brick.id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    assert.deepEqual([], this.mockBackendCalls());
    assert.deepEqual([], this.mockListenerCalls('refresh-done'));
    assert.deepEqual([], this.mockListenerCalls('refresh-cancel'));
    assert.deepEqual([['fail', 'Missing or invalid source brick']], this.mockListenerCalls('refresh-error'));
});

QUnit.test('creme.bricks.Brick.refresh (no data-brick-id)', function(assert) {
    var element = $(
        '<div class="brick ui-creme-widget" widget="brick" id="brick-creme_core-test" ></div>'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal('brick-creme_core-test', brick.id());
    assert.equal(undefined, brick.type_id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    assert.deepEqual([], this.mockBackendCalls());
    assert.deepEqual([], this.mockListenerCalls('refresh-done'));
    assert.deepEqual([], this.mockListenerCalls('refresh-cancel'));
    assert.deepEqual([['fail', 'Missing or invalid source brick']], this.mockListenerCalls('refresh-error'));
});

QUnit.test('creme.bricks.Brick.refresh', function(assert) {
    var element = $(
//        '<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>'
        '<div class="brick ui-creme-widget" widget="brick" id="brick-creme_core-test" data-brick-id="creme_core-test"></div>'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
//    assert.equal('brick-for-test', brick.id());
    assert.equal('brick-creme_core-test', brick.id());
    assert.equal('creme_core-test', brick.type_id());

    brick.refresh();
    assert.deepEqual([
//        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
        ['GET', {"brick_id": ["creme_core-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});


QUnit.test('creme.bricks.Brick.refresh (from pager)', function(assert) {
    var element = $(
        '<div class="brick ui-creme-widget" widget="brick" id="brick-creme_core-test" data-brick-id="creme_core-test"></div>'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal('brick-creme_core-test', brick.id());
    assert.equal('creme_core-test', brick.type_id());

    brick._pager.refresh(2);
    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test"], "creme_core-test_page": 2, "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});


QUnit.test('creme.bricks.Brick.refresh (no deps)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-id="A"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-id="B"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    assert.equal(true, brickA.isBound());
    assert.equal('brick-A', brickA.id());
    assert.deepEqual([], brickA.dependencies().keys());

    assert.equal(true, brickB.isBound());
    assert.equal('brick-B', brickB.id());
    assert.deepEqual([], brickB.dependencies().keys());

    brickA.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();
    brickB.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (no deps intersection)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-id="A" data-brick-deps="[&quot;dep1&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-id="B" data-brick-deps="[&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    assert.equal(true, brickA.isBound());
    assert.equal('brick-A', brickA.id());
    assert.deepEqual(['dep1'], brickA.dependencies().keys());

    assert.equal(true, brickB.isBound());
    assert.equal('brick-B', brickB.id());
    assert.deepEqual(['dep2'], brickB.dependencies().keys());

    brickA.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();
    brickB.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (single intersection)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-id="A" data-brick-deps="[&quot;dep1&quot;,&quot;dep3&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-id="B" data-brick-deps="[&quot;dep1&quot;,&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    assert.equal(true, brickA.isBound());
    assert.equal('brick-A', brickA.id());
    assert.deepEqual(['dep1', 'dep3'], brickA.dependencies().keys());

    assert.equal(true, brickB.isBound());
    assert.equal('brick-B', brickB.id());
    assert.deepEqual(['dep1', 'dep2'], brickB.dependencies().keys());

    brickA.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A", "B"], "extra_data": "{}"}]    // refresh A and B (=> "dep1" dependency)
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickB = $('#brick-B').creme().widget().brick();
    assert.equal(true, brickB.isBound());

    brickB.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A", "B"], "extra_data": "{}"}]    // refresh B and A (=> "dep1" dependency)
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (wildcard deps)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-id="A" data-brick-deps="[&quot;dep1&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-id="B" data-brick-deps="[&quot;*&quot;]"></div>';
    var htmlC = '<div class="brick ui-creme-widget" widget="brick" id="brick-C" data-brick-id="C" data-brick-deps="[&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var elementC = $(htmlC).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();
    var brickC = creme.widget.create(elementC).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);
    this.setBrickReloadContent('brick-C', htmlC);

    assert.equal(true, brickA.isBound());
    assert.equal('brick-A', brickA.id());
    assert.equal('A', brickA.type_id());
    assert.deepEqual(['dep1'], brickA.dependencies().keys());

    assert.equal(true, brickB.isBound());
    assert.equal('brick-B', brickB.id());
    assert.equal('B', brickB.type_id());
    assert.deepEqual([], brickB.dependencies().keys());
    assert.equal(true, brickB.dependencies().isWildcard());

    assert.equal(true, brickC.isBound());
    assert.equal('brick-C', brickC.id());
    assert.deepEqual(['dep2'], brickC.dependencies().keys());

    brickA.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A", "B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickB = $('#brick-B').creme().widget().brick();
    assert.equal(true, brickB.isBound());

    brickB.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["A", "B", "C"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickC = $('#brick-C').creme().widget().brick();
    assert.equal(true, brickC.isBound());

    brickC.refresh();

    assert.deepEqual([
        ['GET', {"brick_id": ["B", "C"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
