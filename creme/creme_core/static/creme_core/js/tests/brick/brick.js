(function($) {

QUnit.module("creme.bricks", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitBrickMixin));

QUnit.test('creme.bricks.Brick (empty)', function(assert) {
    var brick = new creme.bricks.Brick();

    deepEqual({
        overlayDelay: 200,
        deferredStateSaveDelay: 1000
    }, brick._options);

    deepEqual({}, brick.state());
    ok(brick._overlay.is(creme.dialog.Overlay), 'overlay');
    ok(brick._pager.is(creme.list.Pager), 'pager');
    ok(brick._table.is(creme.bricks.BrickTable), 'table');
    equal(undefined, brick._id);
    equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    equal(false, brick.isBound());
    equal(false, brick.isLoading());
    equal(false, brick.readOnly());
});

QUnit.test('creme.bricks.Brick.bind', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    equal(false, brick.isBound());

    brick.bind(element);

    equal(true, brick.isBound());
    equal('brick_01', brick._id);
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (no id)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div></div>');

    equal(false, brick.isBound());

    brick.bind(element);

    equal(true, brick.isBound());
    equal(undefined, brick._id);
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (no state url)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div></div>');

    this.setBrickStateUrl(null);

    equal(false, brick.isBound());

    brick.bind(element);

    equal(true, brick.isBound());
    equal('', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: false,
        reduced: false
    }, brick.state());
});

QUnit.test('creme.bricks.Brick.bind (initial collapse/reduced state)', function(assert) {
    var collapsed = $('<div class="is-collapsed"></div>');
    var reduced = $('<div class="is-content-reduced"></div>');
    var both = $('<div class="is-collapsed is-content-reduced"></div>');

    var brick = new creme.bricks.Brick().bind(collapsed);
    equal(true, brick.isBound());
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: true,
        reduced: false
    }, brick.state());

    brick = new creme.bricks.Brick().bind(reduced);
    equal(true, brick.isBound());
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: false,
        reduced: true
    }, brick.state());

    brick = new creme.bricks.Brick().bind(both);
    equal(true, brick.isBound());
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    deepEqual({
        collapsed: true,
        reduced: true
    }, brick.state());
});


QUnit.test('creme.bricks.Brick.bind (already bound)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    equal(false, brick.isBound());

    brick.bind(element);

    equal(true, brick.isBound());

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

    deepEqual([], this.mockListenerCalls('before-bind'));
    deepEqual([], this.mockListenerCalls('bind'));

    deepEqual([], this.mockListenerJQueryCalls('brick-before-bind'));
    deepEqual([], this.mockListenerJQueryCalls('brick-bind'));

    brick.bind(element);

    deepEqual([['before-bind', element]], this.mockListenerCalls('before-bind'));
    deepEqual([['bind', element]], this.mockListenerCalls('bind'));
    deepEqual([['setup-actions', brick._actionBuilders]], this.mockListenerCalls('setup-actions'));

    deepEqual([['brick-before-bind', [brick, element]]], this.mockListenerJQueryCalls('brick-before-bind'));
    deepEqual([['brick-bind', [brick, element]]], this.mockListenerJQueryCalls('brick-bind'));
    deepEqual([['brick-setup-actions', [brick, brick._actionBuilders]]], this.mockListenerJQueryCalls('brick-setup-actions'));
});

QUnit.test('creme.bricks.Brick.unbind', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    equal(false, brick.isBound());

    brick.bind(element);
    equal(true, brick.isBound());

    brick.unbind();
    equal(false, brick.isBound());
});

QUnit.test('creme.bricks.Brick.unbind (not bound)', function(assert) {
    var brick = new creme.bricks.Brick();

    equal(false, brick.isBound());

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

    deepEqual([], this.mockListenerCalls('before-unbind'));
    deepEqual([], this.mockListenerCalls('unbind'));

    deepEqual([], this.mockListenerJQueryCalls('brick-before-unbind'));
    deepEqual([], this.mockListenerJQueryCalls('brick-unbind'));

    brick.unbind();

    deepEqual([['before-unbind', element]], this.mockListenerCalls('before-unbind'));
    deepEqual([['unbind', element]], this.mockListenerCalls('unbind'));

    deepEqual([['brick-before-unbind', [brick, element]]], this.mockListenerJQueryCalls('brick-before-unbind'));
    deepEqual([['brick-unbind', [brick, element]]], this.mockListenerJQueryCalls('brick-unbind'));
});

