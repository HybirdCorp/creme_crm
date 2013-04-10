var MOCK_PLOT_CONTENT_JSON_INVALID = '{"options": {, "data":[]}';
var MOCK_PLOT_CONTENT_JSON_EMPTY_DATA = '{"options": {}, "data":[]}' 
var MOCK_PLOT_CONTENT_JSON_DEFAULT = '{"options": {}, "data":[[[1, 2],[3, 4],[5, 12]]]}';
var MOCK_PLOT_CONTENT_DEFAULT = {options: {}, data: [[[1, 2],[3, 4],[5, 12]]]};

module("creme.widget.plot.js", {
    setup: function() {
        this.resetMockEvents();
        this.resetMockPlots();

        $.converters.register('mockPlotData', 'jqplotData', function(data) {
            var result = [];

            for(var s_index = 0; s_index < data.length; ++s_index)
            {
                var serie = data[s_index];
                var s_result = [];

                for(var index = 0; index < serie.length; ++index)
                {
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
        });

        $.converters.register('jqplotData', 'mockRendererData', function(data) {
            var result = [];

            for(var s_index = 0; s_index < data.length; ++s_index)
            {
                var serie = data[s_index];
                var s_result = [];

                for(var index = 0; index < serie.length; ++index)
                {
                    var entry = serie[index];

                    if (entry && entry.length > 1) {
                        entry = [entry[1], entry[0]].concat(entry.slice(2));
                    }

                    s_result.push(entry);
                }

                result.push(s_result);
            }

            return result;
        });
    },

    teardown: function() {
        this.cleanupMockPlots();
        $.converters.unregister('mockPlotData', 'jqplotData');
        $.converters.unregister('jqplotData', 'mockRendererData');
    },

    resetMockPlots: function()
    {
        this.plotContainer = $('#mock_creme_widget_plot_container');

        if (!this.plotContainer.get(0)) {
            $('body').append($('<div>').attr('id', 'mock_creme_widget_plot_container')
                                       .css('display', 'none'));
        }

        this.plotContainer = $('#mock_creme_widget_plot_container');
        this.mockPlots = [];
    },

    cleanupMockPlots: function()
    {
        for(var index = 0; index < this.mockPlots.length; ++index)
        {
            var plot = this.mockPlots[index];

            plot.remove();
            plot.unbind('plotSuccess');
            plot.unbind('plotError');
        }

        this.mockPlots = [];
    },

    resetMockEvents: function()
    {
        this.plotError = null;
        this.plotSuccess = null;
    },

    bindMockEvents: function(element)
    {
        var self = this;
        element.bind('plotSuccess', function(e, plot) {self.plotSuccess = plot;});
        element.bind('plotError', function(e, err) {self.plotError = err;});
    },

    createMockPlot: function(data, plotmode, savable, noauto) 
    {
        var options = {
                         plotmode: plotmode || 'svg', 
                         savable: savable || false
                      };

        var plot = creme.widget.buildTag($('<div/>'), 'ui-creme-jqueryplot', options, !noauto)
                               .append($('<script type="text/json">' + data + '</script>'));

        this.plotContainer.append(plot);
        this.mockPlots.push(plot);

        this.bindMockEvents(plot);
        return plot;
    }
});

function assertActive(element) {
    equal(element.hasClass('widget-active'), true, 'is widget active');
}

function assertReady(element) {
    assertActive(element);
    equal(element.hasClass('widget-ready'), true, 'is widget ready');
}

function assertNotReady(element) {
    assertActive(element);
    equal(element.hasClass('widget-ready'), false, 'is widget not ready');
}

function assertNoPlot(context, element, error)
{
    equal(element.creme().widget().plot(), undefined);
    equal($('.jqplot-target', element).length, 0);

    equal(context.plotSuccess, null, 'no success');

    if (error) {
        equal(context.plotError, error);
    } else {
        equal(context.plotError !== null, true, 'has error');
    }
}

function assertPlot(context, element)
{
    equal(typeof element.creme().widget().plot(), 'object');
    equal($('.jqplot-target', element).length, 1);

    deepEqual(context.plotSuccess, element.creme().widget().plot(), 'success');
    equal(context.plotError, null, 'no error');
}

test('creme.widget.Plot.create (empty)', function() {
    var element = this.createMockPlot('');

    creme.widget.create(element);
    assertReady(element);
    assertNoPlot(this, element, 'No Data');
});

test('creme.widget.Plot.create (invalid)', function() {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_INVALID);

    creme.widget.create(element);
    assertReady(element);
    assertNoPlot(this, element);

    equal(this.plotError.substr(0, 'JSON parse error'.length), 'JSON parse error');
});

test('creme.widget.Plot.create (valid)', function() {
    var element = this.createMockPlot(MOCK_PLOT_CONTENT_JSON_DEFAULT);

    stop(1);

    creme.widget.create(element, {}, function() {
        start();
    }, function() {
        start();
    });

    assertReady(element);
    assertPlot(this, element);
});

test('creme.widget.Plot.draw (empty)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);

    assertReady(element);
    assertNoPlot(this, element, 'No Data');

    this.resetMockEvents();
    stop(1);

    widget.draw(MOCK_PLOT_CONTENT_JSON_EMPTY_DATA, undefined, function() {
        start();
    });

    assertReady(element);
    assertNoPlot(this, element, 'No Data');
});

