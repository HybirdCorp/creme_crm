/* globals QUnitPlotMixin QUnitWidgetMixin QUnitConsoleMixin */

(function($) {

var MOCK_PLOT_CONTENT_JSON_INVALID = '{"options": {, "data":[]}';
var MOCK_PLOT_CONTENT_JSON_EMPTY_DATA = '{"options": {}, "data":[]}';
var MOCK_PLOT_CONTENT_JSON_DEFAULT = '{"options": {}, "data":[[[1, 2],[3, 4],[5, 12]]]}';


QUnit.module("creme.widget.plot.js", new QUnitMixin(QUnitAjaxMixin,
                                                    QUnitEventMixin,
                                                    QUnitPlotMixin,
                                                    QUnitConsoleMixin,
                                                    QUnitDialogMixin,
                                                    QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.plot.js'});
    },

    beforeEach: function() {
        this.resetMockPlotEvents();
        this.resetMockPlots();

        creme.utils.converters().register('mockPlotData', 'jqplotData', this._mockPlotData_to_jqplotData);
        creme.utils.converters().register('jqplotData', 'mockRendererData', this._jqplotData_to_mockRendererData);
    },

    afterEach: function() {
        this.resetMockPlotEvents();
        this.resetMockPlots();

        this.cleanupMockPlots();

        creme.utils.converters().unregister('mockPlotData', 'jqplotData');
        creme.utils.converters().unregister('jqplotData', 'mockRendererData');

        creme.widget.shutdown($('body'));

        $('#mock_creme_widget_plot_container').detach();
    },

    _mockPlotData_to_jqplotData: function(data) {
        var result = [];

        for (var s_index = 0; s_index < data.length; ++s_index) {
            var serie = data[s_index];
            var s_result = [];

            for (var index = 0; index < serie.length; ++index) {
                var entry = serie[index];

                if (entry) {
                    entry = [index + 1].concat(entry);
                } else {
                    entry = [index + 1];
                }

                s_result.push(entry);
            }

            result.push(s_result);
        }

        return result;
    },

    _jqplotData_to_mockRendererData: function(data) {
        var result = [];

        for (var s_index = 0; s_index < data.length; ++s_index) {
            var serie = data[s_index];
            var s_result = [];

            for (var index = 0; index < serie.length; ++index) {
                var entry = serie[index];

                if (entry && entry.length > 1) {
                    entry = [entry[1], entry[0]].concat(entry.slice(2));
                }

                s_result.push(entry);
            }

            result.push(s_result);
        }

        return result;
    },

    resetMockPlots: function() {
        this.plotContainer = $('#mock_creme_widget_plot_container');

        if (!this.plotContainer.get(0)) {
            this.qunitFixture().append($('<div>').attr('id', 'mock_creme_widget_plot_container')
                                                 .css('width', 0)
                                                 .css('height', 0));
        }

        this.plotContainer = $('#mock_creme_widget_plot_container');
        this.mockPlots = [];
    },

    cleanupMockPlots: function() {
        for (var index = 0; index < this.mockPlots.length; ++index) {
            var plot = this.mockPlots[index];

            plot.remove();
            plot.off('plotSuccess');
            plot.off('plotError');
        }

        this.mockPlots = [];
    },

    createMockPlot: function(data, plotmode, savable, noauto)  {
        var options = {
                         plotmode: plotmode || 'svg',
                         savable: savable || false
                      };

        var plot = creme.widget.buildTag($('<div/>'), 'ui-creme-jqueryplot', options, !noauto);

        if (Object.isNone(data) === false) {
            plot.append($('<script type="text/json"><!--' + data + '--></script>'));
        }

        this.plotContainer.append(plot);
        this.mockPlots.push(plot);

        this.bindMockPlotEvents(plot);
        return plot;
    }
}));

