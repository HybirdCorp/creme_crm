/* globals QUnitSketchMixin */

(function($) {

QUnit.module("creme.reports.ReportD3Chart*BrickController", new QUnitMixin(QUnitEventMixin,
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
    },

    createBrickWidget: function(html) {
        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    },

    createD3ChartSwappableContentHtml: function(options) {
        options = $.extend({
            charts: [],
            data: [],
            props: {}
        }, options || {});

        if (Object.isEmpty(options.data)) {
            return '<div class="brick-empty">No data</div>';
        } else {
            return (
//                '<div class="brick-graph-header clearfix">' +
                '<div class="brick-chart-header clearfix">' +
//                    '<div class="graph-controls">' +
                    '<div class="chart-controls">' +
//                        '<div class="graph-control graph-controls-type">' +
                        '<div class="chart-control chart-controls-plot">' +
//                            '<span class="graph-control-name">Graph</span>' +
                            '<span class="chart-control-name">Graph</span>' +
//                            '<select class="graph-control-value" data-switch-alt="Type of graph">' +
                            '<select class="chart-control-value" data-switch-alt="Type of graph">' +
                                '${charts}' +
                            '</select>' +
                        '</div>' +
//                        '<div class="graph-control graph-controls-sort">' +
                        '<div class="chart-control chart-controls-sort">' +
//                            '<span class="graph-control-name">Sort</span>' +
                            '<span class="chart-control-name">Sort</span>' +
//                            '<select class="graph-control-value" data-switch-alt="Ordering">' +
                            '<select class="chart-control-value" data-switch-alt="Ordering">' +
                                '<option value="ASC">Ascending</option>' +
                                '<option value="DESC">Descending</option>' +
                            '</select>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<div class="brick-d3-content"></div>' +
                '<script type="application/json" class="sketch-chart-data"><!-- ${data} --></script>' +
                '<script type="application/json" class="sketch-chart-props"><!-- ${props} --></script>'
            ).template({
                charts: options.charts.map(function(chart) {
                    return '<option value="${value}" ${selected}>${label}</option>'.template({
                        value: chart.name,
                        label: chart.label,
                        selected: chart.selected ? 'selected' : ''
                    });
                }).join(''),
                data: JSON.stringify(options.data || {}),
                props: JSON.stringify(options.props || {})
            });
        }
    },

    createD3ChartBrickHtml: function(options) {
        return this.createBrickHtml($.extend({
            content: this.createD3ChartSwappableContentHtml(options)
        }, options));
    },

    createBrick: function(html) {
        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return brick;
    },

    createD3ChartListBrickHtml: function(options) {
        options = $.extend({
            graphs: []
        }, options || {});

        var self = this;

        var content = (
            '<table class="brick-table-content">' +
                '<tbody>${graphs}</tbody>' +
            '</table>'
        ).template({
            graphs: options.graphs.map(function(graph) {
                return (
//                    '<tr data-graph-id="${id}" class="graph-row-header"><td></td></tr>' +
                    '<tr data-chart-id="${id}" class="chart-row-header"><td></td></tr>' +
//                    '<tr class="graph-row-title">' +
                    '<tr class="chart-row-title">' +
                        '<td>' +
//                            '<div class="graph-accordion-title" data-graph-id="${id}">' +
                            '<div class="chart-accordion-title" data-chart-id="${id}">' +
//                                '<div class="graph-accordion-toggle"></div>' +
                                '<div class="chart-accordion-toggle"></div>' +
//                                '<div class="graph-accordion-title">${title}</div>' +
                                '<div class="chart-accordion-text">${title}</div>' +
//                                '<div class="graph-accordion-toggle"></div>' +
                                '<div class="chart-accordion-toggle"></div>' +
                            '</div>' +
                        '</td>' +
                    '</tr>' +
//                    '<tr data-graph-id="${id}" class="graph-row graph-row-collapsed ${empty}">' +
                    '<tr data-chart-id="${id}" class="chart-row chart-row-collapsed ${empty}">' +
//                        '<td class="reports-graph-brick">${chart}</td>' +
                        '<td class="reports-chart-brick">${chart}</td>' +
                    '</tr>'
                ).template({
                    id: graph.id,
                    title: graph.title || 'Graph ${id}'.template(graph),
                    empty: Object.isEmpty(graph.chart.data) ? 'is-empty' : '',
                    chart: self.createD3ChartSwappableContentHtml(graph.chart)
                });
            }).join('')
        });

        return this.createBrickHtml($.extend({
            content: content
        }, options));
    }
}));

QUnit.test('creme.ReportD3ChartBrickController (empty)', function(assert) {
    var html = this.createD3ChartBrickHtml();
    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController();

    controller.registerActions(brick);
    controller.bind(brick);

    assert.equal(controller.swapper(), undefined);
});

