/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

creme.widget.PlotProcessorRegistry = function() {
    this._processors = {}
}

creme.widget.PlotProcessorRegistry.prototype = {
    register: function(name, converter) {
        if ($.isFunction(this.processor(name)))
            throw new Error('processor "' + name + '" is already registered');

        this._processors[name] = converter;
    },

    unregister: function(name)
    {
        if (this.processor(name) === undefined)
            throw new Error('no such processor "' + name + '"');

        delete this._processors[name];
    },

    processor: function(name) {
        return this._processors[name];
    }
}

creme.widget.PlotProcessors = new creme.widget.PlotProcessorRegistry();

$.extend(creme.widget.PlotProcessors, {
    preprocessOptions: function(options, data)
    {
        for(key in options)
        {
            var entry = options[key];

            if (typeof entry == 'object') {
                this.preprocessOptions(entry, data);
            } else if (typeof entry === 'string' && /^preprocess\.[\w\d]+$/.test(entry)) {
                var preprocessor_name = entry.substr('preprocess.'.length);
                var preprocessor_options = options[preprocessor_name + 'Options'];
                var preprocessor = this.processor(preprocessor_name);

                if (preprocessor_options !== undefined)
                    delete options[preprocessor_name + 'Options'];

                options[key] = preprocessor(data, preprocessor_options);
            }
        }
    },

    preprocessData: function(preprocessors, data)
    {
        var result = data;

        for(var index = 0; index < preprocessors.length; ++index)
        {
            var preprocessor_info = preprocessors[index];

            preprocessor_info = (typeof preprocessor_info === 'string') ? {preprocessor: preprocessor_info} : preprocessor_info;
            preprocessor_info = $.extend({preprocessor: '', options: {}}, preprocessor_info);

            result = this.processor(preprocessor_info.preprocessor)(result, preprocessor_info.options);
        }

        return result;
    },

    preprocess: function(plot_info)
    {
        var options = plot_info.options || {};
        var data = creme.object.isempty(plot_info.data) ? (options.dataDefaults || []) : plot_info.data;

        var built_options = $.extend(true, {}, options);
        var built_data = this.preprocessData(options.dataPreprocessors || [], data);

        this.preprocessOptions(built_options, built_data);

        return {
            options: built_options || {}, 
            data: built_data || []
        };
    }
});

creme.widget.PlotProcessors.register('formatSerieLabel', function(series, options) {
    var options = $.extend({format: "%s", seriesIndex: 0}, options);
    var seriesIndex = options.seriesIndex;
    var serie = seriesIndex < series.length ? series[seriesIndex] : [];

    var formatter = function(format) {
        return function(value, index, data) {return format.format(data);}
    }(options.format);

    return serie.map(new Generator().each(formatter).iterator());
});

creme.widget.PlotProcessors.register('formatEntryLabel', function(series, options) {
    var options = $.extend({format: "%s", entryIndex: 0}, options);
    var entryIndex = options.entryIndex;
    var labels = []

    var formatter = function(format, entryIndex) {
        return function(serie, index, data) {return format.format(serie[entryIndex]);};
    }(options.format, entryIndex);

    return series.map(formatter);
});

creme.widget.PlotProcessors.register('ticksLabel', function(series, options) {
    var options = $.extend({labelIndex: 2, seriesIndex: 0}, options);
    var labelIndex = options.labelIndex;
    var seriesIndex = options.seriesIndex;
    var serie = seriesIndex < series.length ? series[seriesIndex] : [];

    return serie.map(new Generator().get(labelIndex).iterator());
});

creme.widget.PlotProcessors.register('seriesLabel', function(series, options) {
    var options = $.extend({defaults: {}, labelIndex: 3, entryIndex: 0}, options);
    var labelIndex = options.labelIndex;
    var entryIndex = options.entryIndex;
    var seriesDefaults = options.defaults;

    return series.map(new Generator().get(entryIndex)
                                     .each(function(value, index, data) {
                                               return $.extend({},
                                                               seriesDefaults,
                                                               {'label': ArrayTools.get(value, labelIndex, '')});
                                           })
                                     .iterator());
});

creme.widget.PlotProcessors.register('seriesColor', function(series, options) {
    var options = $.extend({colorIndex: 2, entryIndex: 0, defaultColor: '#cccccc'}, options);
    var colorIndex = options.colorIndex;
    var entryIndex = options.entryIndex;
    var defaultColor = options.defaultColor;

    return series.map(new Generator().get(entryIndex)
                                     .each(function(value, index, data) {
                                               return ArrayTools.get(value, colorIndex, defaultColor);
                                           })
                                     .iterator());
});

creme.widget.PlotProcessors.register('swap', function(series, options) {
    var options = $.extend({index: 0, next: 1}, options);
    return series.map(function(serie, index, data) {
        return serie.map(GeneratorTools.array.swap(options.index, options.next));
    });
});

creme.widget.PlotProcessors.register('fill', function(series, options) {
    var options = $.extend({index: 0, value: 0}, options);
    return series.map(function(serie, index, data) {
        return serie.map(function(value, index, data) {
            var res = value.slice();
            res.splice(options.index, 0, options.value);
            return res;
        });
    });
});

creme.widget.PlotProcessors.register('index', function(series, options) {
    var options = $.extend({index: 0}, options);
    return series.map(function(serie, s_index, data) {
        return serie.map(function(value, index, data) {
            var res = value.slice();
            res.splice(options.index, 0, index);
            return res;
        });
    });
});

creme.widget.PlotProcessors.register('tee', function(series, options) {
    var result = []

    series.map(function(serie) {
        serie.map(function(value) {result.push([value]);});
    });

    return result;
});

creme.widget.PlotProcessors.register('percentSerie', function(series, options) {
    var options = $.extend({seriesIndex: 0, valueIndex: 0}, options);
    var entryIndex = options.entryIndex;
    var seriesIndex = options.seriesIndex;
    var serie = seriesIndex < series.length ? series[seriesIndex] : [];

    var total = 0.0;
    serie.map(new Generator().get(entryIndex)
                             .each(function(value) {total += value;})
                             .iterator());

    return serie.map(new Generator().each(GeneratorTools.array.ratio(entryIndex, total, 100.0))
                                    .iterator());
});

creme.widget.PlotProcessors.register('percentEntry', function(series, options) {
    var options = $.extend({valueIndex: 0, targetIndex: undefined}, options);
    var valueIndex = options.valueIndex;
    var targetIndex = options.targetIndex;

    var total = 0.0;
    var serieTotalIterator = new Generator().get(valueIndex)
                                            .each(function(value) {total += value;})
                                            .iterator();

    // eval total
    series.map(function(serie, index, data) {serie.map(serieTotalIterator);});

    var seriePercentIterator = new Generator().each(GeneratorTools.array.ratio(valueIndex, total, 100, targetIndex))
                                              .iterator();

    // eval ratio
    return series.map(function(serie, index, data) {
        return serie.map(seriePercentIterator);
    });
});

creme.widget.PlotProcessors.register('format', function(series, options) {
    var options = $.extend({format: "%s", targetIndex: undefined}, options);

    var formatIterator = new Generator().each(GeneratorTools.array.format(options.format,
                                                                          options.targetIndex))
                                        .iterator();

    return series.map(function(serie, index, data) {
        return serie.map(formatIterator);
    });
});
