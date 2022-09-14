(function($) {

QUnit.module("creme.D3Sketch", new QUnitMixin(QUnitEventMixin));

QUnit.test('creme.D3Sketch', function(assert) {
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    equal(undefined, sketch.svg());
    equal(undefined, sketch.element());

    deepEqual({width: 0, height: 0}, sketch.size());
    deepEqual({width: 0, height: 0}, sketch.containerSize());

    deepEqual(0, sketch.width());
    deepEqual(0, sketch.height());
});

QUnit.test('creme.D3Sketch.bind', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">');
    var sketch = new creme.D3Sketch().bind(element);

    equal(true, sketch.isBound());
    equal(element, sketch.element());
    ok(sketch.svg() !== undefined);

    deepEqual({width: 300, height: 200}, sketch.size());
    deepEqual({width: 300, height: 200}, sketch.containerSize());

    deepEqual(300, sketch.width());
    deepEqual(200, sketch.height());

    this.assertRaises(function() {
        sketch.bind(element);
    }, Error, 'Error: D3Sketch is already bound');
});

QUnit.parametrize('creme.D3Sketch.bind (invalid selection)', [
    [
        $([
            '<div style="width: 300px; height: 200px;">',
            '<div style="width: 300px; height: 200px;">'
        ])
    ],
    [
        $([])
    ]
], function(element, assert) {
    this.assertRaises(function() {
        new creme.D3Sketch().bind(element);
    }, Error, 'Error: Unable to bind D3Sketch to multiple nor empty selection');
});

QUnit.test('creme.D3Sketch.unbind', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">');
    var sketch = new creme.D3Sketch();

    this.assertRaises(function() {
        sketch.unbind(element);
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);

    equal(true, sketch.isBound());
    equal(element, sketch.element());
    ok(sketch.svg() !== undefined);

    sketch.unbind();

    equal(undefined, sketch.svg());
    equal(undefined, sketch.element());

    deepEqual({width: 0, height: 0}, sketch.size());
    deepEqual({width: 0, height: 0}, sketch.containerSize());

    deepEqual(0, sketch.width());
    deepEqual(0, sketch.height());
});

QUnit.test('creme.D3Sketch.resize', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());
    deepEqual({width: 0, height: 0}, sketch.size());

    // If not bound, the resize() do nothing.
    element.get(0).style.width = '150px';
    deepEqual({width: 0, height: 0}, sketch.size());

    sketch.bind(element);

    equal(true, sketch.isBound());
    deepEqual({width: 150, height: 200}, sketch.size());

    element.get(0).style.width = '250px';
    deepEqual({width: 250, height: 200}, sketch.size());
});

QUnit.test('creme.D3Sketch.resize (events)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    sketch.bind(element);

    element.on('sketch-resize', this.mockListener('sketch-resize'));
    sketch.on('resize', this.mockListener('resize'));

    deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
    deepEqual([], this.mockListenerCalls('resize'));

    element.get(0).style.width = '150px';

    setTimeout(function() {
        deepEqual([
            ['sketch-resize', [{width: 150, height: 200}]]
        ], this.mockListenerJQueryCalls('sketch-resize'));
        deepEqual([
            ['resize', {width: 150, height: 200}]
        ], this.mockListenerCalls('resize'));
        start();
    }.bind(this), 50);

    stop(1);
});

QUnit.test('creme.D3Sketch.resize (ignore)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch({ignoreResize: true});

    sketch.bind(element);

    element.on('sketch-resize', this.mockListener('sketch-resize'));
    sketch.on('resize', this.mockListener('resize'));

    deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
    deepEqual([], this.mockListenerCalls('resize'));

    element.get(0).style.width = '150px';

    setTimeout(function() {
        deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
        deepEqual([], this.mockListenerCalls('resize'));
        deepEqual({width: 150, height: 200}, sketch.size());
        start();
    }.bind(this), 50);

    stop(1);
});

QUnit.test('creme.D3Sketch.clear', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.clear();
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);
    equal(true, sketch.isBound());

    sketch.svg().append('rect')
                .attr('x', 10)
                .attr('y', 10)
                .attr('width', 20)
                .attr('height', 20)
                .attr('fill', 'red');

    sketch.clear();
    equal('', sketch.svg().html());
});

QUnit.test('creme.D3Sketch.saveAs', function(assert) {
    var withFakeMethod = this.withFakeMethod.bind(this);
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.saveAs('my-test.svg');
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);

    this.assertRaises(function() {
        sketch.saveAs('my-test.svg');
    }, Error, 'Error: A callback is required to convert and save the SVG.');

    sketch.svg().append('rect')
                    .attr('x', 10)
                    .attr('y', 10)
                    .attr('width', 20)
                    .attr('height', 20)
                    .attr('fill', 'red');

    stop(1);

    setTimeout(function() {
        creme.svgAsBlob(function(expected) {
            withFakeMethod({instance: FileSaver, method: 'saveAs'}, function(faker) {
                sketch.saveAs(function() {
                    deepEqual(faker.calls(), [[expected, 'my-test.svg']]);
                    start();
                }, 'my-test.svg');
            });
        }, sketch.svg().node(), sketch.size());
    });
});

QUnit.test('creme.D3Sketch.saveAs (png)', function(assert) {
    var withFakeMethod = this.withFakeMethod.bind(this);
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();
    var noop = function() {};

    equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.saveAs(noop, 'my-test.png', {encoderType: 'image/png'});
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);

    this.assertRaises(function() {
        sketch.saveAs('my-test.png', {encoderType: 'image/png'});
    }, Error, 'Error: A callback is required to convert and save the SVG.');

    sketch.svg().append('rect')
                    .attr('x', 10)
                    .attr('y', 10)
                    .attr('width', 20)
                    .attr('height', 20)
                    .attr('fill', 'red');

    stop(1);

    creme.svgAsBlob(function(expected) {
        withFakeMethod({instance: FileSaver, method: 'saveAs'}, function(faker) {
            sketch.saveAs(function() {
                deepEqual(faker.calls(), [[expected, 'my-test.png']]);
                start();
            }, 'my-test.png', {encoderType: 'image/png'});
        });
    }, sketch.svg().node(), {width: 300, height: 200, encoderType: 'image/png'});
});

QUnit.test('creme.D3Sketch.asImage', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.asImage('my-test.svg');
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);

    this.assertRaises(function() {
        sketch.asImage('my-test.svg');
    }, Error, 'Error: A callback is required to convert the SVG as image.');

    sketch.svg().append('rect')
                    .attr('x', 10)
                    .attr('y', 10)
                    .attr('width', 20)
                    .attr('height', 20)
                    .attr('fill', 'red');

    var expectedURI = creme.svgAsDataURI(
        sketch.svg().node(), {width: 300, height: 200, encoderType: 'image/png'}
    );

    stop(1);

    sketch.asImage(function(image) {
        equal(image.src, expectedURI);
        start();
    }, {encoderType: 'image/png'});
});

QUnit.test('creme.D3Sketch.asImage (custom size)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.asImage('my-test.svg');
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);
    sketch.svg().append('rect')
                    .attr('x', 10)
                    .attr('y', 10)
                    .attr('width', 20)
                    .attr('height', 20)
                    .attr('fill', 'red');

    var expectedURI = creme.svgAsDataURI(
        sketch.svg().node(), {width: 450, height: 218, encoderType: 'image/png'}
    );

    stop(1);

    sketch.asImage(function(image) {
        equal(image.src, expectedURI);
        start();
    }, {width: 450, height: 218, encoderType: 'image/png'});
});

}(jQuery));
