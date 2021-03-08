/* globals QUnitConsoleMixin */

(function($) {
var PLOTSELECTOR_PIEGRAPH_SCRIPT = {
    seriesDefaults: {
        renderer: 'jqplot.PieRenderer',
        rendererOptions: {showDataLabels: true}
    }
};

var PLOTSELECTOR_PIEGRAPH = {
    seriesDefaults: {
        renderer: $.jqplot.PieRenderer,
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

var PLOTSELECTOR_BARGRAPH = {
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
};

var PLOTSELECTOR_PLOT_01_DATA = [[[1, 2],   [3, 4],   [5, 12]]];
var PLOTSELECTOR_PLOT_02_DATA = [[[1, 2.58], [3, 40.5], [5, 121.78]]];

/* globals QUnitPlotMixin, QUnitWidgetMixin */
QUnit.module("creme.widgets.plotselector.js", new QUnitMixin(QUnitAjaxMixin,
                                                             QUnitConsoleMixin,
                                                             QUnitPlotMixin,
                                                             QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.plotselector.js'});
    },

    beforeEach: function() {
        this.resetMockPlotSelectors();

        this.setMockBackendGET({
            'mock/plot/1/data': this.backend.responseJSON(200, PLOTSELECTOR_PLOT_01_DATA),
            'mock/plot/2/data': this.backend.responseJSON(200, PLOTSELECTOR_PLOT_02_DATA),
            'mock/plot/invalid': this.backend.responseJSON(200, []),
            'mock/plot/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/plot/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        this.resetMockPlotEvents();
        this.cleanupMockPlotSelectors();

        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    },

    resetMockPlotSelectors: function() {
        this.mockContainer = $('#mock_creme_widget_plotselector_container');

        if (!this.mockContainer.get(0)) {
            this.qunitFixture().append($('<div>').attr('id', 'mock_creme_widget_plotselector_container')
                                                 .css('display', 'none'));
        }

        this.mockContainer = $('#mock_creme_widget_plotselector_container');
        this.mockSelectors = [];
    },

    cleanupMockPlotSelectors: function() {
        for (var index = 0; index < this.mockSelectors.length; ++index) {
            var selector = this.mockSelectors[index];
            var plot = $('.ui-creme-jqueryplot', selector);

            selector.remove();
            plot.off('plotSuccess');
            plot.off('plotError');
        }

        this.mockSelectors = [];
    },

    createMockPlot: function(data, plotmode, savable, noauto)  {
        data = data || '';
        var options = {
                         plotmode: plotmode || 'svg',
                         savable: savable || false
                      };

        var plot = creme.widget.buildTag($('<div/>'), 'ui-creme-jqueryplot', options, !noauto);

        if (Object.isNone(data) === false) {
            plot.append($('<script type="text/json"><!--' + data + '--></script>'));
        }

        this.bindMockPlotEvents(plot);
        return plot;
    },

    createMockPlotSelector: function(options, noauto) {
        options = options || {};
        var plot = this.createMockPlot();
        var selector = creme.widget.buildTag($('<div/>'), 'ui-creme-plotselector', options, !noauto)
                                   .append(plot);

        this.mockContainer.append(selector);
        this.mockSelectors.push(selector);

        return selector;
    },

    appendMockPlotScript: function(selector, name, data) {
        var script = data || '';
        script = (typeof script === 'string') ? script : JSON.stringify(script);

        selector.append($('<script name="' + name + '" type="text/json"><!--' + script + '--></script>'));
    }
}));

QUnit.test('creme.widget.PlotSelector.create (no graph, no data)', function(assert) {
    var element = this.createMockPlotSelector();
    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), []);

    deepEqual(widget.plotOptions(), []);
    equal(widget.plotOption('bar'), undefined);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);

    deepEqual([], this.mockConsoleWarnCalls());
    deepEqual([], this.mockConsoleErrorCalls());
});

QUnit.test('creme.widget.PlotSelector.create (graphs, no data)', function(assert) {
    var element = this.createMockPlotSelector();
    this.appendMockPlotScript(element, 'bar', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), []);

    deepEqual(widget.plotOptions().map(function(item) { return [item[0], item[1].replace(/\r\n/g, '')]; }),
              [['bar', JSON.stringify(PLOTSELECTOR_BARGRAPH_SCRIPT)],
               ['pie', JSON.stringify(PLOTSELECTOR_PIEGRAPH_SCRIPT)]], 'test 1');

    equal(widget.plotOption('bar').replace(/\r\n/g, ''), JSON.stringify(PLOTSELECTOR_BARGRAPH_SCRIPT), 'test 2');
    equal(widget.plotOption('pie').replace(/\r\n/g, ''), JSON.stringify(PLOTSELECTOR_PIEGRAPH_SCRIPT), 'test 3');
    equal(widget.plotOption('unknown'), undefined);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, name, no data)', function(assert) {
    var element = this.createMockPlotSelector({'plot-name': 'pie'});
    this.appendMockPlotScript(element, 'bar', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, template name, no initial, no data)', function(assert) {
    var element = this.createMockPlotSelector({'plot-name': '${name}-graph'});
    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, template name, initial, no data)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-name': '${name}-graph',
        'initial': JSON.stringify({'name': 'pie'})
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element);
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, name, data url)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/1/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, name, template data url, no initial)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.create (graphs, name, template data url, initial)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph',
        'initial': JSON.stringify({'id': 1})
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);
});

