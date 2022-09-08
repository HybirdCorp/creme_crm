/* globals QUnitSketchMixin */

(function($) {

QUnit.module("creme.D3Chart*", new QUnitMixin(QUnitSketchMixin));

QUnit.parametrize('creme.D3Chart (demo, empty)', {
    barchart: new creme.D3BarChart(),
    donutchart: new creme.D3DonutChart(),
    areachart: new creme.D3AreaChart(),
    groupbarchart: new creme.D3GroupBarChart(),
    stackbarchart: new creme.D3StackBarChart()
}, function(chart, assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);

    deepEqual($.extend(
        {drawOnResize: true},
        chart.defaultProps
    ), chart.props());

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();
    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
});

QUnit.parametrize('creme.D3Chart (demo, asImage, empty)', {
    barchart: new creme.D3BarChart(),
    donutchart: new creme.D3DonutChart(),
    areachart: new creme.D3AreaChart(),
    groupbarchart: new creme.D3GroupBarChart(),
    stackbarchart: new creme.D3StackBarChart()
}, function(chart, assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);

    stop(1);

    setTimeout(function() {
        chart.asImage(function(image) {
            equal(image.width, 300);
            equal(image.height, 200);
            start();
        }, {width: 300, height: 200});
    });
});

QUnit.parametrize('creme.D3Chart (demo, visible)', {
    barchart: new creme.D3BarChart(),
    donutchart: new creme.D3DonutChart(),
    areachart: new creme.D3AreaChart(),
    groupbarchart: new creme.D3GroupBarChart(),
    stackbarchart: new creme.D3StackBarChart()
}, function(chart, assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);

    equal(true, chart.props().visible);

    chart.draw();

    equal(false, sketch.svg().select('.d3-chart').classed('not-visible'));

    chart.prop('visible', false);
    chart.draw();

    equal(true, sketch.svg().select('.d3-chart').classed('not-visible'));
});

QUnit.parametrize('creme.D3Chart (demo, transition)', [
    true, false
], {
    barchart: new creme.D3BarChart(),
    donutchart: new creme.D3DonutChart(),
    areachart: new creme.D3AreaChart(),
    groupbarchart: new creme.D3GroupBarChart(),
    stackbarchart: new creme.D3StackBarChart()
}, function(transition, chart, assert) {
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.prop('transition', transition);
    chart.sketch(sketch);
    chart.model([{x: 'A', y: 1, g: 'Group A'}]);

    chart.draw();
    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
});

QUnit.parametrize('creme.D3BarChart (draw)', [
    [[{x: 'A', y: 0}], {}, {
        '.bar-chart .bars .bar': 1,
        '.bar-chart .limits .limit': 0,
        '.bar-chart .x .axis-title-label': {'text': ''},
        '.bar-chart .y .axis-title-label': {'text': ''}
    }],
    [[{x: 'A', y: 0}], {limits: [5, 10, 15], xAxisTitle: 'X'}, {
        '.bar-chart .bars .bar': 1,
        '.bar-chart .limits .limit': 3,
        '.bar-chart .x .axis-title-label': {'text': 'X'},
        '.bar-chart .y .axis-title-label': {'text': ''}
    }],
    [[
        {x: 'A', y: 0},
        {x: 'B', y: 5},
        {x: 'C', y: 38},
        {x: 'D', y: 12}
    ], {limits: [5, 10, 15], xAxisTitle: 'X', yAxisTitle: 'Y'}, {
        '.bar-chart .bars .bar': 4,
        '.bar-chart .limits .limit': 3,
        '.bar-chart .x .axis-title-label': {'text': 'X'},
        '.bar-chart .y .axis-title-label': {'text': 'Y'}
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3BarChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.D3BarChart (select)', function(assert) {
    var chart = new creme.D3BarChart({transition: false}); // disable transitions
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model([{x: 'A', y: 0}, {x: 'B', y: 5}, {x: 'C', y: 38}, {x: 'D', y: 12}]);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
    deepEqual([], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.bar-chart .selected': 0
    });

    chart.selection().select(2);

    deepEqual([{x: 'C', y: 38, selected: true}], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.bar-chart .selected': 1
    });

    // toggles selection
    sketch.svg().select('.bar-chart .bars .bar rect').dispatch('click');

    deepEqual([{x: 'A', y: 0, selected: true}], chart.selection().selected());
});

