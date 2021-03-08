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

creme.widget.PlotEventHandlerRegistry = function() {
    this._handlers = {};
};

creme.widget.PlotEventHandlerRegistry.prototype = {
    register: function(name, handler) {
        if ($.isFunction(this.get(name, null))) { throw new Error('handler "' + name + '" is already registered'); }

        this._handlers[name] = handler;
    },

    unregister: function(name) {
        if (this.get(name) === undefined) { throw new Error('no such handler "' + name + '"'); }

        delete this._handlers[name];
    },

    get: function(name, defaults) {
        var handler = this._handlers[name];

        if ($.isFunction(handler) === false) {
            if (defaults === undefined) { throw new Error('no such plot event handler "' + name + '"'); }

            return defaults;
        }

        return this._handlers[name];
    }
};


creme.widget.PlotEventHandlers = new creme.widget.PlotEventHandlerRegistry();

creme.widget.PlotEventHandlers.register('redirect', function(event, seriesIndex, pointIndex, value, options) {
    var url = options.url.format(value);

    if (options.url !== url && !Object.isEmpty(url)) {
        window.location = url;
    }
});

creme.widget.PlotEventHandlers.register('popup', function(event, seriesIndex, pointIndex, value, options) {
    var url = options.url.format(value);

    if (options.url !== url && !Object.isEmpty(url)) {
        creme.dialogs.url(options.url.format(value), {'title': options.url.format(value)}).open();
    }
});


