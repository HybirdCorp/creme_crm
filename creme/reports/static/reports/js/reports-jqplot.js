/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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
 *
 * This temporary package has been created to ease the removal of jQplot codebase
 */

(function($) {
"use strict";

creme.reports = creme.reports || {};

creme.utils.converters().register('creme.graphael.BargraphData', 'jqplotData', function(data) {
    var ticks = data['x'] || [];
    var values = data['y'] || [];
    var jqplotData = [];

    var clean_float = function(value) {
        var res = parseFloat(value);
        return isNaN(res) ? 0.0 : res;
    };

    for (var index = 0; index < Math.min(ticks.length, values.length); ++index) {
        var tick = ticks[index];
        var value = values[index];
        var item;

        if (typeof value === 'string') {
            item = [tick, clean_float(value), undefined];
        } else if (Array.isArray(value)) {
            item = [tick, clean_float(value[0]), value[1]];
        } else {
            item = [tick, value, undefined];
        }

        jqplotData.push(item);
    }

    return jqplotData.length ? [jqplotData] : [];
});


creme.reports.ChartController = creme.component.Component.sub({
    _init_: function(properties) {
        this._properties = properties || {};
    },

    initialize: function(element, initial) {
        var self = this;
        var properties = this._properties || {};
        var plot = this._plot = creme.widget.create($('.ui-creme-plotselector', element));
        var state = $.extend({}, initial);

        var setState = function(data) {
            state = self._state = $.extend({}, state, data);

            $('.graph-controls-type .graph-control-value', element).text(properties.charts[state.chart]);
            $('.graph-controls-sort .graph-control-value', element).text(properties.sorts[state.sort]);

            plot.reload(state);
        };

        var popoverContent = function(popover, choices, selected) {
            choices = Object.entries(choices).filter(function(e) {
                return e[0] !== selected;
            });

            choices = choices.map(function(choice) {
                var value = choice[0], label = choice[1];

//                return $('<a class="popover-list-item" title="%s" alt="%s">%s</a>'.format(label, label, label)).on('click', function(e) {
                return $('<a class="popover-list-item" title="%s">%s</a>'.format(label, label)).on('click', function(e) {
                    e.preventDefault();
                    popover.close(value);
                });
            });

            return choices;
        };

        var chartPopover = new creme.dialog.Popover()
                                           .on('closed', function(event, value) {
                                               setState({chart: value});
                                           });

        var sortPopover = new creme.dialog.Popover({direction: 'right'})
                                          .on('closed', function(event, value) {
                                              setState({sort: value});
                                          });

        chartPopover.fill(popoverContent(chartPopover, properties.charts, state.chart));
        sortPopover.fill(popoverContent(sortPopover, properties.sorts, state.sort));

        $('.graph-controls-type .graph-control-value', element).on('click', function(e) {
            e.stopPropagation();
            chartPopover.fill(popoverContent(chartPopover, properties.charts, state.chart))
                        .toggle(this);
        });

        $('.graph-controls-sort .graph-control-value', element).on('click', function(e) {
            e.stopPropagation();
            sortPopover.fill(popoverContent(sortPopover, properties.sorts, state.sort))
                       .toggle(this);
        });

        setState(initial);
    },

    reset: function() {
        this._plot.resetBackend();
        this._plot.reload(this._state);
    }
});

}(jQuery));
