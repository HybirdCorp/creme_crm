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

creme.widget.PlotEventHandlerRegistry = function() {
    this._handlers = {}
}

creme.widget.PlotEventHandlerRegistry.prototype = {
    register: function(name, handler)
    {
        if ($.isFunction(this.get(name, null)))
            throw new Error('handler "' + name + '" is already registered');

        this._handlers[name] = handler;
    },

    unregister: function(name)
    {
        if (this.get(name) === undefined)
            throw new Error('no such handler "' + name + '"');

        delete this._handlers[name];
    },

    get: function(name, defaults)
    {
        var handler = this._handlers[name];

        if ($.isFunction(handler) === false)
        {
            if (defaults === undefined)
                throw new Error('no such plot event handler "' + name + '"');
            
            return defaults;
        }

        return this._handlers[name];
    }
};


creme.widget.PlotEventHandlers = new creme.widget.PlotEventHandlerRegistry();

creme.widget.PlotEventHandlers.register('redirect', function(event, seriesIndex, pointIndex, value, options) {
    var url = options.url.format(value);

    if (options.url !== url && !creme.object.isempty(url)) {
        window.location = url;
    }
});

creme.widget.PlotEventHandlers.register('popup', function(event, seriesIndex, pointIndex, value, options) {
    var url = options.url.format(value);

    if (options.url !== url && !creme.object.isempty(url)) {
        creme.widget.component.Dialogs.openUrl(options.url.format(value), {'title': options.url.format(value)});
    }
});