QUnit.test('creme.widget.Plot.create (empty)', function(assert) {
    var element = this.createMockPlot();
    creme.widget.create(element, {},
                        this.mockListener('plot-init'),
                        this.mockListener('plot-init-fail'));

    this.assertReady(element);
    this.assertNoPlot(this, element, 'null');

    deepEqual({
        'plot-init': [[element]]
    }, this.mockListenerCalls());

    deepEqual([], this.mockConsoleWarnCalls());
});

QUnit.test('creme.widget.Plot.create (invalid)', function(assert) {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_INVALID);

    creme.widget.create(element,
                        this.mockListener('plot-init'),
                        this.mockListener('plot-init-fail'));

    this.assertReady(element);
    this.assertNoPlot(this, element);

    equal(this.plotError.message.substr(0, 'JSON parse error'.length), 'JSON parse error');

    deepEqual({
        'plot-init-fail': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.create (valid)', function(assert) {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);
    var widget = creme.widget.create(element, {},
                                     this.mockListener('plot-init'),
                                     this.mockListener('plot-init-fail'));

    this.assertReady(element);
    this.assertPlot(this, element);

    equal(false, widget.isSavable());

    var capture = $('.jqplot-actions button[name="capture"]', element);
    equal(0, capture.length);

    deepEqual({
        'plot-init': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.create (valid, savable)', function(assert) {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);
    var widget = creme.widget.create(element, {savable: true},
                                     this.mockListener('plot-init'),
                                     this.mockListener('plot-init-fail'));

    this.assertReady(element);
    this.assertPlot(this, element);

    equal(true, widget.isSavable());

    var capture = $('.jqplot-actions button[name="capture"]', element);
    equal(1, capture.length);

    deepEqual({
        'plot-init': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.draw (empty)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);

    this.assertReady(element);
    this.assertNoPlot(this, element, 'null');

    this.resetMockPlotEvents();

    widget.draw(MOCK_PLOT_CONTENT_JSON_EMPTY_DATA,
                this.mockListener('plot-draw'),
                this.mockListener('plot-draw-fail'));

    this.assertReady(element);
    this.assertNoPlot(this, element, 'null');

    deepEqual({
        'plot-draw': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.draw (valid)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    this.resetMockPlotEvents();

    widget.draw(MOCK_PLOT_CONTENT_JSON_DEFAULT,
                this.mockListener('plot-draw'),
                this.mockListener('plot-draw-fail'));

    this.assertReady(element);
    this.assertPlot(this, element);

    deepEqual({
        'plot-draw': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.draw (valid, raster)', function(assert) {
    var self = this;
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element, {plotmode: 'raster'});

    this.assertActive(element);
    this.resetMockPlotEvents();

    element.on('plotSuccess', function() {
        self.assertReady(element);
        self.assertRasterPlot(self, element);
        start();
    });

    element.on('plotError', function(e) {
        fail('plot has failed', e);
        start();
    });

    widget.draw(MOCK_PLOT_CONTENT_JSON_DEFAULT);
    stop(1);
});

QUnit.test('creme.widget.Plot.draw (invalid)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    this.resetMockPlotEvents();

    widget.draw(MOCK_PLOT_CONTENT_JSON_INVALID,
                this.mockListener('plot-draw'),
                this.mockListener('plot-draw-fail'));

    this.assertReady(element);
    this.assertNoPlot(this, element);

    equal(this.plotError.message.substr(0, 'JSON parse error'.length), 'JSON parse error');

    deepEqual({
        'plot-draw-fail': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.redraw (valid, data)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    widget.plotData([[[1, 2], [3, 4], [5, 12]]]);

    deepEqual(widget.plotData(), [[[1, 2], [3, 4], [5, 12]]]);
    deepEqual(widget.plotOptions(), {});

    this.resetMockPlotEvents();

    widget.redraw(this.mockListener('plot-draw'),
                  this.mockListener('plot-draw-fail'));

    this.assertPlot(this, element);

    deepEqual({
        'plot-draw': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.redraw (empty, valid default)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertReady(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    widget.plotOptions({dataDefaults: [[[5, 2], [4, 4]]]});

    this.resetMockPlotEvents();

    widget.redraw(this.mockListener('plot-draw'),
                  this.mockListener('plot-draw-fail'));

    this.assertPlot(this, element);

    deepEqual({
        'plot-draw': [[element]]
    }, this.mockListenerCalls());

    deepEqual(widget.plotData(), []);
});

QUnit.test('creme.widget.Plot.redraw (valid, options)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {
                showDataLabels: true
            }
        }
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 2], [3, 4], [5, 12]]]);

    deepEqual(widget.plotData(), [[[1, 2], [3, 4], [5, 12]]]);
    deepEqual(widget.plotOptions(), plot_options);

    this.resetMockPlotEvents();

    widget.redraw(this.mockListener('plot-draw'),
                  this.mockListener('plot-draw-fail'));

    this.assertPlot(this, element);

    deepEqual({
        'plot-draw': [[element]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.widget.Plot.capture (svg)', function(assert) {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);
    var widget = creme.widget.create(element, {});

    this.assertReady(element);
    this.assertPlot(this, element);

    equal(1, widget.capture().length);
});

QUnit.test('creme.widget.Plot.capture (raster)', function(assert) {
    var self = this;
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);

    var widget = creme.widget.create(element, {plotmode: 'raster'});

    stop(1);

    element.on('plotSuccess', function() {
        self.assertReady(element);
        self.assertRasterPlot(self, element);

        equal(1, widget.capture().length);
        start();
    });

    element.on('plotError', function(e) {
        start();
        fail('plot has failed', e);
    });
});

QUnit.test('creme.widget.Plot.capture (raster image in popup)', function(assert) {
    var self = this;
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);
    creme.widget.create(element, {savable: true});

    this.assertReady(element);
    this.assertPlot(this, element);

    var capture = $('.jqplot-actions button[name="capture"]', element);
    equal(1, capture.length);

    this.assertClosedDialog();

    capture.trigger('click');

    stop(1);

    setTimeout(function() {
        start();
        self.assertOpenedPopover();
        self.assertPopoverTitle(gettext('Canvas image'));
    }, 200);
});

QUnit.test('creme.widget.Plot.preprocess (convert data)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        dataFormat: "mockPlotData"
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 2.58], [3, 40.5], [5, 121.78]]]);

    deepEqual(widget.plotData(), [[[1, 1, 2.58], [2, 3, 40.5], [3, 5, 121.78]]]);
    deepEqual(widget.plotOptions(), plot_options);
});