QUnit.test('creme.ReportD3ChartBrickController (missing chart)', function(assert) {
    var html = this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' },
            { name: 'pie', label: 'Pie Chart', selected: true }
        ],
        data: [
            { x: 'A', y: 1 }
        ]
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController();

    controller.registerActions(brick);
    controller.bind(brick);

    var swapper = controller.swapper();

    assert.equal(swapper.sketch().isBound(), true);
    assert.equal(swapper.chart(), undefined);
});

QUnit.test('creme.ReportD3ChartBrickController (swap chart)', function(assert) {
    var html = this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' },
            { name: 'pie', label: 'Pie Chart', selected: true }
        ],
        data: [
            { x: 'A', y: 1 }
        ],
        props: {
            pie: { band: 42 },
            bar: { xAxisTitle: 'X Axis', yAxisTitle: 'Y Axis' }
        }
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController({
        charts: {
            bar: new creme.D3BarChart({margin: 4}),
            pie: new creme.D3DonutChart({margin: 8})
        }
    });

    controller.registerActions(brick);
    controller.bind(brick);

    var swapper = controller.swapper();

    assert.equal(swapper.sketch().isBound(), true);
    assert.equal(swapper.chart() instanceof creme.D3DonutChart, true, 'is creme.D3DonutChart');

    var props = swapper.chart().props();
    assert.equal(props.band, 42);

    swapper.swapChart('bar');
    assert.equal(swapper.chart() instanceof creme.D3BarChart, true, 'is creme.D3BarChart');

    props = swapper.chart().props();
    assert.equal(props.xAxisTitle, 'X Axis');
    assert.equal(props.yAxisTitle, 'Y Axis');
});

QUnit.test('creme.ReportD3ChartBrickController (visibility)', function(assert) {
    var html = this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' },
            { name: 'pie', label: 'Pie Chart', selected: true }
        ],
        data: [
            { x: 'A', y: 1 }
        ],
        props: {
            pie: { band: 42 },
            bar: { xAxisTitle: 'X Axis', yAxisTitle: 'Y Axis' }
        }
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController({
        charts: {
            bar: new creme.D3BarChart({margin: 4}),
            pie: new creme.D3DonutChart({margin: 8})
        }
    });

    controller.registerActions(brick);
    controller.bind(brick);

    var sketch = controller.swapper().sketch();
//    var chartSelect = brick.element().find('.graph-controls-type .graph-control-value');
    var chartSelect = brick.element().find('.chart-controls-plot .chart-control-value');

    // At initial state, only the default pie chart is rendered
    assert.equal('pie', chartSelect.val());
    assert.equal(sketch.svg().selectAll('.d3-chart').size(), 1);
    assert.equal(sketch.svg().select('.d3-chart').attr('class'), 'donut-chart d3-chart');

    // Select the bar !
    chartSelect.val('bar').trigger('change');

    // Now both pie & bar charts are rendered but the first one is "not-visible"
    assert.equal(controller.swapper().chart() instanceof creme.D3BarChart, true, 'is creme.D3BarChart');

    assert.equal(sketch.svg().selectAll('.d3-chart').size(), 2);
    assert.equal(sketch.svg().select('.donut-chart').attr('class'), 'donut-chart d3-chart not-visible');
    assert.equal(sketch.svg().select('.bar-chart').attr('class'), 'bar-chart d3-chart');
});

QUnit.parametrize('creme.ReportD3ChartBrickController (selection)', [
    [[{ x: 'A', y: 1 }], []],
    [[{ x: 'A', y: 1, url: '/mock/A' }], ['/mock/A']]
], function(data, expectedCalls, assert) {
    var html = this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' }
        ],
        data: data
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController({
        charts: {
            // Disable transition to get the "selected" state immediately
            bar: new creme.D3BarChart({ transition: false })
        }
    });

    controller.registerActions(brick);
    controller.bind(brick);

    var sketch = controller.swapper().sketch();

    controller.swapper().draw();

    assert.equal(sketch.svg().select('.bars .bar').attr('class'), 'bar');
    assert.deepEqual([], this.mockRedirectCalls());

    sketch.svg().select('.bars .bar rect').dispatch('click');

    assert.equal(sketch.svg().select('.bars .bar').attr('class'), 'bar selected');
    assert.deepEqual(expectedCalls, this.mockRedirectCalls());
});

