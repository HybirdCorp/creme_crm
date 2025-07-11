(function($) {

QUnit.module("creme.D3Sketch", new QUnitMixin(QUnitEventMixin));

QUnit.test('creme.D3Sketch', function(assert) {
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());

    assert.equal(undefined, sketch.svg());
    assert.equal(undefined, sketch.element());

    assert.deepEqual({width: 0, height: 0}, sketch.size());
    assert.deepEqual({width: 0, height: 0}, sketch.containerSize());

    assert.deepEqual(0, sketch.width());
    assert.deepEqual(0, sketch.height());
});

QUnit.test('creme.D3Sketch.bind', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">');
    var sketch = new creme.D3Sketch().bind(element);

    assert.equal(true, sketch.isBound());
    assert.equal(element, sketch.element());
    assert.ok(sketch.svg() !== undefined);

    assert.deepEqual({width: 300, height: 200}, sketch.size());
    assert.deepEqual({width: 300, height: 200}, sketch.containerSize());

    assert.deepEqual(300, sketch.width());
    assert.deepEqual(200, sketch.height());

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

    assert.equal(true, sketch.isBound());
    assert.equal(element, sketch.element());
    assert.ok(sketch.svg() !== undefined);

    sketch.unbind();

    assert.equal(undefined, sketch.svg());
    assert.equal(undefined, sketch.element());

    assert.deepEqual({width: 0, height: 0}, sketch.size());
    assert.deepEqual({width: 0, height: 0}, sketch.containerSize());

    assert.deepEqual(0, sketch.width());
    assert.deepEqual(0, sketch.height());
});

QUnit.test('creme.D3Sketch.resize', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());
    assert.deepEqual({width: 0, height: 0}, sketch.size());

    // If not bound, the resize() do nothing.
    element.get(0).style.width = '150px';
    assert.deepEqual({width: 0, height: 0}, sketch.size());

    sketch.bind(element);

    assert.equal(true, sketch.isBound());
    assert.deepEqual({width: 150, height: 200}, sketch.size());

    element.get(0).style.width = '250px';
    assert.deepEqual({width: 250, height: 200}, sketch.size());
});

QUnit.test('creme.D3Sketch.resize (events)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    sketch.bind(element);

    element.on('sketch-resize', this.mockListener('sketch-resize'));
    sketch.on('resize', this.mockListener('resize'));

    assert.deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
    assert.deepEqual([], this.mockListenerCalls('resize'));

    element.get(0).style.width = '150px';

    var done = assert.async();

    setTimeout(function() {
        assert.deepEqual([
            ['sketch-resize', [{width: 150, height: 200}]]
        ], this.mockListenerJQueryCalls('sketch-resize'));
        assert.deepEqual([
            ['resize', {width: 150, height: 200}]
        ], this.mockListenerCalls('resize'));
        done();
    }.bind(this), 50);
});

QUnit.test('creme.D3Sketch.resize (ignore)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch({ignoreResize: true});

    sketch.bind(element);

    element.on('sketch-resize', this.mockListener('sketch-resize'));
    sketch.on('resize', this.mockListener('resize'));

    assert.deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
    assert.deepEqual([], this.mockListenerCalls('resize'));

    element.get(0).style.width = '150px';

    var done = assert.async();

    setTimeout(function() {
        assert.deepEqual([], this.mockListenerJQueryCalls('sketch-resize'));
        assert.deepEqual([], this.mockListenerCalls('resize'));
        assert.deepEqual({width: 150, height: 200}, sketch.size());
        done();
    }.bind(this), 50);
});

QUnit.test('creme.D3Sketch.clear', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());

    this.assertRaises(function() {
        sketch.clear();
    }, Error, 'Error: D3Sketch is not bound');

    sketch.bind(element);
    assert.equal(true, sketch.isBound());

    sketch.svg().append('rect')
                .attr('x', 10)
                .attr('y', 10)
                .attr('width', 20)
                .attr('height', 20)
                .attr('fill', 'red');

    sketch.clear();
    assert.equal('', sketch.svg().html());
});

QUnit.test('creme.D3Sketch.saveAs', function(assert) {
    var withFakeMethod = this.withFakeMethod.bind(this);
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());

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

    var done = assert.async();

    setTimeout(function() {
        creme.svgAsBlob(function(expected) {
            withFakeMethod({instance: FileSaver, method: 'saveAs'}, function(faker) {
                sketch.saveAs(function() {
                    assert.deepEqual(faker.calls(), [[expected, 'my-test.svg']]);
                    done();
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

    assert.equal(false, sketch.isBound());

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

    var done = assert.async();

    creme.svgAsBlob(function(expected) {
        withFakeMethod({instance: FileSaver, method: 'saveAs'}, function(faker) {
            sketch.saveAs(function() {
                assert.deepEqual(faker.calls(), [[expected, 'my-test.png']]);
                done();
            }, 'my-test.png', {encoderType: 'image/png'});
        });
    }, sketch.svg().node(), {width: 300, height: 200, encoderType: 'image/png'});
});

QUnit.test('creme.D3Sketch.asImage', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());

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

    var done = assert.async();

    sketch.asImage(function(image) {
        assert.equal(image.src, expectedURI);
        done();
    }, {encoderType: 'image/png'});
});

QUnit.test('creme.D3Sketch.asImage (custom size)', function(assert) {
    var element = $('<div style="width: 300px; height: 200px;">').appendTo(this.qunitFixture());
    var sketch = new creme.D3Sketch();

    assert.equal(false, sketch.isBound());

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

    var done = assert.async();

    sketch.asImage(function(image) {
        assert.equal(image.src, expectedURI);
        done();
    }, {width: 450, height: 218, encoderType: 'image/png'});
});

}(jQuery));