QUnit.test('creme.widget.PlotSelector.reload (graphs, name, template data url)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id']);

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({id: 2});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({id: 'unknown'});

    this.assertEmptyPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});

QUnit.test('creme.widget.PlotSelector.reload (no cache)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    equal(false, Object.isFunc(this.backend.reset));

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id']);

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    // replace backend data
    this.setMockBackendGET({
        'mock/plot/1/data': this.backend.responseJSON(200, PLOTSELECTOR_PLOT_02_DATA)
    });

    widget.reload({id: 1});

    // immediately replaced
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.resetBackend();
    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);
});

QUnit.test('creme.widget.PlotSelector.reload (cache, timeout)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    // cache of 200ms
    var cacheBackend = new creme.ajax.CacheBackend(this.backend, {
        condition: new creme.ajax.CacheBackendTimeout(200)
    });

    equal(true, Object.isFunc(cacheBackend.reset));

    var widget = creme.widget.create(element, {backend: cacheBackend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id']);

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    // replace backend data
    this.setMockBackendGET({
        'mock/plot/1/data': this.backend.responseJSON(200, PLOTSELECTOR_PLOT_02_DATA)
    });

    widget.reload({id: 1});

    // not replaced
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    stop(1);
    var self = this;

    setTimeout(function() {
        widget.reload({id: 1});

        // on cache timeout, data is replaced
        self.assertPlot(self, $('.ui-creme-jqueryplot', element));
        deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
        deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);
        start();
    }, 300);
});

QUnit.test('creme.widget.PlotSelector.reload (cache, resetBackend)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': 'pie-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    // cache of 200ms
    var cacheBackend = new creme.ajax.CacheBackend(this.backend, {
        condition: new creme.ajax.CacheBackendTimeout(200)
    });

    equal(true, Object.isFunc(cacheBackend.reset));

    var widget = creme.widget.create(element, {backend: cacheBackend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id']);

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    // replace backend data
    this.setMockBackendGET({
        'mock/plot/1/data': this.backend.responseJSON(200, PLOTSELECTOR_PLOT_02_DATA)
    });

    widget.reload({id: 1});

    // not replaced
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.resetBackend();
    widget.reload({id: 1});

    // cache is reset, so data is replaced
    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);
});

QUnit.test('creme.widget.PlotSelector.reload (graphs, template name, template data url)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': '${name}-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id', 'name']);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);

    widget.reload({id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({name: 'pie', id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reload({name: 'pie', id: 2});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);

    widget.reload({name: 'bar'});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_BARGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_02_DATA);
});

QUnit.test('creme.widget.PlotSelector.reset (graphs, template name, template data url)', function(assert) {
    var element = this.createMockPlotSelector({
        'plot-data-url': 'mock/plot/${id}/data',
        'plot-name': '${name}-graph'
    });

    this.appendMockPlotScript(element, 'bar-graph', PLOTSELECTOR_BARGRAPH_SCRIPT);
    this.appendMockPlotScript(element, 'pie-graph', PLOTSELECTOR_PIEGRAPH_SCRIPT);

    var widget = creme.widget.create(element, {backend: this.backend});
    var plot_widget = $('.ui-creme-jqueryplot', element).creme().widget();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));
    this.assertNoPlot(this, $('.ui-creme-jqueryplot', element), 'null');

    deepEqual(widget.dependencies(), ['id', 'name']);

    deepEqual(plot_widget.plotOptions(), {});
    deepEqual(plot_widget.plotData(), []);

    widget.reload({name: 'pie', id: 1});

    this.assertPlot(this, $('.ui-creme-jqueryplot', element));
    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), PLOTSELECTOR_PLOT_01_DATA);

    widget.reset();

    this.assertReady(element);
    this.assertReady($('.ui-creme-jqueryplot', element));

    deepEqual(plot_widget.plotOptions(), PLOTSELECTOR_PIEGRAPH);
    deepEqual(plot_widget.plotData(), []);
});
}(jQuery));