creme.widget.Plot = creme.widget.declare('ui-creme-jqueryplot', {
    options: {
        plotmode:       'svg',
        savable:        false,
        resizable:      false,
        'resize-delay': 200
    },

    _create: function(element, options, cb, sync, attributes) {
        var self = this;
        var can_raster = !$.matchIEVersion(7, 8);

        this._israster = options.plotmode === 'raster' && can_raster;
        this._issavable = (options.savable === true || options.savable === 'true') && can_raster;
        this._plot_info = {options: {}, data: []};
        this._plot_handlers = [];

        element.on('resizestop', function() { self._onResize(element); });

        this.draw(element, this.plotScript(element), cb, cb);
    },

    _rasterImage: function(plot, onload, options) {
        var image = document.createElement("img");
        var str = plot.jqplotToImageStr(options);

        if (Object.isFunc(onload)) {
            image.onload = function() { onload(image); };
        }

        image.src = str;
        return image;
    },

    _popupRasterImage: function() {
        this._rasterImage(this._plot, function(image) {
            creme.dialogs.image(image, {title: gettext('Canvas image')}).open();
        });
    },

    _draw: function(element, plot_info, cb) {
        var width = element.attr('width') || element.width();
        var height = element.attr('height') || element.height();

        var target = $('<div>').width(width)
                               .height(height)
                               .css('margin', '0')
                               .css('border', '0')
                               .css('padding', '0')
                               .attr('id', creme.object.uuid());

        try {
            if (this._israster) {
                this._drawRaster(element, target, plot_info.data, plot_info.options, cb);
            } else {
                this._drawSVG(element, target, plot_info.data, plot_info.options, cb);
            }
        } catch (err) {
            console.error(err);
            target.remove();
            throw err;
        }
    },

    _drawRaster: function(element, target, data, options, cb) {
        target.css('visibility', 'hidden');
        element.append(target);

        if (Object.isEmpty(data)) {
            creme.object.invoke(cb, element);
            return;
        }

        return this._rasterImage(target.jqplot(data, options), function(image) {
            target.remove();
            element.append($('<div>').addClass('jqplot-target')
                                     .append($(image)).css('margin', '0')
                                                      .css('border', '0')
                                                      .css('padding', '0')
                                                      .css('overflow', 'hidden'));
            creme.object.invoke(cb, element);
        });
    },

    _populateSVGActions: function(element, target, options) {
        var self = this;
        var actions = $('<div class="jqplot-actions">');

        if (this._issavable) {
            actions.append($('<button>').attr('title', gettext('View as image'))
                                        .attr('alt', gettext('View as image'))
                                        .attr('name', 'capture')
                                        .on('click', function(e) {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            self._popupRasterImage();
                                         }));
        }

        target.append(actions);
    },

    _drawSVG: function(element, target, data, options, cb) {
        var self = this;

        if (Object.isEmpty(data)) {
            creme.object.invoke(cb, element);
            return;
        }

        element.append(target);

        self._plot = target.jqplot(data, options);
        self._plot_id = target.attr('id');

        self._populateSVGActions(element, target, options);

        self._bindPlotHandlers(self._plot, options);
        creme.object.invoke(cb, element);
    },

    _bindPlotHandlers: function(plot, options) {
        var self = this;

        options.handlers.forEach(function(handler) {
            plot.bind(handler.event,
                      function(event, seriesIndex, pointIndex, data) {
                          handler.action.apply(self, [event, seriesIndex, pointIndex, data, handler]);
                      });
        });
    },

    _jqplotRenderer: function(name) {
        var renderer = name ? $.jqplot[name] : undefined;

        if (typeof renderer !== 'function') {
            throw Error('no such renderer "' + name + '"');
        }

        return renderer;
    },

    _parseJQPlotOptions: function(data) {
        for (var key in data) {
            var value = data[key];

            if (Object.isString(value) && /^jqplot\.[\w\d]+$/.test(value)) {
                data[key] = this._jqplotRenderer(value.substr('jqplot.'.length));
            } else if (typeof value === 'object') {
                this._parseJQPlotOptions(value);
            }
        }

        return data;
    },

    _preprocessPlotHandlers: function(handlers) {
        handlers = handlers || [];
        var built = [];

        handlers.forEach(function(options) {
            options = options || {};
            var name = options.action || 'redirect';

            var eventname = options.event || 'click';
            eventname = eventname.length > 1 ? eventname.substr(0, 1).toUpperCase() + eventname.substr(1).toLowerCase() : eventname;

            built.push($.extend({}, options, {
                event: 'jqplotData' + eventname,
                action: creme.widget.PlotEventHandlers.get(name)
            }));
        });

        return built;
    },

    _convertData: function(data, options) {
        return creme.utils.convert(data, {
            from: options.dataFormat || 'jqplotData',
            to: 'jqplotData',
            defaults: data
        });
    },

    _preprocess: function() {
        var plot_info = this._plot_info;

        if (plot_info.built !== undefined) { return plot_info.built; }

        plot_info.built = creme.widget.PlotProcessors.preprocess(plot_info);
        plot_info.built.options['handlers'] = this._preprocessPlotHandlers(plot_info.built.options.handlers);

        if (this._issavable) {
            plot_info.built.options['title'] = plot_info.built.options.title || '&nbsp;';
        }

        return plot_info.built;
    },

    _onDrawSuccess: function(element, data, cb) {
        // console.log('success:', element, data);
        element.addClass('widget-ready').attr("status", "valid");
        element.trigger('plotSuccess', [this._plot, data]);
        creme.object.invoke(cb, element);
    },

    _onDrawError: function(element, err, data, cb) {
        // console.error(element ? element[0] : undefined, (err && err.message) ? err.message : err, (err && err.stack) ? err.stack : '');
        element.addClass('widget-ready').attr("status", "error");
        element.trigger('plotError', [err, data]);
        creme.object.invoke(cb, element);
    },

    _onBeforeDraw: function(element) {
        element.removeClass('widget-ready');
        this.clear(element);
        element.attr("status", "wait");
    },

    _onResize: function(element) {
        var self = this;
        var delay = this.options['resize-delay'] || 0;

        if (this.options.resize === false || element.is('[status="wait"]')) { return; }

        creme.object.deferred_start(element, 'jqplot-resize', function() {
            self.redraw(element);
        }, delay);
    },

    clear: function(element, status) {
        $('> .jqplot-target', element).remove();
        element.attr("status", status || "valid");
    },

    draw: function(element, data, cb, error_cb) {
        var self = this;

        try {
            self._onBeforeDraw(element);
            self.plotInfo(element, data);

            self._draw(element, self._preprocess(), function() {
                self._onDrawSuccess(element, data, cb);
            });
        } catch (err) {
            self._onDrawError(element, err, data, error_cb);
        }
    },

    redraw: function(element, cb, error_cb) {
        var self = this;
        var info = null;

        try {
            self._onBeforeDraw(element);
            info = self._preprocess();

            self._draw(element, info, function() {
                self._onDrawSuccess(element, info, cb);
            });
        } catch (err) {
            self._onDrawError(element, err, info, error_cb);
        }
    },

    plotOptions: function(element, options) {
        if (options === undefined) {
            return this._plot_info.options;
        }

        var cleaned_options = creme.utils.JSON.clean(options);

        this._plot_info.options = this._parseJQPlotOptions(cleaned_options || {});
        this._plot_info.built = undefined;
    },

    plotData: function(element, data) {
        if (data === undefined) {
            return this._plot_info.data;
        }

        var cleaned_data = creme.utils.JSON.clean(data);
        this._plot_info.data = this._convertData(cleaned_data, this._plot_info.options);
        this._plot_info.built = undefined;
    },

    plotInfo: function(element, source) {
        if (source === undefined) {
            return this._plot_info;
        }

        var plot_info = this._plot_info;

        if (Object.isEmpty(source)) {
            plot_info = {options: {}, data: []};
            return;
        }

        var rawdata = creme.utils.JSON.clean(source);
        var data = Array.isArray(rawdata) ? {data: rawdata} : rawdata;

        plot_info.options = this._parseJQPlotOptions(data.options || plot_info.options);
        plot_info.data = this._convertData(data.data, plot_info.options);
        plot_info.built = undefined;
    },

    plotScript: function(element) {
        var script = $('> script[type$="/json"]', element);
        return creme.utils.JSON.readScriptText(script, {ignoreEmpty: true});
    },

    plot: function(element) {
        return this._plot;
    },

    preprocess: function(element) {
        return this._preprocess();
    },

    isSavable: function(element) {
        return this._issavable;
    },

    capture: function(element, cb) {
        var img;

        if (this._israster) {
            img = $(element, '.jqplot-target img');
            creme.object.invoke(cb, img.get());
        } else {
            img = $(this._rasterImage(this._plot, cb));
        }

        return img;
    }
});
}(jQuery));