QUnit.test('creme.widget.Plot.preprocess (preprocess data)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        dataPreprocessors: ["swap"]
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 150.5, "a"], [2, 3.45, "b"], [3, 12.80, "c"]]]);
    widget.preprocess();

    var built_plot_options = {
        seriesDefaults: {
            renderer: $.jqplot.PieRenderer,
            rendererOptions: {showDataLabels: true}
        },
        handlers: [],
        dataPreprocessors: ["swap"]
    };

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"], [3.45, 2, "b"], [12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, built_plot_options);
});

QUnit.test('creme.widget.Plot.preprocess (preprocess data chained)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        dataPreprocessors: [
                            "swap",
                            "tee"
                           ]
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 150.5, "a"], [2, 3.45, "b"], [3, 12.80, "c"]]]);
    widget.preprocess();

    var built_plot_options = {
        seriesDefaults: {
            renderer: $.jqplot.PieRenderer,
            rendererOptions: {showDataLabels: true}
        },
        handlers: [],
        dataPreprocessors: ["swap", "tee"]
    };

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"]], [[3.45, 2, "b"]], [[12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, built_plot_options);
});

QUnit.test('creme.widget.Plot.preprocess (convert + preprocess data)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        dataFormat: "mockPlotData",
        dataPreprocessors: ["swap"]
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[150.5, "a"], [3.45, "b"], [12.80, "c"]]]);
    widget.preprocess();

    var built_plot_options = {
        seriesDefaults: {
            renderer: $.jqplot.PieRenderer,
            rendererOptions: {showDataLabels: true}
        },
        handlers: [],
        dataFormat: "mockPlotData",
        dataPreprocessors: ["swap"]
    };

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"], [3.45, 2, "b"], [12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, built_plot_options);
});

