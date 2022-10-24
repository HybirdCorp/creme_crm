/* globals QUnitSketchMixin, FakeD3Chart */

(function($) {

QUnit.module("creme.D3Chart", new QUnitMixin(QUnitSketchMixin));

QUnit.test('creme.D3Chart', function(assert) {
    var chart = new creme.D3Chart();

    equal(undefined, chart.model());
    equal(undefined, chart.sketch());
    equal(false, chart.hasCanvas());
    deepEqual({drawOnResize: true}, chart.props());
    deepEqual({}, chart.exportProps());
    equal("g { font: 10px sans-serif; }", chart.exportStyle());
});

QUnit.test('creme.D3Chart.sketch', function(assert) {
    var sketch = new creme.D3Sketch();
    var chart = new creme.D3Chart();

    equal(undefined, chart.sketch());
    equal(false, chart.hasCanvas());

    chart.sketch(sketch);

    deepEqual(sketch, chart.sketch());
    equal(true, chart.hasCanvas());
});

QUnit.test('creme.D3Chart.sketch (replace)', function(assert) {
    var sketch = new creme.D3Sketch();
    var chart = new creme.D3Chart();

    chart.sketch(sketch);

    deepEqual(sketch, chart.sketch());
    equal(true, chart.hasCanvas());

    var sketch2 = new creme.D3Sketch();
    chart.sketch(sketch2);

    deepEqual(sketch2, chart.sketch());
    equal(true, chart.hasCanvas());
});

QUnit.parametrize('creme.D3Chart.sketch (invalid)', [
    null, [], new creme.D3Chart(), 'invalid', {}
], function(sketch, assert) {
    var chart = new creme.D3Chart();

    this.assertRaises(function() {
        chart.sketch(sketch);
    }, Error, 'Error: ${sketch} is not a creme.D3Sketch'.template({sketch: sketch}));

    equal(false, chart.hasCanvas());
});

QUnit.parametrize('creme.D3Chart.model', [
    [[], []],
    [[1, 2, 3], [1, 2, 3]],
    [new creme.model.Array([3, 2, 1]), [3, 2, 1]]
], function(model, expected, assert) {
    var chart = new creme.D3Chart();

    chart.model(model);

    ok(chart.model() instanceof creme.model.Array);
    deepEqual(expected, chart.model().all());
});

QUnit.parametrize('creme.D3Chart.model (invalid)', [
    null, [], new creme.D3Chart(), 'invalid', {}
], function(model, assert) {
    var chart = new creme.D3Chart();

    this.assertRaises(function() {
        chart.model(model);
    }, Error, 'Error: ${model} is not a valid data model'.template({model: model}));

    equal(undefined, chart.model());
});

QUnit.test('creme.D3Chart.sketch (replace)', function(assert) {
    var chart = new creme.D3Chart();
    var model = new creme.model.Array([1, 2, 3]);
    var model2 = new creme.model.Array([3, 2, 1]);

    chart.model(model);

    deepEqual(model, chart.model());

    chart.model(model2);

    deepEqual(model2, chart.model());
});

QUnit.test('creme.D3Chart.draw (no sketch)', function(assert) {
    var chart = new creme.D3Chart();

    this.assertRaises(function() {
        chart.draw();
    }, Error, 'Error: D3Chart must have a target sketch to draw on');
});

QUnit.test('creme.D3Chart.draw (not bound)', function(assert) {
    var chart = new creme.D3Chart().sketch(new creme.D3Sketch());

    this.assertRaises(function() {
        chart.draw();
    }, Error, 'Error: D3Chart sketch is not bound');
});

QUnit.test('creme.D3Chart.draw (not implemented)', function(assert) {
    // Note : ignore resize here or the observer will trigger a draw() later
    // that throws an 'Not implement' excaption and trash the other test execution.
    var sketch = new creme.D3Sketch({ignoreResize: true}).bind($('<div>'));
    var chart = new creme.D3Chart().sketch(sketch);

    this.assertRaises(function() {
        chart.draw();
    }, Error, 'Error: Not implemented');
});

QUnit.test('creme.D3Chart.draw (empty)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch);

    equal(0, sketch.svg().select('rect').size());

    chart.draw();

    equal(0, sketch.svg().select('rect').size());
});

QUnit.test('creme.D3Chart.draw (array)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch);

    chart.model([{color: 'red'}, {color: 'blue'}]);
    chart.draw();

    this.equalHtml($(
        '<rect x="3" y="7" width="52" height="107" fill="red"></rect>' +
        '<rect x="3" y="114" width="52" height="107" fill="blue"></rect>'
    ), sketch.svg().node());
});


