/* globals QUnitSketchMixin, FakeD3Chart */
(function($, QUnit) {
"use strict";


QUnit.module("creme.D3ChartBrickController", new QUnitMixin(QUnitEventMixin,
                                                            QUnitAjaxMixin,
                                                            QUnitDialogMixin,
                                                            QUnitBrickMixin,
                                                            QUnitSketchMixin, {
    beforeEach: function() {
        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    }
}));

QUnit.test('creme.D3ChartBrickController', function(assert) {
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    equal(true, controller.sketch() instanceof creme.D3Sketch);
    equal(false, controller.sketch().isBound());

    equal(true, controller.model() instanceof creme.model.Array);
    deepEqual([], controller.model().all());

    equal(false, controller.isBound());
    deepEqual(chart, controller.chart());
});

QUnit.parametrize('creme.D3ChartBrickController (missing chart)', [
    undefined, null
], function(chart, assert) {
    this.assertRaises(function() {
        return new creme.D3ChartBrickController({chart: chart});
    }, Error, 'Error: D3ChartBrickController must have a creme.D3Chart');
});

QUnit.parametrize('creme.D3ChartBrickController (invalid chart)', [
    {}, [], creme.D3Sketch, 'invalid'
], function(chart, assert) {
    this.assertRaises(function() {
        return new creme.D3ChartBrickController({chart: chart});
    }, Error, 'Error: ${chart} is not a creme.D3Chart'.template({chart: chart}));
});

QUnit.test('creme.D3ChartBrickController.bind (no data)', function(assert) {
    var brick = this.createD3ChartBrick().brick();
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    equal(false, controller.isBound());

    controller.bind(brick);

    equal(true, controller.isBound());
    deepEqual([], controller.model().all());

    this.assertRaises(function() {
        controller.bind(brick);
    }, Error, 'Error: D3ChartBrickController is already bound');
});

QUnit.parametrize('creme.D3ChartBrickController.bind', [
    [null, null, [], {drawOnResize: true, x: 3, y: 7, width: 52, height: 107}],
    [[1, 2, 3, 4], null, [1, 2, 3, 4], {drawOnResize: true, x: 3, y: 7, width: 52, height: 107}],
    [null, {x: 147, group: 'A'}, [], {drawOnResize: true, x: 147, y: 7, width: 52, height: 107, group: 'A'}],
    [[1, 2, 3, 4], {x: 147, group: 'A'}, [1, 2, 3, 4], {drawOnResize: true, x: 147, y: 7, width: 52, height: 107, group: 'A'}]
], function(data, props, expectedData, expectedProps, assert) {
    var brick = this.createD3ChartBrick({
        data: data,
        props: props
    }).brick();
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    equal(false, controller.isBound());

    controller.bind(brick);

    equal(true, controller.isBound());
    deepEqual(expectedData, controller.model().all());
    deepEqual(expectedProps, controller.chart().props());
});

QUnit.parametrize('creme.D3ChartBrickController.registerActions (invalid)', [
    null, undefined, {}, [], creme.D3Sketch
], function(brick, assert) {
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    this.assertRaises(function() {
        controller.registerActions(brick);
    }, Error, 'Error: ${brick} is not a creme.bricks.Brick'.template({brick: brick}));
});

QUnit.test('creme.D3ChartBrickController.registerActions', function(assert) {
    var brick = this.createD3ChartBrick().brick();
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    equal(false, brick.getActionBuilders().builders().indexOf('sketch-download') !== -1);
    equal(false, brick.getActionBuilders().builders().indexOf('sketch-popover') !== -1);

    controller.registerActions(brick);

    equal(true, brick.getActionBuilders().builders().indexOf('sketch-download') !== -1);
    equal(true, brick.getActionBuilders().builders().indexOf('sketch-popover') !== -1);
});

QUnit.test('creme.D3ChartBrickDownloadAction', function(assert) {
    var brick = this.createD3ChartBrick().brick();
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    controller.registerActions(brick);
    controller.bind(brick);

    var download = brick.action('sketch-download').on(this.brickActionListeners);

    this.withFakeMethod({
        instance: chart,
        method: 'saveAs',
        callable: function(done, filename, options) {
            done();
        }
    }, function(faker) {
        var options = {filename: 'my-sketch.svg', width: 150, height: 200};

        download.start(options);

        equal(faker.count(), 1);
        deepEqual(faker.calls()[0].slice(1), ['my-sketch.svg', options]);
    });

    deepEqual([
        ['start', {filename: 'my-sketch.svg', width: 150, height: 200}]
    ], this.mockListenerCalls('action-start'));

    deepEqual([['done']], this.mockListenerCalls('action-done'));
});

QUnit.test('creme.D3ChartBrickPopoverAction', function(assert) {
    var brick = this.createD3ChartBrick().brick();
    var chart = new FakeD3Chart();
    var controller = new creme.D3ChartBrickController({chart: chart});

    controller.registerActions(brick);
    controller.bind(brick);

    this.assertClosedPopover();

    var action = brick.action('sketch-popover')
                      .on(this.brickActionListeners);

    this.withFakeMethod({
        instance: chart,
        method: 'asImage',
        callable: function(done) {
            done($('<img>'));
        }
    }, function(faker) {
        var options = {width: 150, height: 200};

        deepEqual([], this.mockListenerCalls('action-done'), '');

        action.start(options);

        equal(faker.count(), 1, 'asImage called once');
        deepEqual(faker.calls()[0].slice(1), [{width: 150, height: 200}]);

        this.assertOpenedPopover();
        this.closePopover();

        deepEqual([['done']], this.mockListenerCalls('action-done'));
    });
});

QUnit.parametrize('creme.setupD3ChartBrick', [
    [null, null, [], {drawOnResize: true, x: 3, y: 7, width: 52, height: 107}],
    [[1, 2, 3, 4], null, [1, 2, 3, 4], {drawOnResize: true, x: 3, y: 7, width: 52, height: 107}],
    [null, {x: 147, group: 'A'}, [], {drawOnResize: true, x: 147, y: 7, width: 52, height: 107, group: 'A'}],
    [[1, 2, 3, 4], {drawOnResize: false, x: 147, group: 'A'}, [1, 2, 3, 4], {drawOnResize: false, x: 147, y: 7, width: 52, height: 107, group: 'A'}]
], function(data, props, expectedData, expectedProps, assert) {
    var chart = new FakeD3Chart();
    var html = this.createD3ChartBrickHtml({
        data: data,
        props: props
    });
    var element = $(html).appendTo(this.qunitFixture());

    var controller = creme.setupD3ChartBrick(element, {chart: chart});
    var brick = creme.widget.create(element).brick();

    equal(true, brick.isBound());
    equal(false, brick.isLoading());

    // chart & controller are bound
    equal(true, controller.isBound());

    // chart has been set up
    deepEqual(expectedProps, chart.props());
    deepEqual(expectedData, chart.model().all());

    // actions are registered
    equal(true, brick.getActionBuilders().builders().indexOf('sketch-download') !== -1);
    equal(true, brick.getActionBuilders().builders().indexOf('sketch-popover') !== -1);
});

}(jQuery, QUnit));
