PLOTSELECTOR_PIEGRAPH_SCRIPT = {
    seriesDefaults: {
        renderer: 'jqplot.PieRenderer', 
        rendererOptions: {showDataLabels: true}
    }
};

PLOTSELECTOR_PIEGRAPH = {
    seriesDefaults: {
        renderer: $.jqplot.PieRenderer, 
        rendererOptions: {showDataLabels: true}
    }
}

PLOTSELECTOR_BARGRAPH_SCRIPT = {
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

PLOTSELECTOR_BARGRAPH = {
    seriesDefaults: {
        renderer: $.jqplot.BarRenderer, 
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
            renderer: $.jqplot.CategoryAxisRenderer
        },
        yaxis: {
            tickOptions: {formatString: "%.2f €"}
        }
    }
}

PLOTSELECTOR_PLOT_01_DATA = [[[1, 2],   [3, 4],   [5, 12]]];
PLOTSELECTOR_PLOT_02_DATA = [[[1, 2.58],[3, 40.5],[5, 121.78]]];

module("creme.widgets.plotselector.js", {
    setup: function() {
        this.resetMockEvents();
        this.resetMockPlotSelectors();

        this.backend = new creme.ajax.MockAjaxBackend({sync:true});
        $.extend(this.backend.GET, {'mock/plot/1/data': this.backend.response(200, PLOTSELECTOR_PLOT_01_DATA),
                                    'mock/plot/2/data': this.backend.response(200, PLOTSELECTOR_PLOT_02_DATA),
                                    'mock/plot/invalid': this.backend.response(200, []),
                                    'mock/plot/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/plot/error': this.backend.response(500, 'HTTP - Error 500')});
    },

    teardown: function() {
        this.cleanupMockPlotSelectors();
    },

    resetMockPlotSelectors: function()
    {
        this.mockContainer = $('#mock_creme_widget_plotselector_container');

        if (!this.mockContainer.get(0)) {
            $('body').append($('<div>').attr('id', 'mock_creme_widget_plotselector_container')
                                       .css('display', 'none'));
        }

        this.mockContainer = $('#mock_creme_widget_plotselector_container');
        this.mockSelectors = [];
    },

    cleanupMockPlotSelectors: function()
    {
        for(var index = 0; index < this.mockSelectors.length; ++index)
        {
            var selector = this.mockSelectors[index];
            var plot = $('.ui-creme-jqueryplot', selector);

            selector.remove();
            plot.unbind('plotSuccess');
            plot.unbind('plotError');
        }

        this.mockSelectors = [];
    },

    createMockPlot: function(data, plotmode, savable, noauto) 
    {
        var data = data || '';
        var options = {
                         plotmode: plotmode || 'svg', 
                         savable: savable || false
                      };

        var plot = creme.widget.buildTag($('<div/>'), 'ui-creme-jqueryplot', options, !noauto)
                               .append($('<script type="text/json">' + data + '</script>'));

        this.bindMockEvents(plot);
        return plot;
    },

    createMockPlotSelector: function(options, noauto)
    {
        var options = options || {};
        var plot = this.createMockPlot('', 'svg', false, false);
        var selector = creme.widget.buildTag($('<div/>'), 'ui-creme-plotselector', options, !noauto)
                                   .append(plot);

        this.mockContainer.append(selector);
        this.mockSelectors.push(selector);

        return selector;
    },

    appendMockPlotScript: function(selector, name, data)
    {
        var script = data || '';
        script = (typeof script === 'string') ? script : $.toJSON(script);

        selector.append($('<script name="' + name + '" type="text/json">' + script + '</script>'))
    },

    resetMockEvents: function()
    {
        this.plotError = null;
        this.plotSuccess = null;
    },

    bindMockEvents: function(plot)
    {
        var self = this;
        plot.bind('plotSuccess', function(e, plot) {self.plotSuccess = plot; self.plotError = null;});
        plot.bind('plotError', function(e, err) {self.plotError = err; self.plotSuccess = null;});
    },
});


test('creme.widget.PlotSelector.create (no graph, no data)', function() {
    var element = this.createMockPlotSelector();
    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(widget.plotOptions(), []);
    equal(widget.plotOption('bar'), undefined);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, no data)', function() {
    var element = this.createMockPlotSelector();
    this.appendMockPlotScript(element, 'bar', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(widget.plotOptions(), [['bar', $.toJSON(PLOTSELECTOR_BARGRAPH_SCRIPT)], 
                                     ['pie', $.toJSON(PLOTSELECTOR_PIEGRAPH_SCRIPT)]]);
    equal(widget.plotOption('bar'), $.toJSON(PLOTSELECTOR_BARGRAPH_SCRIPT));
    equal(widget.plotOption('pie'), $.toJSON(PLOTSELECTOR_PIEGRAPH_SCRIPT));
    equal(widget.plotOption('unknown'), undefined);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, name, no data)', function() {
    var element = this.createMockPlotSelector({'plot-name': 'pie'});
    this.appendMockPlotScript(element, 'bar', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, template name, no initial, no data)', function() {
    var element = this.createMockPlotSelector({'plot-name': '${name}-graph'});
    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, template name, initial, no data)', function() {
    var element = this.createMockPlotSelector({
        'plot-name': '${name}-graph', 
        'initial': $.toJSON({'name': 'pie'})
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, name, data url)', function() {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/1/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertPlot(this, $('.ui-creme-jqueryplot', element));

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);
});

test('creme.widget.PlotSelector.create (graphs, name, template data url, no initial)', function() {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.create (graphs, name, template data url, initial)', function() {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph',
        'initial': $.toJSON({'id': 1})
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertPlot(this, $('.ui-creme-jqueryplot', element));

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(),PLOTSELECTOR_PLOT_01_DATA);
});

test('creme.widget.PlotSelector.reload (graphs, name, template data url)', function() {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({id: 2});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({id: 'unknown'});

    assertInvalidPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

test('creme.widget.PlotSelector.reload (graphs, template name, template data url)', function() {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': '${name}-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    assertReady(element);
    assertReady($('.ui-creme-jqueryplot', element));
    assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'No Data');

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({name: 'pie', id: 1});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({name: 'pie', id: 2});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({name: 'bar'});

    assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_BARGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);
});
