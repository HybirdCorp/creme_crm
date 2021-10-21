/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

(function($) {

"use strict";

creme.widget.PlotSelector = creme.widget.declare('ui-creme-plotselector', {
    options: {
        'plot-data-url': '',
        'plot-name': undefined,
        backend: undefined,
        initial: {}
    },

    _create: function(element, options, cb, sync) {
        var self = this;

        if (Object.isNone(options.backend)) {
            this._backend = new creme.ajax.CacheBackend(creme.ajax.defaultBackend(), {
                condition: new creme.ajax.CacheBackendTimeout(options.cacheTimeout * 1000)
            });
        } else {
            this._backend = options.backend;
        }

        this._plot_data_url = new creme.utils.Template(options['plot-data-url']);
        this._plot_name = (options['plot-name']) ? new creme.utils.Template(options['plot-name']) : undefined;

        options.initial = creme.widget.cleanval(options.initial, {});

        this._initPlot(element, function() {
            self.reload(element, options.initial, cb, cb, sync);
        }, sync);
    },

    _initPlot: function(element, cb, sync) {
//        $('.ui-creme-jqueryplot:first', element).creme().create({}, cb, sync);
        $('.ui-creme-jqueryplot', element).first().creme().create({}, cb, sync);
    },

    _delegate: function(element) {
//        return $('.ui-creme-jqueryplot:first', element).creme().widget();
        return $('.ui-creme-jqueryplot', element).first().creme().widget();
    },

    _updatePlotOptions: function(element, plot, data) {
        try {
            if (Object.isNone(this._plot_name)) {
                plot.plotInfo(plot.plotScript());
                return;
            }

            this._plot_name.update(data);

            var plot_name = this._plot_name.render();
            var plot_options = this.plotOption(element, plot_name);

            if (plot_options === null) {
                plot.plotInfo(plot.plotScript());
                return;
            }

            plot.plotOptions(plot_options);
        } catch (error) {
            throw new Error('unable to update plot options : ' + error);
        }
    },

    _updatePlotData: function(plot, data, cb, options) {
        var self = this;
        var backend = this._backend;
        var plot_data_url = this._plot_data_url;

        plot_data_url.update(data);

        if (plot_data_url.iscomplete() === false) {
            self._plot_last_url = undefined;
            plot.plotData([]);
            throw new Error('incomplete data url');
        }

        var url = plot_data_url.render();

        if (Object.isEmpty(url)) {
            throw new Error('empty data url');
        }

        backend.get(url, {},
                    function(data) {
                        plot.plotData(creme.widget.cleanval(data, []));
                        creme.object.invoke(cb, plot.plotData());
                    },
                    function(data, error) {
                        self._plot_last_url = undefined;
                        plot.plotData([]);
                        creme.object.invoke(cb, plot.plotData());
                    },
                    $.extend({dataType: 'json'}, options));
    },

    plotOptions: function(element) {
        var options = [];

        $('> script[type$="/json"][name]', element).each(function() {
            options.push([$(this).attr('name'), creme.utils.JSON.readScriptText($(this)) || null]);
        });

        return options;
    },

    plotOption: function(element, name) {
        var script = $('> script[type$="/json"][name="' + name + '"]', element);
        return creme.utils.JSON.readScriptText(script, {ignoreEmpty: true}) || null;
    },

    dependencies: function(element) {
        var deps = this._plot_data_url.tags();

        if (this._plot_name) {
            deps = deps.concat(this._plot_name.tags());
        }

        return deps;
    },

    _onRedrawOk: function(element, plot, data, cb) {
        element.addClass('widget-ready');
        creme.object.invoke(cb, element, data);
    },

    _onRedrawError: function(element, plot, error, cb) {
        plot.clear("error");
        element.addClass('widget-ready');
        creme.object.invoke(cb, element, error);
    },

    reload: function(element, data, cb, error_cb, sync, options) {
        var self = this;
        var plot = this._delegate(element);

        if (Object.isNone(plot)) {
            creme.object.invoke(error_cb, element, new Error('Plot not initialized'));
            return;
        }

        try {
            element.removeClass('widget-ready');

            this._updatePlotOptions(element, plot, data);
            this._updatePlotData(plot, data,
                                 function(data) {
                                     plot.redraw(
                                         function() { self._onRedrawOk(element, plot, data, cb); },
                                         function() { self._onRedrawError(element, plot, null, error_cb); }
                                     );
                                 }, options);
        } catch (error) {
            self._onRedrawError(element, plot, error, error_cb);
        }
    },

    // TODO : use a better method for plot cache issue in reports. As temporary fix all cache is cleaned before popupNReload.
    resetBackend: function(element) {
        if (Object.isFunc(this._backend.reset)) {
            this._backend.reset();
        }
    },

    reset: function(element) {
        this._plot_data_url.parameters({});

        if (this._plot_name !== undefined) {
            this._plot_name.parameters({});
        }

        this.reload(element, this.options.initial);
    },

    val: function(element, value) {
        return null;
    },

    cleanedval: function(element) {
        return null;
    }
});

}(jQuery));