QUnit.parametrize('creme.ReportD3ChartBrickController (ordering)', [
    [[{ x: 'A', y: 1 }], [{ x: 'A', y: 1 }]],
    [[{ x: 'A', y: 1 }, { x: 'B', y: 12 }], [{ x: 'B', y: 12 }, { x: 'A', y: 1 }]]
], function(data, expected, assert) {
    var html = this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' }
        ],
        data: data
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartBrickController({
        charts: {
            bar: new creme.D3BarChart({ transition: false })
        }
    });

    controller.registerActions(brick);
    controller.bind(brick);

//    var orderingSelect = brick.element().find('.graph-controls-sort .graph-control-value');
    var orderingSelect = brick.element().find('.chart-controls-sort .chart-control-value');

    // Select the bar !
    orderingSelect.val('DESC').trigger('change');

    assert.deepEqual(expected, controller.swapper().model().all());
});

QUnit.test('creme.ReportD3ChartBrickController (setup)', function(assert) {
    var element = $(this.createD3ChartBrickHtml({
        charts: [
            { name: 'bar', label: 'Bar Chart' }
        ],
        data: [{ x: 'A', y: 1 }]
    })).appendTo(this.qunitFixture());

    // Bind controller creation to brick setup events.
    creme.setupReportD3ChartBrick(element, {
        charts: {
            bar: new creme.D3BarChart({ transition: false })
        }
    });

    assert.equal(0, element.find('svg').length);

    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal(false, brick.isLoading());

    assert.equal(1, element.find('svg').length);
    var svg = d3.select(element.find('svg').get(0));

    assert.equal(svg.select('.bars .bar').size(), 1);
});

QUnit.test('creme.ReportD3ChartListBrickController (empty)', function(assert) {
    var html = this.createD3ChartListBrickHtml();
    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartListBrickController();

    controller.bind(brick);

    assert.deepEqual(controller.swappers(), {});
});

QUnit.test('creme.ReportD3ChartListBrickController (toggle)', function(assert) {
    var html = this.createD3ChartListBrickHtml({
        graphs: [ /* TODO: rename */
            {
                id: 'graph-a',
                chart: {
                    charts: [
                        { name: 'bar', label: 'Bar Chart' },
                        { name: 'pie', label: 'Pie Chart', selected: true }
                    ],
                    data: [
                        { x: 'A', y: 1 }
                    ],
                    props: {
                        pie: { band: 42 },
                        bar: { xAxisTitle: 'X Axis', yAxisTitle: 'Y Axis' }
                    }
                }
            }, {
                id: 'graph-b',
                chart: {
                    charts: [
                        { name: 'bar', label: 'Bar Chart', selected: true },
                        { name: 'pie', label: 'Pie Chart' }
                    ],
                    data: [
                        { x: 'X', y: 78 }
                    ],
                    props: {
                        pie: { band: 0 },
                        bar: { xAxisTitle: 'B Abscissas', yAxisTitle: 'B Ordinates' }
                    }
                }
            }
        ]
    });

    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartListBrickController({
        charts: function() {
            return {
                bar: new creme.D3BarChart({margin: 4}),
                pie: new creme.D3DonutChart({margin: 8})
            };
        }
    });

    controller.bind(brick);

    var element = brick.element();
    var swappers = controller.swappers();

    assert.deepEqual(Object.keys(swappers), ['graph-a', 'graph-b']);

    // All rows are collapsed on startup
//    assert.deepEqual(element.find('.graph-row').map(function() {
    assert.deepEqual(element.find('.chart-row').map(function() {
        return {
//            id: $(this).data('graphId'),
            id: $(this).data('chartId'),
//            collapsed: $(this).is('.graph-row-collapsed')
            collapsed: $(this).is('.chart-row-collapsed')
        };
    }).get(), [
        {id: 'graph-a', collapsed: true},
        {id: 'graph-b', collapsed: true}
    ]);

    // Swappers are built
    assert.equal(swappers['graph-a'].chart() instanceof creme.D3DonutChart, true);
    var props = swappers['graph-a'].chart().props();
    assert.equal(props.band, 42);

    assert.equal(swappers['graph-b'].chart() instanceof creme.D3BarChart, true);
    props = swappers['graph-b'].chart().props();
    assert.equal(props.xAxisTitle, 'B Abscissas');
    assert.equal(props.yAxisTitle, 'B Ordinates');

    // Sketches are created but nothing visible
    assert.equal(2, element.find('svg').length, 'svg canvas count');
    assert.equal(0, element.find('svg .d3-chart').length);

    // Now toggle first one
//    element.find('.graph-accordion-title[data-graph-id="graph-b"]').trigger('click');
    element.find('.chart-accordion-title[data-chart-id="graph-b"]').trigger('click');

//    assert.equal(element.find('.graph-row[data-graph-id="graph-a"]').is('.graph-row-collapsed'), true);
    assert.equal(element.find('.chart-row[data-chart-id="graph-a"]').is('.chart-row-collapsed'), true);
//    assert.equal(element.find('.graph-row[data-graph-id="graph-b"]').is('.graph-row-collapsed'), false);
    assert.equal(element.find('.chart-row[data-chart-id="graph-b"]').is('.chart-row-collapsed'), false);

    assert.equal(1, element.find('svg .d3-chart').length);

    // Then the second one
//    element.find('.graph-accordion-title[data-graph-id="graph-a"]').trigger('click');
    element.find('.chart-accordion-title[data-chart-id="graph-a"]').trigger('click');

//    assert.equal(element.find('.graph-row[data-graph-id="graph-a"]').is('.graph-row-collapsed'), false);
    assert.equal(element.find('.chart-row[data-chart-id="graph-a"]').is('.chart-row-collapsed'), false);
//    assert.equal(element.find('.graph-row[data-graph-id="graph-b"]').is('.graph-row-collapsed'), false);
    assert.equal(element.find('.chart-row[data-chart-id="graph-b"]').is('.chart-row-collapsed'), false);

    assert.equal(2, element.find('svg .d3-chart').length);
});