creme.widget.Plot = creme.widget.declare('ui-creme-jqueryplot', {
    options: {
        plotmode:       'svg',
        savable:        false,
        resizable:      false,
        'resize-delay': 500
    },

    _create: function(element, options, cb, sync, arguments)
    {
        var self = this;
        var can_raster = !$.assertIEVersions(7, 8);

        this._israster = options.plotmode == 'raster' && can_raster;
        this._issavable = options.savable == 'true' && can_raster;
        this._plot_info = {options: {}, data: []}
        this._plot_handlers = [];

        element.bind('resize', function() {self._onResize(element);});

        this.draw(element, this.plotScript(element), cb, cb);
    },

    _rasterImage: function(plot, onload, options)
    {
        var image = document.createElement("img");
        var str = plot.jqplotToImageStr(options);

        image.onload = function() {onload(image);}
        image.src = str;
        return image;
    },

    _popupRasterImage: function(element)
    {
        this._rasterImage(this._plot, function(image) {
            creme.widget.component.Dialogs.openImage(image, 
                                                     {title: gettext('Canvas image')});
        });
    },

    _draw: function(element, plot_info, cb)
    {
        var width = element.attr('width') || element.width();
        var height = element.attr('height') || element.height();

        var target = $('<div>').width(width)
                               .height(height)
                               .css('margin', '0')
                               .css('border', '0')
                               .css('padding', '0')
                               .attr('id', creme.object.uuid());

        try
        {
            if (this._israster) {
                this._drawRaster(element, target, plot_info.data, plot_info.options, cb)
            } else {
                this._drawSVG(element, target, plot_info.data, plot_info.options, cb)
            }
        } catch(err) {
            target.remove();
            throw err;
        }
    },

    _drawRaster: function(element, target, data, options, cb)
    {
        target.css('visibility', 'hidden');
        element.append(target);

        var image = this._rasterImage(target.jqplot(data, options), function() {
            target.remove();
            element.append($('<div>').addClass('jqplot-target')
                                     .append($(image)).css('margin', '0')
                                                      .css('border', '0')
                                                      .css('padding', '0')
                                                      .css('overflow', 'hidden'));
            creme.object.invoke(cb, element);
        });
    },

    _drawSVG: function(element, target, data, options, cb)
    {
        var self = this;

        element.append(target);

        self._plot = target.jqplot(data, options);
        self._plot_id = target.attr('id');

        if (this._issavable)
        {
            var button = $('<button>').text(gettext('View as image'))
                                      .bind('click', function() {self._popupRasterImage();})
                                      .css('position', 'absolute')
                                      .css('z-index', '1')
                                      .css('right', 5);
            target.append(button);
        }

        self._bindPlotHandlers(self._plot, options);

        creme.object.invoke(cb, element);
    },

    _bindPlotHandlers: function(plot, options)
    {
        var self = this;

        options.handlers.forEach(function(handler) {
            plot.bind(handler.event,
                      function(event, seriesIndex, pointIndex, data) {
                          handler.action.apply(self, [event, seriesIndex, pointIndex, data, handler]);
                      })
        });
    },

    _jqplotRenderer: function(name)
    {
        var renderer = name ? $.jqplot[name] : undefined;

        if (typeof renderer !== 'function')
            throw 'no such renderer "' + name + '"';

        return renderer;
    },

    _parseJQPlotOptions: function(data)
    {
        for(key in data)
        {
            var value = data[key];

            if (typeof value === 'object') {
                this._parseJQPlotOptions(value);
            } else if (typeof value === 'string' && /^jqplot\.[\w\d]+$/.test(value)) {
                data[key] = this._jqplotRenderer(value.substr('jqplot.'.length));
            }
        }

        return data;
    },

    _preprocessPlotHandlers: function(handlers)
    {
        var handlers = handlers || [];
        var built = [];

        handlers.forEach(function(options) {
            var options = options || {};
            var name = options.action || 'redirect';

            var eventname = options.event || 'click';
            var eventname = eventname.length > 1 ? eventname.substr(0, 1).toUpperCase() + eventname.substr(1).toLowerCase() : eventname;

            built.push($.extend({}, options, {
                event: 'jqplotData' + eventname,
                action: creme.widget.PlotEventHandlers.get(name)
            }));
        });

        return built;
    },

    _convertData: function(data, options) {
        return $.converters.convert(options.dataFormat || 'jqplotData', 'jqplotData', data);
    },

    _preprocess: function()
    {
        var plot_info = this._plot_info;

        if (plot_info.built !== undefined)
            return plot_info.built;

        plot_info.built = creme.widget.PlotProcessors.preprocess(plot_info);
        plot_info.built.options['handlers'] = this._preprocessPlotHandlers(plot_info.built.options.handlers);

        if (this._issavable) {
            plot_info.built.options['title'] = plot_info.built.options.title || '&nbsp;';
        }

        return plot_info.built;
    },

    _onDrawSuccess: function(element, data, cb)
    {
        //console.log('success:', element, data);
        element.addClass('widget-ready').attr("status", "valid");
        element.trigger('plotSuccess', [this._plot, data]);
        creme.object.invoke(cb, element);
    },

    _onDrawError: function(element, err, data, cb)
    {
        //console.error(element, (err && err.message) ? err.message : err, (err && err.stack) ? err.stack : '');
        element.addClass('widget-ready').attr("status", "error");
        element.trigger('plotError', [err, data]);
        creme.object.invoke(cb, element);
    },

    _onBeforeDraw: function(element)
    {
        element.removeClass('widget-ready');
        this.clear(element);
        element.attr("status", "wait");
    },

    _onResize: function(element)
    {
        var self = this;
        var delay = this.options['resize-delay'] || 0;

        if (this.options.resize === false || element.is('[status="wait"]'))
            return;

        creme.object.deferred_start(element, 'jqplot-resize', function() {
            self.redraw(element);
        }, delay);
    },

    clear: function(element, status) {
        $('> .jqplot-target', element).remove();
        element.attr("status", status || "valid");
    },

    draw: function(element, data, cb, error_cb)
    {
        var self = this;

        try {
            self._onBeforeDraw(element);
            self.plotInfo(element, data);

            self._draw(element, self._preprocess(), function() {
                self._onDrawSuccess(element, data, cb);
            });
        } catch(err) {
            self._onDrawError(element, err, data, error_cb);
        }
    },

    redraw: function(element, cb, error_cb)
    {
        var self = this;
        var info = null;

        try {
            self._onBeforeDraw(element);
            info = self._preprocess();

            self._draw(element, info, function() {
                self._onDrawSuccess(element, info, cb);
            });
        } catch(err) {
            self._onDrawError(element, err, info, error_cb);
        }
    },

    plotOptions: function(element, options)
    {
        if (options === undefined)
            return this._plot_info.options;

        var options = (typeof options === 'string') ? new creme.object.JSON().decode(options) : options;
        this._plot_info.options = this._parseJQPlotOptions(options || {});
        this._plot_info.built = undefined;
    },

    plotData: function(element, data)
    {
        if (data === undefined)
            return this._plot_info.data;

        var data = (typeof data === 'string') ? new creme.object.JSON().decode(data) : data;
        this._plot_info.data = this._convertData(data, this._plot_info.options);
        this._plot_info.built = undefined;
    },

    plotInfo: function(element, source)
    {
        if (source === undefined)
            return this._plot_info;

        var self = this;
        var plot_info = this._plot_info;

        if (creme.object.isempty(source)) {
            plot_info = {options: {}, data: []};
            return;
        }

        var rawdata = (typeof source === 'string') ? new creme.object.JSON().decode(source) : source;
        var data = $.isArray(rawdata) ? {data: rawdata} : rawdata;

        plot_info.options = this._parseJQPlotOptions(data.options || plot_info.options);
        plot_info.data = this._convertData(data.data, plot_info.options);
        plot_info.built = undefined;
    },

    plotScript: function(element) {
        return $('> script[type="text/json"]', element).html();
    },

    plot: function(element) {
        return this._plot;
    },

    preprocess: function(element) {
        return this._preprocess();
    }
});