QUnit.test('creme.bricks.Brick.trigger', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div id="brick_01"></div>');

    brick.on('testit', this.mockListener('testit'));
    element.on('brick-testit', this.mockListener('brick-testit'));

    brick.trigger('testit', [12, 'b']);
    deepEqual([['testit', 12, 'b']], this.mockListenerCalls('testit'));
    deepEqual([], this.mockListenerJQueryCalls('brick-testit'));

    brick.bind(element);

    brick.trigger('testit', [73, 'ab']);
    deepEqual([
        ['testit', 12, 'b'],
        ['testit', 73, 'ab']
    ], this.mockListenerCalls('testit'));
    deepEqual([['brick-testit', [brick, 73, 'ab']]], this.mockListenerJQueryCalls('brick-testit'));

    brick.trigger('testit');
    deepEqual([
        ['testit', 12, 'b'],
        ['testit', 73, 'ab'],
        ['testit']
    ], this.mockListenerCalls('testit'));
    deepEqual([
        ['brick-testit', [brick, 73, 'ab']],
        ['brick-testit', [brick]]
    ], this.mockListenerJQueryCalls('brick-testit'));
});

QUnit.test('creme.bricks.Brick.isLoading', function(assert) {
    var Brick = creme.bricks.Brick;

    equal(false, new Brick().readOnly());
    equal(false, new Brick().bind($('<div></div>')).isLoading());
    equal(true, new Brick().bind($('<div class="is-loading"></div>')).isLoading());
});

QUnit.test('creme.bricks.Brick.readOnly', function(assert) {
    var Brick = creme.bricks.Brick;

    equal(false, new Brick().readOnly());
    equal(false, new Brick().bind($('<div></div>')).readOnly());
    equal(false, new Brick().bind($('<div data-brick-readonly></div>')).readOnly());
    equal(false, new Brick().bind($('<div data-brick-readonly="boo"></div>')).readOnly());
    equal(false, new Brick().bind($('<div data-brick-readonly="false"></div>')).readOnly());
    equal(true, new Brick().bind($('<div data-brick-readonly="true"></div>')).readOnly());
});

QUnit.test('creme.bricks.Brick.dependencies', function(assert) {
    var Brick = creme.bricks.Brick;

    deepEqual([], new Brick().dependencies().keys());
    deepEqual([], new Brick().bind($('<div></div>')).dependencies().keys());
    deepEqual([], new Brick().bind($('<div data-brick-deps></div>')).dependencies().keys());
    deepEqual([], new Brick().bind($('<div data-brick-deps="not json"></div>')).dependencies().keys());
    deepEqual(['a', 'b', 'c'],
              new Brick().bind($('<div data-brick-deps="[&quot;a&quot;,&quot;b&quot;,&quot;c&quot;]"></div>'))
                         .dependencies().keys());
});

QUnit.test('creme.bricks.Brick.reloadingInfo', function(assert) {
    var Brick = creme.bricks.Brick;

    deepEqual({}, new Brick().reloadingInfo());
    deepEqual({}, new Brick().bind($('<div></div>')).reloadingInfo());
    deepEqual({}, new Brick().bind($('<div data-brick-reloading-info></div>')).reloadingInfo());
    deepEqual({}, new Brick().bind($('<div data-brick-reloading-info="not json"></div>')).reloadingInfo());
    deepEqual({a: 12}, new Brick().bind($('<div data-brick-reloading-info="{&quot;a&quot;:12}"></div>')).reloadingInfo());
});

