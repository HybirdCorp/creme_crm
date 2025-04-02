/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2025  Hybird

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

creme.D3ChartBrickController = creme.component.Component.sub({
    _init_: function(options) {
        options = options || {};

        var chart = options.chart;

        Assert.not(Object.isNone(chart), 'D3ChartBrickController must have a creme.D3Chart');
        Assert.is(chart, creme.D3Chart, '${chart} is not a creme.D3Chart', options);

        this._chart = chart;
        this._sketch = new creme.D3Sketch();
        this._model = new creme.model.Array([]);
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'D3ChartBrickController is already bound');

        var model = this._model;
        var element = brick.element();
        var container = element.find('.brick-d3-content');

        this._brick = brick;

        if (container.length > 0) {
            this._sketch.bind(container);
        }

        this._chart.props(this.initialProps())
                   .sketch(this._sketch)
                   .model(model);

        model.reset(this.initialData());
    },

    initialData: function() {
        var script = $('script[type$="/json"].sketch-chart-data:first', this._brick.element());
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? [] : JSON.parse(data);
    },

    initialProps: function() {
        var script = $('script[type$="/json"].sketch-chart-props:first', this._brick.element());
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? {} : JSON.parse(data);
    },

    sketch: function() {
        return this._sketch;
    },

    chart: function() {
        return this._chart;
    },

    model: function() {
        return this._model;
    },

    registerActions: function(brick) {
        var self = this;

        Assert.is(brick, creme.bricks.Brick, '${brick} is not a creme.bricks.Brick', {brick: brick});

        brick.getActionBuilders().registerAll({
            'sketch-download': function(url, options, data, e) {
                options = Object.assign({
                    filename: url,
                    width: $(window).innerWidth(),
                    height: $(window).innerHeight()
                }, options || {});

                return new creme.D3ChartBrickDownloadAction(this._brick, self.chart(), options);
            },
            'sketch-popover': function(url, options, data, e) {
                options = Object.assign({
                    width: $(window).innerWidth() * 0.8,
                    height: $(window).innerHeight() * 0.8
                }, options || {});

                return new creme.D3ChartBrickPopoverAction(this._brick, self.chart(), options);
            }
        });
    }
});

creme.D3ChartBrickDownloadAction = creme.component.Action.sub({
    _init_: function(brick, chart, options) {
        options = options || {};

        this._brick = brick;
        this._chart = chart;
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = Object.assign({}, this.options(), options || {});

        var self = this;

        this._chart.saveAs(function() {
            self.done();
        }, options.filename, options);
    }
});

creme.D3ChartBrickPopoverAction = creme.component.Action.sub({
    _init_: function(brick, chart, options) {
        options = options || {};

        this._brick = brick;
        this._chart = chart;
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = Object.assign({}, this.options(), options || {});

        var self = this;

        this._chart.asImage(function(image) {
            if (image) {
                var dialog = creme.dialogs.image(image, {title: self._brick.title()});

                dialog.on('closed', function() {
                    self.done();
                }).open();
            } else {
                self.done();
            }
        }, options);
    }
});

creme.setupD3ChartBrick = function(element, options) {
    var controller = new creme.D3ChartBrickController(options);

    $(element).on('brick-ready', function(e, brick) {
        controller.bind(brick);
    }).on('brick-setup-actions', function(e, brick, actions) {
        controller.registerActions(brick);
    });

    return controller;
};

}(jQuery));