QUnit.parametrize('creme.D3Chart.props.drawOnResize', [
    [true, '<rect x="3" y="7" width="52" height="107" fill="red"></rect>'],
    [false, '']
], function(drawOnResize, expected, assert) {
    var element = $('<div>');
    var sketch = new creme.D3Sketch().bind(element);
    var chart = new FakeD3Chart({
        drawOnResize: drawOnResize
    }).sketch(sketch);

    chart.model([{color: 'red'}]);

    this.equalHtml('', sketch.svg().node());

    element.css({width: 12, height: 12}).trigger('resize');

    setTimeout(function() {
        this.equalHtml(expected, sketch.svg().node());
        start();
    }.bind(this), 300);

    stop(1);
});

QUnit.test('creme.D3Chart.saveAs', function(assert) {
    var withFakeMethod = this.withFakeMethod.bind(this);

    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch);
    var expectedBlob = new Blob([
        '<?xml version="1.0" standalone="no"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="300">\n',
            '<style>g { font: 10px sans-serif; }</style>',
            '<rect x="3" y="7" width="52" height="107" fill="red"></rect>',
            '<rect x="3" y="114" width="52" height="107" fill="blue"></rect>',
        '\n</svg>'
    ], { type: "image/svg+xml;charset=utf-8" });

    chart.model([{color: 'red'}, {color: 'blue'}]);

    stop(1);

    setTimeout(function() {
        withFakeMethod({instance: FileSaver, method: 'saveAs'}, function(faker) {
            chart.saveAs(function() {
                deepEqual(faker.calls(), [[expectedBlob, 'my-test.svg']]);
                start();
            }, 'my-test.svg', {width: 300, height: 200});
        });
    });
});

QUnit.test('creme.D3Chart.asImage', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch);
    var expectedURI = creme.svgAsDataURI(this.createD3Node(
        '<style>g { font: 10px sans-serif; }</style>' +
        '<rect x="3" y="7" width="52" height="107" fill="red"></rect>' +
        '<rect x="3" y="114" width="52" height="107" fill="blue"></rect>'
    ).node(), {width: 300, height: 200});

    chart.model([{color: 'red'}, {color: 'blue'}]);

    stop(1);

    setTimeout(function() {
        chart.asImage(function(image) {
            equal(image.width, 300);
            equal(image.height, 200);
            equal(image.src, expectedURI);
            start();
        }, {width: 300, height: 200});
    });
});

QUnit.test('creme.D3Chart.model (append)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch).model([{color: 'red'}]);

    chart.draw();

    deepEqual(['red'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));

    chart.model().append({color: 'blue'});

    deepEqual([{color: 'red'}, {color: 'blue'}], chart.model().all());
    deepEqual(['red', 'blue'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));
});

QUnit.test('creme.D3Chart.model (reset)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch).model([{color: 'red'}]);

    chart.draw();

    deepEqual(['red'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));

    chart.model().reset([{color: 'rgb(0, 128, 64)'}]);

    stop(1);

    setTimeout(function() {
        deepEqual([{color: 'rgb(0, 128, 64)'}], chart.model().all());
        deepEqual(['rgb(0, 128, 64)'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));
        start();
    }.bind(this), 50);
});

QUnit.test('creme.D3Chart.model (update)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch).model([{color: 'red'}]);

    chart.draw();

    deepEqual(['red'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));

    chart.model().set({color: 'rgb(64, 128, 64)'}, 0);

    stop(1);

    setTimeout(function() {
        deepEqual([{color: 'rgb(64, 128, 64)'}], chart.model().all());
        deepEqual(['rgb(64, 128, 64)'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));
        start();
    }.bind(this), 50);
});

QUnit.test('creme.D3Chart.model (remove)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new FakeD3Chart().sketch(sketch).model([{color: 'red'}]);

    chart.draw();

    deepEqual(['red'], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));

    chart.model().pop(0);

    deepEqual([], chart.model().all());
    deepEqual([], this.mapD3Attr('fill', sketch.svg().selectAll('rect')));
});

}(jQuery));
