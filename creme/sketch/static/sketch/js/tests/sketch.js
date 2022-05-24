(function($) {

QUnit.module("creme.D3Sketch", new QUnitMixin());

QUnit.test('creme.D3Sketch', function(assert) {
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());

    equal(undefined, sketch.svg());
    equal(undefined, sketch.element());

    deepEqual({width: 0, height: 0}, sketch.size());
    deepEqual({width: 0, height: 0}, sketch.preferredSize());

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
    deepEqual({width: 300, height: 200}, sketch.preferredSize());

    deepEqual(300, sketch.width());
    deepEqual(200, sketch.height());

    this.assertRaises(function() {
        sketch.bind(element);
    }, Error, 'Error: D3Sketch is already bound');
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
    deepEqual({width: 0, height: 0}, sketch.preferredSize());

    deepEqual(0, sketch.width());
    deepEqual(0, sketch.height());
});

QUnit.test('creme.D3Sketch.resize', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    equal(false, sketch.isBound());
    deepEqual({width: 0, height: 0}, sketch.size());

    // If not bound, the resize() do nothing.
    sketch.resize({width: 150});
    deepEqual({width: 0, height: 0}, sketch.size());

    sketch.bind(element);

    equal(true, sketch.isBound());
    deepEqual({width: 300, height: 200}, sketch.size());

    sketch.resize({width: 150});
    deepEqual({width: 150, height: 200}, sketch.size());

    sketch.resize({width: 250, height: 500});
    deepEqual({width: 250, height: 500}, sketch.size());

    // Use preferredSize as default
    sketch.resize();
    deepEqual({width: 300, height: 200}, sketch.size());
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
        }, sketch.svg().node(), {width: 300, height: 200});
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
    }, {width: 300, height: 200, encoderType: 'image/png'});
});

}(jQuery));
