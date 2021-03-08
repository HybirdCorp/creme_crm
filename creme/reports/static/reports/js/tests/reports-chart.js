(function($) {
var PLOTSELECTOR_PIEGRAPH_SCRIPT = {
    seriesDefaults: {
        renderer: 'jqplot.PieRenderer',
        rendererOptions: {showDataLabels: true}
    }
};

var PLOTSELECTOR_BARGRAPH_SCRIPT = {
    seriesDefaults: {
        renderer: 'jqplot.BarRenderer',
        rendererOptions: {
            showDataLabels: true,
            fillToZero: true
        }
    },
    series: [
        {label: "CA Attendu"},
        {label: "CA Effectué"}
    ],
    axes: {
        xaxis: {
            ticks: ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
            renderer: "jqplot.CategoryAxisRenderer"
        },
        yaxis: {
            tickOptions: {formatString: "%.2f €"}
        }
    }
};

var REPORT_CHART_CONTENT = '<div class="reports-graph-brick">' +
                                '<div class="brick-graph-header clearfix">' +
                                    '<div class="graph-controls graph-controls-type">' +
                                        '<a class="graph-control-value" title="Select graphic type">Bar Chart</a>' +
                                    '</div>' +
                                    '<div class="graph-controls graph-controls-sort">' +
                                        '<a class="graph-control-value" title="Sort order">Ascending</a>' +
                                    '</div>' +
                                '</div>' +
                                '<div class="ui-widget-content ui-creme-widget ui-creme-plotselector" widget="ui-creme-plotselector" plot-data-url="mock/fetch?order=${sort}" plot-name="${chart}">' +
                                    '<script name="piechart" type="text/json"><!-- ' + PLOTSELECTOR_PIEGRAPH_SCRIPT + ' --></script>' +
                                    '<script name="barchart" type="text/json"><!-- ' + PLOTSELECTOR_BARGRAPH_SCRIPT + ' --></script>' +
                                    '<div class="ui-widget-content ui-creme-widget ui-creme-jqueryplot ui-creme-resizable widget-active widget-ready" widget="ui-creme-jqueryplot" savable="false" format="creme.graphael.BargraphData"></div>' +
                                '</div>' +
                           '</div>';

var REPORT_CHART_PROPERTIES = {
    charts: {
        'piechart': 'Pie Chart',
        'barchart': 'Bar Chart'
    },
    sorts: {
        'ASC':  'Ascending',
        'DESC': 'Descending'
    }
};


QUnit.module("creme.reports.chart", new QUnitMixin(QUnitEventMixin,
                                                   QUnitAjaxMixin,
                                                   QUnitDialogMixin, {

}));

QUnit.test('creme.reports.ChartController (initialize)', function(assert) {
    var initial = {
        chart: 'piechart',
        sort:  'DESC'
    };

    var element = $(REPORT_CHART_CONTENT);
    var controller = new creme.reports.ChartController(REPORT_CHART_PROPERTIES);

    equal('Bar Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Ascending', element.find('.graph-controls-sort .graph-control-value').text());

    equal(false, element.find('.ui-creme-plotselector').is('.widget-ready'));

    controller.initialize(element, initial);

    equal('Pie Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Descending', element.find('.graph-controls-sort .graph-control-value').text());

    equal(true, element.find('.ui-creme-plotselector').is('.widget-ready'));
});

QUnit.test('creme.reports.ChartController (select chart)', function(assert) {
    var initial = {
        chart: 'piechart',
        sort:  'DESC'
    };

    var element = $(REPORT_CHART_CONTENT);
    var controller = new creme.reports.ChartController(REPORT_CHART_PROPERTIES);

    controller.initialize(element, initial);

    equal('Pie Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Descending', element.find('.graph-controls-sort .graph-control-value').text());

    equal(0, $('.popover').length);

    element.find('.graph-controls-type .graph-control-value').trigger('click');

    equal(1, $('.popover').length);

    $('.popover .popover-content .popover-list-item[alt="Bar Chart"]').trigger('click');

    equal(0, $('.popover').length);

    equal('Bar Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Descending', element.find('.graph-controls-sort .graph-control-value').text());
});

QUnit.test('creme.reports.ChartController (select chart)', function(assert) {
    var initial = {
        chart: 'piechart',
        sort:  'DESC'
    };

    var element = $(REPORT_CHART_CONTENT);
    var controller = new creme.reports.ChartController(REPORT_CHART_PROPERTIES);

    controller.initialize(element, initial);

    equal('Pie Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Descending', element.find('.graph-controls-sort .graph-control-value').text());

    equal(0, $('.popover').length);

    element.find('.graph-controls-sort .graph-control-value').trigger('click');

    equal(1, $('.popover').length);

    $('.popover .popover-content .popover-list-item[alt="Ascending"]').trigger('click');

    equal(0, $('.popover').length);

    equal('Pie Chart', element.find('.graph-controls-type .graph-control-value').text());
    equal('Ascending', element.find('.graph-controls-sort .graph-control-value').text());
});

QUnit.parameterize('creme.reports.ChartController (graphael converter)', [
    [{}, []],
    [{x: [1, 2]}, []],  // needs both x & y
    [{y: [1, 2]}, []],  // needs both x & y
    [
        {x: [1, 2], y: [0.5, 1.47]},
        [
            [[1, 0.5, undefined], [2, 1.47, undefined]]
        ]
    ],
    [ // take the shorter list from x & y
        {x: [1, 2], y: [0.5, 1.47, 5.78]},
        [
            [[1, 0.5, undefined], [2, 1.47, undefined]]
        ]
    ],
    [
        {x: [1, 2, 3], y: [0.5, 1.47]},
        [
            [[1, 0.5, undefined], [2, 1.47, undefined]]
        ]
    ],
    [ // x can be a string, y is converted to float
        {x: ['1', '2'], y: ['0.5', '1.47']},
        [
            [['1', 0.5, undefined], ['2', 1.47, undefined]]
        ]
    ],
    [
        {x: ['A', 'B'], y: ['0.5', '1.47']},
        [
            [['A', 0.5, undefined], ['B', 1.47, undefined]]
        ]
    ],
    [
        {x: ['A', 'B'], y: ['X', 'Y']},
        [
            [['A', 0.0, undefined], ['B', 0.0, undefined]]
        ]
    ],
    [ // y can be an array
        {x: ['A', 'B'], y: [['0.5', 'YA'], ['1.47', 'YB']]},
        [
            [['A', 0.5, 'YA'], ['B', 1.47, 'YB']]
        ]
    ]
], function(input, expected, assert) {
    var output = creme.utils.convert(input, {
        from: 'creme.graphael.BargraphData',
        to: 'jqplotData'
    });

    deepEqual(output, expected);
});

}(jQuery));