QUnit.parametrize('creme.D3DonutChart (draw)', [
    [[{x: 'A', y: 1}], {}, {
        '.donut-chart .slices .slice': 1,
        '.legend .legend-item': 1
    }],
    [[{x: 'A', y: 1}], {showLegend: false}, {
        '.donut-chart .slices .slice': 1,
        '.legend .legend-item': 0
    }],
    [[{x: 'A', y: 1}, {x: 'B', y: 2}, {x: 'C', y: 3}, {x: 'D', y: 4}], {band: 0}, {
        '.donut-chart .slices .slice': 4,
        '.legend .legend-item': 4
    }],
    // zero-y are ignored in slice rending
    [[{x: 'A', y: 1}, {x: 'B', y: 2}, {x: 'C', y: 0}, {x: 'D', y: 4}], {}, {
        '.donut-chart .slices .slice': 3,
        '.legend .legend-item': 4
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3DonutChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.D3DonutChart (select)', function(assert) {
    var chart = new creme.D3DonutChart({transition: false}); // disable transitions
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model([{x: 'A', y: 1}, {x: 'B', y: 5}, {x: 'C', y: 38}, {x: 'D', y: 12}]);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
    deepEqual([], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.donut-chart .selected': 0
    });

    chart.selection().select(2);

    deepEqual([{x: 'C', y: 38, selected: true}], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.donut-chart .selected': 1
    });

    // toggles selection
    sketch.svg().select('.donut-chart .slices .slice path').dispatch('click');

    deepEqual([{x: 'A', y: 1, selected: true}], chart.selection().selected());
});