test('creme.widget.Plot.draw (valid)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

    this.resetMockEvents();
    stop(1);

    widget.draw(MOCK_PLOT_CONTENT_JSON_DEFAULT, function() {
        start();
    }, function() {
        start();
    });

    assertReady(element);
    assertPlot(this, element);
});

test('creme.widget.Plot.draw (invalid)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

    this.resetMockEvents();
    stop(1);

    widget.draw(MOCK_PLOT_CONTENT_JSON_INVALID, undefined, function() {
        start();
    });

    assertReady(element);
    assertNoPlot(this, element);
    equal(this.plotError.substr(0, 'JSON parse error'.length), 'JSON parse error');
});

test('creme.widget.Plot.redraw (valid, data)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

    deepEqual(widget.plotData(), []);
    deepEqual(widget.plotOptions(), {});

    widget.plotData([[[1, 2],[3, 4],[5, 12]]]);

    deepEqual(widget.plotData(), [[[1, 2],[3, 4],[5, 12]]]);
    deepEqual(widget.plotOptions(), {});

    this.resetMockEvents();
    stop(1);

    widget.redraw(function() {
        start();
    },
    function() {
        start();
    });

    assertPlot(this, element);
});

test('creme.widget.Plot.redraw (valid, options)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[1, 2],[3, 4],[5, 12]]]);

    deepEqual(widget.plotData(), [[[1, 2],[3, 4],[5, 12]]]);
    deepEqual(widget.plotOptions(), plot_options);

    this.resetMockEvents();
    stop(1);

    widget.redraw(function() {
        start();
    });

    assertPlot(this, element);
});

test('creme.widget.Plot.preprocess (convert data)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[1, 2.58],[3, 40.5],[5, 121.78]]]);

    deepEqual(widget.plotData(), [[[1, 1, 2.58],[2, 3, 40.5],[3, 5, 121.78]]]);
    deepEqual(widget.plotOptions(), plot_options);
});

test('creme.widget.Plot.preprocess (preprocess data)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[1, 150.5, "a"],[2, 3.45, "b"],[3, 12.80, "c"]]]);
    widget.preprocess();

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"],[3.45, 2, "b"],[12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, plot_options);
});

test('creme.widget.Plot.preprocess (preprocess data chained)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[1, 150.5, "a"],[2, 3.45, "b"],[3, 12.80, "c"]]]);
    widget.preprocess();

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"]],[[3.45, 2, "b"]],[[12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, plot_options);
});

test('creme.widget.Plot.preprocess (convert + preprocess data)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[150.5, "a"],[3.45, "b"],[12.80, "c"]]]);
    widget.preprocess();

    deepEqual(widget.plotInfo().built.data, [[[150.5, 1, "a"],[3.45, 2, "b"],[12.80, 3, "c"]]]);
    deepEqual(widget.plotInfo().built.options, plot_options);
});

test('creme.widget.Plot.preprocess (preprocess options)', function() {
    var element = this.createMockPlot('');
    var widget = creme.widget.create(element);
    assertActive(element);

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
    widget.plotData([[[1, 150.5, "a", "serie1"],[2,  3.45, "b"],[3, 12.80, "c"]],
                     [[1,  12.5, "serie2"],     [2, 13.45],     [3, 52.80]]]);

    deepEqual(widget.plotData(), [[[1, 150.5, "a", "serie1"],[2,  3.45, "b"],[3, 12.80, "c"]],
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
        axes: {
            xaxis: {
                ticks: ["a", "b", "c"]
            }
        }
    };

    deepEqual(widget.plotInfo().built.options, plot_built_options);
    deepEqual(widget.plotData(), [[[1, 150.5, "a", "serie1"],[2,  3.45, "b"],[3, 12.80, "c"]],
                                  [[1,  12.5, "serie2"],     [2, 13.45],     [3, 52.80]]]);
    deepEqual(widget.plotOptions(), plot_options);
});