QUnit.test('creme.widget.Plot.preprocess (preprocess options)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        series: 'preprocess.seriesLabel',
        seriesLabelOptions: {
            defaults: {showLabel: true},
            labelIndex: -1
        },
        axes: {
            xaxis: {
                ticks: 'preprocess.ticksLabel',
                ticksLabelOptions: {
                    labelIndex: 2,
                    seriesIndex: 0
                }
            }
        }
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 150.5, "a", "serie1"], [2,  3.45, "b"], [3, 12.80, "c"]],
                     [[1,  12.5, "serie2"],     [2, 13.45],     [3, 52.80]]]);

    deepEqual(widget.plotData(), [[[1, 150.5, "a", "serie1"], [2,  3.45, "b"], [3, 12.80, "c"]],
                                  [[1,  12.5, "serie2"],     [2, 13.45],     [3, 52.80]]]);
    deepEqual(widget.plotOptions(), plot_options);
    deepEqual(widget.plotInfo().built, undefined);

    widget.preprocess();

    var plot_built_options = {
        seriesDefaults: {
            renderer: $.jqplot.PieRenderer,
            rendererOptions: {showDataLabels: true}
        },
        series: [
            {
                showLabel: true,
                label: 'serie1'
            },
            {
                showLabel: true,
                label: 'serie2'
            }
        ],
        handlers: [],
        axes: {
            xaxis: {
                ticks: ["a", "b", "c"]
            }
        }
    };

    deepEqual(widget.plotInfo().built.options, plot_built_options);
    deepEqual(widget.plotData(), [[[1, 150.5, "a", "serie1"], [2,  3.45, "b"], [3, 12.80, "c"]],
                                  [[1,  12.5, "serie2"],     [2, 13.45],     [3, 52.80]]]);
    deepEqual(widget.plotOptions(), plot_options);
});

QUnit.test('creme.widget.Plot.preprocess (preprocess handlers)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        handlers: [
            {action: 'popup', event: 'click', url: '/mock/action/%d'},
            {action: 'redirect', event: 'dblclick', url: '/mock/action/%d'}
        ]
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 2.58], [3, 40.5], [5, 121.78]]]);

    deepEqual(widget.plotData(), [[[1, 2.58], [3, 40.5], [5, 121.78]]]);
    deepEqual(widget.plotOptions(), plot_options);

    widget.preprocess();

    var plot_built_options = {
        seriesDefaults: {
            renderer: $.jqplot.PieRenderer,
            rendererOptions: {showDataLabels: true}
        },
        handlers: [
            {action: creme.widget.PlotEventHandlers.get('popup'),    event: 'jqplotDataClick',    url: '/mock/action/%d'},
            {action: creme.widget.PlotEventHandlers.get('redirect'), event: 'jqplotDataDblclick', url: '/mock/action/%d'}
        ]
    };

    deepEqual(widget.plotInfo().built.options, plot_built_options);
});

QUnit.test('creme.widget.Plot.preprocess (preprocess invalid handler)', function(assert) {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    this.assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    var plot_options = {
        seriesDefaults: {
            renderer: 'jqplot.PieRenderer',
            rendererOptions: {showDataLabels: true}
        },
        handlers: [
            {action: 'popup', event: 'click', url: '/mock/action/%d'},
            {action: 'unknown', event: 'dblclick', url: '/mock/action/%d'}
        ]
    };

    widget.plotOptions(plot_options);
    widget.plotData([[[1, 2.58], [3, 40.5], [5, 121.78]]]);

    deepEqual(widget.plotData(), [[[1, 2.58], [3, 40.5], [5, 121.78]]]);
    deepEqual(widget.plotOptions(), plot_options);

    widget.redraw();

    this.assertNoPlot(this, element, 'Error: no such plot event handler "unknown"');
});

}(jQuery));