QUnit.parametrize('creme.D3AreaChart (draw)', [
    [[{x: 'A', y: 0}], {}, {
        '.area-chart .area': 1
    }],
    [[{x: 'A', y: 0}, {x: 'B', y: 0}, {x: 'C', y: 0}, {x: 'D', y: 0}], {}, {
        '.area-chart .area': 1
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3AreaChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.parametrize('creme.D3GroupBarChart (hierarchy)', [
    [[], []],
    [
        [{x: 'A', y: 0, g: 'Group A'}],
        [
            {
                group: 'Group A',
                items: [
                    {x: 'A', y: 0, index: 0, data: {x: 'A', y: 0, g: 'Group A'}}
                ]
            }
        ]
    ],
    [
        [
            {x: 'A', y: 0, g: 'Group A'},
            {x: 'B', y: 0, g: 'Group A'},
            {x: 'C', y: 0, g: 'Group B'},
            {x: 'A', y: 0, g: 'Group C'}
        ],
        [
            {
                group: 'Group A',
                items: [
                    {x: 'A', y: 0, index: 0, data: {x: 'A', y: 0, g: 'Group A'}},
                    {x: 'B', y: 0, index: 1, data: {x: 'B', y: 0, g: 'Group A'}}
                ]
            },
            {
                group: 'Group B',
                items: [
                    {x: 'C', y: 0, index: 2, data: {x: 'C', y: 0, g: 'Group B'}}
                ]
            },
            {
                group: 'Group C',
                items: [
                    {x: 'A', y: 0, index: 3, data: {x: 'A', y: 0, g: 'Group C'}}
                ]
            }
        ]
    ]
], function(input, expected, assert) {
    var chart = new creme.D3GroupBarChart();
    deepEqual(chart.hierarchy(input, {groupId: function(d) { return d.g; }}), expected);
});

QUnit.parametrize('creme.D3GroupBarChart (draw)', [
    [[{x: 'A', y: 0, group: 'Group A'}], {}, {
        '.group-bar-chart .bar': 1,
        '.group-bar-chart .group': 1,
        '.limits .limit': 0,
        '.legend .legend-item': 1
    }],
    [[{x: 'A', y: 0, group: 'Group A'}], {showLegend: false}, {
        '.group-bar-chart .bar': 1,
        '.group-bar-chart .group': 1,
        '.limits .limit': 0,
        '.legend .legend-item': 0
    }],
    [[{x: 'A', y: 0, group: 'Group A'}], {limits: [12, 754]}, {
        '.group-bar-chart .bar': 1,
        '.group-bar-chart .group': 1,
        '.limits .limit': 2,
        '.legend .legend-item': 1
    }],
    [[
        {x: 'A', y: 0, group: 'Group A'},
        {x: 'B', y: 97, group: 'Group A'},
        {x: 'C', y: 5, group: 'Group B'},
        {x: 'A', y: 12, group: 'Group C'}
     ], {}, {
        '.group-bar-chart .bar': 4,
        '.group-bar-chart .group': 3,
        '.limits .limit': 0,
        '.legend .legend-item': 3
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3GroupBarChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.D3GroupBarChart (select)', function(assert) {
    var chart = new creme.D3GroupBarChart({transition: false}); // disable transitions
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model([
        {x: 'A', y: 0, group: 'Group A'},
        {x: 'B', y: 97, group: 'Group A'},
        {x: 'C', y: 5, group: 'Group B'},
        {x: 'A', y: 12, group: 'Group C'}
    ]);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
    deepEqual([], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.group-bar-chart .selected': 0
    });

    chart.selection().select(2);

    deepEqual([{x: 'C', y: 5, group: 'Group B', selected: true}], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.group-bar-chart .selected': 1
    });

    // toggles selection
    sketch.svg().select('.group-bar-chart rect').dispatch('click');

    deepEqual([{x: 'A', y: 0, group: 'Group A', selected: true}], chart.selection().selected());
});


QUnit.parametrize('creme.D3StackBarChart (hierarchy)', [
    [[], []],
    [
        [{x: 'A', y: 0, g: 'Group A'}],
        [{
            group: 'Group A',
            items: [
                {x: 'A', y: 0, index: 0, startY: 0, endY: 0, data: {x: 'A', y: 0, g: 'Group A'}}
            ]
        }]
    ],
    [
        [
            {x: 'A', y: 5, g: 'Group A'},
            {x: 'B', y: 12, g: 'Group A'},
            {x: 'C', y: 23, g: 'Group B'},
            {x: 'A', y: 8, g: 'Group C'},
            {x: 'B', y: 71, g: 'Group C'},
            {x: 'C', y: 6, g: 'Group C'}
        ],
        [
            {
                group: 'Group A',
                items: [
                    {x: 'A', y: 5,  index: 0, startY: 0, endY: 5,      data: {x: 'A', y: 5,  g: 'Group A'}},
                    {x: 'B', y: 12, index: 1, startY: 5, endY: 5 + 12, data: {x: 'B', y: 12, g: 'Group A'}}
                ]
            },
            {
                group: 'Group B',
                items: [
                    {x: 'C', y: 23, index: 2, startY: 0, endY: 23, data: {x: 'C', y: 23, g: 'Group B'}}
                ]
            },
            {
                group: 'Group C',
                items: [
                    {x: 'A', index: 3, y: 8,  startY: 0,      endY: 8,          data: {x: 'A', y: 8,  g: 'Group C'}},
                    {x: 'B', index: 4, y: 71, startY: 8,      endY: 8 + 71,     data: {x: 'B', y: 71, g: 'Group C'}},
                    {x: 'C', index: 5, y: 6,  startY: 8 + 71, endY: 8 + 71 + 6, data: {x: 'C', y: 6,  g: 'Group C'}}
                ]
            }
        ]
    ]
], function(input, expected, assert) {
    var chart = new creme.D3StackBarChart();
    deepEqual(chart.hierarchy(input, {groupId: function(d) { return d.g; }}), expected);
});

QUnit.parametrize('creme.D3StackBarChart (draw)', [
    [[{x: 'A', y: 0, group: 'Group A'}], {}, {
        '.stack-bar-chart .bar': 1,
        '.stack-bar-chart .stack': 1,
        '.limits .limit': 0,
        '.legend .legend-item': 1
    }],
    [[{x: 'A', y: 0, group: 'Group A'}], {showLegend: false}, {
        '.stack-bar-chart .bar': 1,
        '.stack-bar-chart .stack': 1,
        '.limits .limit': 0,
        '.legend .legend-item': 0
    }],
    [[{x: 'A', y: 0, group: 'Group A'}], {limits: [12, 754]}, {
        '.stack-bar-chart .bar': 1,
        '.stack-bar-chart .stack': 1,
        '.limits .limit': 2,
        '.legend .legend-item': 1
    }],
    [[
        {x: 'A', y: 0, group: 'Group A'},
        {x: 'B', y: 97, group: 'Group A'},
        {x: 'C', y: 5, group: 'Group B'},
        {x: 'A', y: 12, group: 'Group C'}
     ], {}, {
        '.stack-bar-chart .bar': 4,
        '.stack-bar-chart .stack': 3,
        '.limits .limit': 0,
        '.legend .legend-item': 3
    }]
], function(data, options, expected, assert) {
    var chart = new creme.D3StackBarChart(options);
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

QUnit.test('creme.D3StackBarChart (select)', function(assert) {
    var chart = new creme.D3StackBarChart({transition: false}); // disable transitions
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model([
        {x: 'A', y: 0, group: 'Group A'},
        {x: 'B', y: 97, group: 'Group A'},
        {x: 'C', y: 5, group: 'Group B'},
        {x: 'A', y: 12, group: 'Group C'}
    ]);

    equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    equal(1, sketch.svg().select('.d3-chart').size());
    deepEqual([], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.stack-bar-chart .selected': 0
    });

    chart.selection().select(2);

    deepEqual([{x: 'C', y: 5, group: 'Group B', selected: true}], chart.selection().selected());
    this.assertD3Nodes(sketch.svg(), {
        '.stack-bar-chart .selected': 1
    });

    // toggles selection
    sketch.svg().select('.stack-bar-chart rect').dispatch('click');

    deepEqual([{x: 'A', y: 0, group: 'Group A', selected: true}], chart.selection().selected());
});

}(jQuery));
