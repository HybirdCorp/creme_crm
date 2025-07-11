/* globals QUnitSketchMixin */

(function($) {

QUnit.module("creme.reports.D3TubeChart", new QUnitMixin(QUnitSketchMixin));

QUnit.test('creme.D3TubeChart (empty)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new creme.D3TubeChart();

    chart.sketch(sketch);

    assert.deepEqual($.extend({drawOnResize: true}, chart.defaultProps), chart.props());
    assert.equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();
    chart.draw();

    assert.equal(1, sketch.svg().select('.d3-chart').size());
});

QUnit.test('creme.D3TubeChart (asImage, empty)', function(assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));
    var chart = new creme.D3TubeChart();

    chart.sketch(sketch);

    var done = assert.async();

    setTimeout(function() {
        chart.asImage(function(image) {
            assert.equal(image.width, 300);
            assert.equal(image.height, 200);
            done();
        }, {width: 300, height: 200});
    });
});

QUnit.parametrize('creme.D3TubeChart (draw)', [
    [[{x: 'A', y: 1}], {}, {
        '.tube-chart .bars .bar': 1,
        '.tube-chart .legend .legend-item': 1,
        '.tube-chart .x .axis-title-label': {'text': ''}
    }],
    [[{x: 'A', y: 1}], {xAxisTitle: 'X'}, {
        '.tube-chart .bars .bar': 1,
        '.tube-chart .legend .legend-item': 1,
        '.tube-chart .x .axis-title-label': {'text': 'X'}
    }],
    [[{x: 'A', y: 1}, {x: 'B', y: 0}], {xAxisTitle: 'X without zeros'}, {
        '.tube-chart .bars .bar': 1,
        '.tube-chart .legend .legend-item': 2,
        '.tube-chart .x .axis-title-label': {'text': 'X without zeros'}
    }],
    [[
        {x: 'A', y: 1},
        {x: 'B', y: 5},
        {x: 'C', y: 38},
        {x: 'D', y: 12}
    ], {xAxisTitle: 'X'}, {
        '.tube-chart .bars .bar': 4,
        '.tube-chart .legend .legend-item': 4,
        '.tube-chart .x .axis-title-label': {'text': 'X'}
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3TubeChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    assert.equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    assert.equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.D3TubeChart (select)', function(assert) {
    var chart = new creme.D3TubeChart({transition: false}); // disable transitions
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model([{x: 'A', y: 1}, {x: 'B', y: 5}, {x: 'C', y: 38}, {x: 'D', y: 12}]);

    assert.equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    assert.equal(1, sketch.svg().select('.d3-chart').size());
    assert.deepEqual([], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.tube-chart .selected': 0
    });

    chart.selection().select(2);

    assert.deepEqual([{x: 'C', y: 38, selected: true}], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.tube-chart .selected': 1
    });

    // toggles selection
    sketch.svg().select('.tube-chart .bars .bar rect').dispatch('click');

    assert.deepEqual([{x: 'A', y: 1, selected: true}], chart.selection().selected());
});

}(jQuery));