QUnit.test('creme.bricks.Brick.title', function(assert) {
    var Brick = creme.bricks.Brick;

    equal(undefined, new Brick().title());
    equal(undefined, new Brick().bind($('<div>' +
            '<div class="brick-header">' +
                '<div class="brick-title">This is a title</div>' +
            '</div>' +
        '</div>')).title());

    equal('This is a alt title', new Brick().bind($('<div>' +
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
    deepEqual(state_none, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.setState(state_collapsed);
    deepEqual(state_collapsed, brick.state());
    equal(true, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.setState(state_reduced);
    deepEqual(state_reduced, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(true, element.is('.is-content-reduced'));

    brick.setState(state_both);
    deepEqual(state_both, brick.state());
    equal(true, element.is('.is-collapsed'));
    equal(true, element.is('.is-content-reduced'));
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
    deepEqual(state_none, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.toggleState('collapsed');
    deepEqual(state_collapsed, brick.state());
    equal(true, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.toggleState('collapsed');
    deepEqual(state_none, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    deepEqual(state_reduced, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(true, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    deepEqual(state_none, brick.state());
    equal(false, element.is('.is-collapsed'));
    equal(false, element.is('.is-content-reduced'));

    brick.toggleState('reduced');
    brick.toggleState('collapsed');
    deepEqual(state_both, brick.state());
    equal(true, element.is('.is-collapsed'));
    equal(true, element.is('.is-content-reduced'));
});

QUnit.test('creme.bricks.Brick.saveState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    equal(false, brick.isBound());
    equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    brick.saveState();
    equal(0, this.backend.counts.POST);

    brick.bind(element);
    equal(true, brick.isBound());
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    equal(0, this.backend.counts.POST);

    brick.saveState();
    equal(1, this.backend.counts.POST);
});

QUnit.test('creme.bricks.Brick.saveState (no save stateURL)', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 0
                });
    var element = $('<div></div>');

    this.setBrickStateUrl(null);

    brick.bind(element);
    equal(true, brick.isBound());
    equal("", brick._stateSaveURL, 'stateSaveURL');
    equal(0, this.backend.counts.POST);

    brick.saveState();
    equal(0, this.backend.counts.POST);
});


QUnit.test('creme.bricks.Brick.deferredSaveState', function(assert) {
    var brick = new creme.bricks.Brick({
                    deferredStateSaveDelay: 100
                });
    var element = $('<div></div>');

    equal(false, brick.isBound());
    equal(undefined, brick._stateSaveURL, 'stateSaveURL');

    brick.saveState();
    equal(0, this.backend.counts.POST);

    brick.bind(element);
    equal(true, brick.isBound());
    equal('mock/brick/status', brick._stateSaveURL, 'stateSaveURL');
    equal(0, this.backend.counts.POST);

    brick.toggleState('collapsed');
    equal(0, this.backend.counts.POST);

    stop(1);

    setTimeout(function() {
        equal(1, this.backend.counts.POST);
        start();
    }.bind(this), 200);
});

QUnit.test('creme.bricks.Brick.setLoadingState', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-loading-indicator-title"></div></div>');

    element.on('brick-loading-start', this.mockListener('loading-start'));
    element.on('brick-loading-complete', this.mockListener('loading-complete'));

    brick.setLoadingState(true, 'Loading test...');
    equal(false, brick.isBound());
    equal(false, brick.isLoading());
    equal(undefined, brick._defaultLoadingMessage);
    deepEqual([], this.mockListenerCalls('loading-start'));
    deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.bind(element);
    brick.setLoadingState(true, 'Loading test...');
    equal(true, brick.isBound());
    equal(true, brick.isLoading());
    equal('Loading test...', $('.brick-loading-indicator-title', element).html());
    deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.setLoadingState(true, 'Loading test...'); // twice, state not chaned
    equal(true, brick.isLoading());
    deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    deepEqual([], this.mockListenerCalls('loading-complete'));

    brick.setLoadingState(false);
    equal(false, brick.isLoading());
    equal('', $('.brick-loading-indicator-title', element).html());
    deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    deepEqual([['brick-loading-complete']], this.mockListenerJQueryCalls('loading-complete'));

    brick.setLoadingState(false); // twice, state not chaned
    equal(false, brick.isLoading());
    equal('', $('.brick-loading-indicator-title', element).html());
    deepEqual([['brick-loading-start']], this.mockListenerJQueryCalls('loading-start'));
    deepEqual([['brick-loading-complete']], this.mockListenerJQueryCalls('loading-complete'));
});

QUnit.test('creme.bricks.Brick.setLoadingState (default message)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-loading-indicator-title">Default loading...</div></div>');

    brick.bind(element);
    brick.setLoadingState(true);
    equal(true, brick.isBound());
    equal(true, brick.isLoading());
    equal('Default loading...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(false);
    equal(false, brick.isLoading());
    equal('Default loading...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(true, 'Loading test...'); // twice, state not chaned
    equal(true, brick.isLoading());
    equal('Loading test...', $('.brick-loading-indicator-title', element).html());

    brick.setLoadingState(false);
    equal(false, brick.isLoading());
    equal('Default loading...', $('.brick-loading-indicator-title', element).html());
});

QUnit.test('creme.bricks.Brick.setDownloadStatus', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div><div class="brick-header"></div></div>');

    brick.setDownloadStatus(10);
    equal(undefined, element.find('.brick-header').attr('data-loading-progress'));

    brick.bind(element);
    equal(undefined, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(0);
    equal(0, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(50);
    equal(50, element.find('.brick-header').attr('data-loading-progress'));

    brick.setDownloadStatus(100);
    equal(100, element.find('.brick-header').attr('data-loading-progress'));
});

QUnit.test('creme.bricks.Brick.setSelectionState (no title data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    equal(true, brick.isBound());
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.setSelectionState (no plural data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title" data-title-format="%d entry"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    equal(true, brick.isBound());
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('5 entry', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.setSelectionState (plural data)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div>' +
            '<div class="brick-selection-indicator">' +
               '<span class="brick-selection-title" data-title-format="%d entry on %d" data-plural-format="%d entries on %d"></span>' +
            '</div>' +
        '</div>');

    brick.setSelectionState(0, 10);

    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.bind(element);

    equal(true, brick.isBound());
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(0, 10);
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState();
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(-10, -5);
    equal(false, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('', element.find('.brick-selection-title').text());

    brick.setSelectionState(5, 10);
    equal(true, element.find('.brick-selection-indicator').is('.has-selection'));
    equal('5 entries on 10', element.find('.brick-selection-title').text());
});

QUnit.test('creme.bricks.Brick.redirect', function(assert) {
    var brick = new creme.bricks.Brick();

    brick.redirect('mock/redirected');
    deepEqual(['mock/redirected'], this.mockRedirectCalls());

    brick.redirect('${location}/redirected');
    deepEqual(['mock/redirected',
               window.location.href.replace(/.*?:\/\/[^\/]*/g, '') + '/redirected'], this.mockRedirectCalls());
});

QUnit.test('creme.bricks.Brick.refresh (widget not ready)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick"></div>').appendTo(this.qunitFixture());

    brick.refresh();
    deepEqual([], this.mockBackendCalls());

    brick.bind(element);
    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    deepEqual([], this.mockBackendCalls());
    deepEqual([], this.mockListenerCalls('refresh-done'));
    deepEqual([], this.mockListenerCalls('refresh-cancel'));
    deepEqual([['fail', 'Missing or invalid source brick']], this.mockListenerCalls('refresh-error'));
});

QUnit.test('creme.bricks.Brick.refresh (no reload url)', function(assert) {
    this.setBrickAllRefreshUrl(null);

    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    equal(true, brick.isBound());
    equal('brick-for-test', brick.id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    deepEqual([], this.mockBackendCalls());
    deepEqual([], this.mockListenerCalls('refresh-done'));
    deepEqual([], this.mockListenerCalls('refresh-cancel'));
    deepEqual([
        ['fail', Error('Unable to send request with empty url'),
            new creme.ajax.AjaxResponse(400, 'Unable to send request with empty url')
        ]
    ], this.mockListenerCalls('refresh-error'));  // request failure
});

QUnit.test('creme.bricks.Brick.refresh (empty reload url)', function(assert) {
    this.setBrickAllRefreshUrl('');

    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    equal(true, brick.isBound());
    equal('brick-for-test', brick.id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    deepEqual([], this.mockBackendCalls());
    deepEqual([], this.mockListenerCalls('refresh-done'));
    deepEqual([], this.mockListenerCalls('refresh-cancel'));
    deepEqual([
        ['fail', Error('Unable to send request with empty url'),
            new creme.ajax.AjaxResponse(400, 'Unable to send request with empty url')
        ]
    ], this.mockListenerCalls('refresh-error'));  // request failure
});

QUnit.test('creme.bricks.Brick.refresh (no id)', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick"></div>').appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    equal(true, brick.isBound());
    equal(undefined, brick.id());

    brick.refresh({}, {
        'done': this.mockListener('refresh-done'),
        'cancel': this.mockListener('refresh-cancel'),
        'fail': this.mockListener('refresh-error')
    });

    deepEqual([], this.mockBackendCalls());
    deepEqual([], this.mockListenerCalls('refresh-done'));
    deepEqual([], this.mockListenerCalls('refresh-cancel'));
    deepEqual([['fail', 'Missing or invalid source brick']], this.mockListenerCalls('refresh-error'));
});

QUnit.test('creme.bricks.Brick.refresh', function(assert) {
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test"></div>').appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);
    var brick = widget.brick();

    equal(true, brick.isBound());
    equal('brick-for-test', brick.id());

    brick.refresh();
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (no deps)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    equal(true, brickA.isBound());
    equal('brick-A', brickA.id());
    deepEqual([], brickA.dependencies().keys());

    equal(true, brickB.isBound());
    equal('brick-B', brickB.id());
    deepEqual([], brickB.dependencies().keys());

    brickA.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();
    brickB.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (no deps intersection)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-deps="[&quot;dep1&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-deps="[&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    equal(true, brickA.isBound());
    equal('brick-A', brickA.id());
    deepEqual(['dep1'], brickA.dependencies().keys());

    equal(true, brickB.isBound());
    equal('brick-B', brickB.id());
    deepEqual(['dep2'], brickB.dependencies().keys());

    brickA.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();
    brickB.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (single instersection)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-deps="[&quot;dep1&quot;,&quot;dep3&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-deps="[&quot;dep1&quot;,&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);

    equal(true, brickA.isBound());
    equal('brick-A', brickA.id());
    deepEqual(['dep1', 'dep3'], brickA.dependencies().keys());

    equal(true, brickB.isBound());
    equal('brick-B', brickB.id());
    deepEqual(['dep1', 'dep2'], brickB.dependencies().keys());

    brickA.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A", "brick-B"], "extra_data": "{}"}]    // refresh A and B (=> "dep1" dependency)
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickB = $('#brick-B').creme().widget().brick();
    equal(true, brickB.isBound());

    brickB.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A", "brick-B"], "extra_data": "{}"}]    // refresh B and A (=> "dep1" dependency)
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.bricks.Brick.refresh (wildcard deps)', function(assert) {
    var htmlA = '<div class="brick ui-creme-widget" widget="brick" id="brick-A" data-brick-deps="[&quot;dep1&quot;]"></div>';
    var htmlB = '<div class="brick ui-creme-widget" widget="brick" id="brick-B" data-brick-deps="[&quot;*&quot;]"></div>';
    var htmlC = '<div class="brick ui-creme-widget" widget="brick" id="brick-C" data-brick-deps="[&quot;dep2&quot;]"></div>';
    var elementA = $(htmlA).appendTo(this.qunitFixture());
    var elementB = $(htmlB).appendTo(this.qunitFixture());
    var elementC = $(htmlC).appendTo(this.qunitFixture());
    var brickA = creme.widget.create(elementA).brick();
    var brickB = creme.widget.create(elementB).brick();
    var brickC = creme.widget.create(elementC).brick();

    this.setBrickReloadContent('brick-A', htmlA);
    this.setBrickReloadContent('brick-B', htmlB);
    this.setBrickReloadContent('brick-C', htmlC);

    equal(true, brickA.isBound());
    equal('brick-A', brickA.id());
    deepEqual(['dep1'], brickA.dependencies().keys());

    equal(true, brickB.isBound());
    equal('brick-B', brickB.id());
    deepEqual([], brickB.dependencies().keys());
    equal(true, brickB.dependencies().isWildcard());

    equal(true, brickC.isBound());
    equal('brick-C', brickC.id());
    deepEqual(['dep2'], brickC.dependencies().keys());

    brickA.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A", "brick-B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickB = $('#brick-B').creme().widget().brick();
    equal(true, brickB.isBound());

    brickB.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-A", "brick-B", "brick-C"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.resetMockBackendCalls();

    brickC = $('#brick-C').creme().widget().brick();
    equal(true, brickC.isBound());

    brickC.refresh();

    deepEqual([
        ['GET', {"brick_id": ["brick-B", "brick-C"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