QUnit.test('creme.ReportD3ChartListBrickController (empty sub-graph)', function(assert) {
    var html = this.createD3ChartListBrickHtml({
        graphs: [
            {
                id: 'graph-a',
                chart: {
                    charts: [
                        { name: 'bar', label: 'Bar Chart' },
                        { name: 'pie', label: 'Pie Chart', selected: true }
                    ],
                    data: [],
                    props: {
                        pie: { band: 42 },
                        bar: { xAxisTitle: 'X Axis', yAxisTitle: 'Y Axis' }
                    }
                }
            }, {
                id: 'graph-b',
                chart: {
                    charts: [
                        { name: 'bar', label: 'Bar Chart', selected: true },
                        { name: 'pie', label: 'Pie Chart' }
                    ],
                    data: [
                        { x: 'X', y: 78 }
                    ],
                    props: {
                        pie: { band: 0 },
                        bar: { xAxisTitle: 'B Abscissas', yAxisTitle: 'B Ordinates' }
                    }
                }
            }
        ]
    });
    var brick = this.createBrick(html);
    var controller = new creme.ReportD3ChartListBrickController({
        charts: function() {
            return {
                bar: new creme.D3BarChart({margin: 4}),
                pie: new creme.D3DonutChart({margin: 8})
            };
        }
    });

    controller.bind(brick);

    var element = brick.element();
    var swappers = controller.swappers();

    assert.deepEqual(Object.keys(swappers), ['graph-b']);

//    assert.deepEqual(element.find('.graph-row').map(function() {
    assert.deepEqual(element.find('.chart-row').map(function() {
        return {
//            id: $(this).data('graphId'),
            id: $(this).data('chartId'),
//            collapsed: $(this).is('.graph-row-collapsed')
            collapsed: $(this).is('.chart-row-collapsed')
        };
    }).get(), [
        {id: 'graph-a', collapsed: true},
        {id: 'graph-b', collapsed: true}
    ]);

    assert.equal(swappers['graph-b'].chart() instanceof creme.D3BarChart, true);
    var props = swappers['graph-b'].chart().props();
    assert.equal(props.xAxisTitle, 'B Abscissas');
    assert.equal(props.yAxisTitle, 'B Ordinates');

    // Only one sketch is created but nothing visible
    assert.equal(1, element.find('svg').length, 'svg canvas count');
    assert.equal(0, element.find('svg .d3-chart').length);
});

QUnit.test('creme.ReportD3ChartListBrickController (setup)', function(assert) {
    var element = $(this.createD3ChartListBrickHtml({
        graphs: [
            {
                id: 'graph-a',
                chart: {
                    charts: [
                        { name: 'bar', label: 'Bar Chart' }
                    ],
                    data: [{ x: 'A', y: 1 }]
                }
            }, {
                id: 'graph-b',
                chart: {
                    charts: [
                        { name: 'pie', label: 'Pie Chart' }
                    ],
                    data: [{ x: 'X', y: 78 }]
                }
            }
       ]
    })).appendTo(this.qunitFixture());

    // Bind controller creation to brick setup events.
    creme.setupReportD3ChartListBrick(element, {
        charts: function() {
            return {
                bar: new creme.D3BarChart({margin: 4}),
                pie: new creme.D3DonutChart({margin: 8})
            };
        }
    });

    assert.equal(0, element.find('svg').length);

    var widget = creme.widget.create(element);
    var brick = widget.brick();

    assert.equal(true, brick.isBound());
    assert.equal(false, brick.isLoading());

    assert.equal(2, element.find('svg').length);
});

}(jQuery));
