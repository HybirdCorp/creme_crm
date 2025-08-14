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

/*
 * Requires : creme, jQuery, creme.utils, creme.ajax, creme.dialogs
 */

(function($) {
"use strict";

creme.ReportD3ChartSwapper = creme.component.Component.sub({
    _init_: function(element, options) {
        var self = this;

        options = $.extend({
            debounceDelay: 100
        }, options || {});

        this._charts = {};
        this._element = element;
        this._backend = options.backend || creme.ajax.defaultCacheBackend();
        this._model = new creme.model.AjaxArray(this._backend);
        this._model.url(options.fetchUrl);
        this.debounceDelay(options.debounceDelay);

        this._selectionListeners = {
            change: function(event) {
                return self._onSelectionChange(event);
            }
        };

        this._sketch = new creme.D3Sketch().bind(element.find('.brick-d3-content'));
//        this._sortState = element.find('.graph-controls-sort .graph-control-value').dropdown();
        this._sortState = element.find('.chart-controls-sort .chart-control-value').dropdown();
//        this._chartState = element.find('.graph-controls-type .graph-control-value').dropdown();
        this._plotState = element.find('.chart-controls-plot .chart-control-value').dropdown();

//        element.on('change', '.graph-controls-type .graph-control-value', function(e) {
        element.on('change', '.chart-controls-plot .chart-control-value', function(e) {
            this.swapChart($(e.target).val()).draw();
            this._updateFetchSettings();
        }.bind(this));

//        element.on('change', '.graph-controls-sort .graph-control-value', function(e) {
        element.on('change', '.chart-controls-sort .chart-control-value', function(e) {
            this.model().reverse();
            this._updateFetchSettings();
        }.bind(this));

        this._model.reset(this.initialData());

        this.charts(options.charts);
//        this.swapChart(this._chartState.val());
        this.swapChart(this._plotState.val());
    },

    charts: function(charts) {
        if (charts === undefined) {
            return this._charts;
        }

        Assert.not(Object.isEmpty(charts), 'ReportD3ChartBrickController must have a dict of creme.D3Chart');

        for (var key in charts) {
            var chart = charts[key];
            Assert.is(chart, creme.D3Chart, '${key} : ${chart} is not a creme.D3Chart', {key: key, chart: chart});
        }

        this._charts = charts;
    },

    chart: function() {
        return this._chart;
    },

    selected: function() {
        var chart = this.chart();
        return chart ? chart.selection().selected() : [];
    },

    model: function() {
        return this._model;
    },

    sketch: function() {
        return this._sketch;
    },

    draw: function() {
        Object.values(this._charts).forEach(function(chart) {
            if (chart.hasCanvas()) {
                chart.draw();
            }
        });

        return this;
    },

    debounceDelay: function(delay) {
        return Object.property(this, '_debounceDelay', delay);
    },

    state: function() {
/*        var chart = this._element.find('.graph-controls-type .graph-control-value').val(); */
        var plot = this._element.find('.chart-controls-plot .chart-control-value').val();
//        var sort = this._element.find('.graph-controls-sort .graph-control-value').val();
        var sort = this._element.find('.chart-controls-sort .chart-control-value').val();

/*        return {chart: chart, sort: sort}; */
        return {plot: plot, sort: sort};
    },

    swapChart: function(name) {
        var chart = this._charts[name];

        if (Object.isNone(chart)) {
            console.warn(
                'ReportD3ChartSwapper : unable to swap to the unknown chart "${name}"'.template({name: name})
            );
            return;
        }

        if (this._chart) {
            this._chart.props({visible: false});
            this._chart.selection().off(this._selectionListeners);
        }

        chart.props(this.initialProps()[name] || {})
             .props({visible: true})
             .sketch(this._sketch)
             .model(this._model);

        chart.selection().on(this._selectionListeners);
        this._chart = chart;

        return this;
    },

    _updateFetchSettings: function() {
//        var url = this._element.find('.graph-controls').data('fetchSettingsUrl');
        var url = this._element.find('.chart-controls').data('fetchSettingsUrl');

        _.debounce(function() {
            creme.ajax.query(url, {action: 'post', dataType: 'json'}, this.state()).start();
        }.bind(this), this.debounceDelay() || 0)();
    },

    _onSelectionChange: function(event) {
        var data = this.selected();

        if (data.length > 0 && data[0].url) {
            creme.utils.redirect(data[0].url);
        }
    },

    initialData: function() {
        var script = $('script[type$="/json"].sketch-chart-data:first', this._element);
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? [] : JSON.parse(data);
    },

    initialProps: function() {
        var script = $('script[type$="/json"].sketch-chart-props:first', this._element);
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? {} : JSON.parse(data);
    }
});

creme.setupReportD3ChartBrick = function(element, options) {
    var controller = new creme.ReportD3ChartBrickController(options);

    $(element).on('brick-ready', function(e, brick) {
        controller.bind(brick);
    }).on('brick-setup-actions', function(e, brick, actions) {
        controller.registerActions(brick);
    });

    return controller;
};

creme.ReportD3ChartBrickController = creme.component.Component.sub({
    _init_: function(options) {
        this.props(options || {});
    },

    props: function(props) {
        return Object.property(this, '_props', props);
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'ReportD3ChartBrickController is already bound');

        this._brick = brick;

        if (brick.element().find('.brick-d3-content').length > 0) {
            this._swapper = new creme.ReportD3ChartSwapper(brick.element(), {
                charts: this.props().charts
            });

            this._swapper.draw();
        }
    },

    swapper: function() {
        return this._swapper;
    },

    registerActions: function(brick) {
        var self = this;

        Assert.is(brick, creme.bricks.Brick, '${brick} is not a creme.bricks.Brick', {brick: brick});

        brick.getActionBuilders().registerAll({
            'sketch-download': function(url, options, data, e) {
                options = $.extend({
                    filename: url,
                    width: $(window).innerWidth(),
                    height: $(window).innerHeight()
                }, options || {});

                return new creme.D3ChartBrickDownloadAction(this._brick, self.swapper().chart(), options);
            },
            'sketch-popover': function(url, options, data, e) {
                options = $.extend({
                    width: $(window).innerWidth() * 0.8,
                    height: $(window).innerHeight() * 0.8
                }, options || {});

                return new creme.D3ChartBrickPopoverAction(this._brick, self.swapper().chart(), options);
            }
        });
    }
});

creme.ReportD3ChartListBrickController = creme.component.Component.sub({
    _init_: function(options) {
        this.props(options);
    },

    props: function(props) {
        return Object.property(this, '_props', props);
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    },

    bind: function(brick) {
        Assert.not(this.isBound(), 'ReportD3ChartListBrickController is already bound');

        this._brick = brick;

        var props = this.props();
        var swappers = this._swappers = {};

//        brick.element().find('.graph-row:not(.is-empty)').each(function() {
        brick.element().find('.chart-row:not(.is-empty)').each(function() {
//            swappers[$(this).data('graphId')] = new creme.ReportD3ChartSwapper($(this), {
            swappers[$(this).data('chartId')] = new creme.ReportD3ChartSwapper($(this), {
                charts: props.charts()  // TODO: use constructors instead!
            });
        });

//        brick.element().on('click', '.graph-accordion-title', function(e) {
        brick.element().on('click', '.chart-accordion-title', function(e) {
//            var graphId = $(this).data('graphId');
            var chartId = $(this).data('chartId');

//            brick.element().find('.graph-row').filter(function() {
            brick.element().find('.chart-row').filter(function() {
//                return $(this).data('graphId') === graphId;
                return $(this).data('chartId') === chartId;
//            }).toggleClass('graph-row-collapsed');
            }).toggleClass('chart-row-collapsed');

//            $(this).toggleClass('graph-accordion-expanded');
            $(this).toggleClass('chart-accordion-expanded');

//            if ($(this).is('.graph-accordion-expanded')) {
            if ($(this).is('.chart-accordion-expanded')) {
//                swappers[graphId].draw();
                swappers[chartId].draw();
            }
        });
    },

    swappers: function() {
        return this._swappers;
    }
});

creme.setupReportD3ChartListBrick = function(element, options) {
    var controller = new creme.ReportD3ChartListBrickController(options);

    $(element).on('brick-ready', function(e, brick) {
        controller.bind(brick);
    });

    return controller;
};

}(jQuery));
