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

/*
 * Requires : creme, jQuery, creme.utils, creme.ajax, creme.dialogs
 */

(function($) {
"use strict";

creme.reports = creme.reports || {};

// creme.reports.ReportFormController = creme.component.Component.sub({
//    _init_: function(options) {
//        console.warn('creme.reports.ReportFormController is deprecated.');
//
//        options = options || {};
//
//        this._backend = options.backend || creme.ajax.defaultCacheBackend();
//        this._hfilters = this._createFilterModel({
//            url: options.hfilterUrl,
//            allLabel: gettext("No selected view")
//        });
//        this._efilters = this._createFilterModel({
//            url: options.efilterUrl,
//            allLabel: gettext("All"),
//            emptyLabel: gettext("All")
//        });
//    },
//
//    _createFilterModel: function(options) {
//        options = $.extend({
//            emptyLabel: gettext("None available")
//        }, options || {});
//
//        if (Object.isEmpty(options.url)) {
//            throw new Error('Unable to create filter model without fetch url');
//        }
//
//        var initial = [{
//            label: options.emptyLabel
//        }];
//
//        var converter = function(rawdata) {
//            var data = creme.model.ChoiceRenderer.choicesFromTuples(creme.utils.JSON.clean(rawdata, []));
//
//            if (Object.isEmpty(data)) {
//                data = initial;
//            } else if (options.allLabel) {
//                data = [{
//                    label: options.allLabel
//                }].concat(data);
//            }
//
//            return data;
//        };
//
//        var model = new creme.model.AjaxArray(this._backend, initial)
//                                   .url(options.url)
//                                   .converter(converter);
//
//        return new creme.model.ChoiceRenderer().model(model);
//    },
//
//    updateFilters: function(ctype) {
//        if (this.isBound()) {
//            if (Object.isEmpty(ctype)) {
//                this._hfilters.model().reset(this._hfilters.model().initial());
//                this._efilters.model().reset(this._efilters.model().initial());
//            } else {
//                this._hfilters.model().fetch({ct_id: ctype});
//                this._efilters.model().fetch({ct_id: ctype});
//            }
//        }
//
//        return this;
//    },
//
//    bind: function(element) {
//        if (this.isBound()) {
//            throw new Error('ReportFilterController is already bound');
//        }
//
//        this._hfilters.target(element.find('select[name="hf"]')).redraw();
//        this._efilters.target(element.find('select[name="filter"]')).redraw();
//
//        var self = this;
//        var ctypes = element.find('select[name="ct"]');
//
//        ctypes.on('change', function() {
//            self.updateFilters($(this).val());
//        });
//
//        this._element = element;
//        self.updateFilters(ctypes.val());
//
//        return this;
//    },
//
//    isBound: function() {
//        return Object.isNone(this._element) === false;
//    }
// });

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

creme.reports.PreviewController = creme.component.Component.sub({
    _init_: function(options) {
        options = options || {};

        this._redirectUrl = options.previewUrl || '';
        this._downloadUrl = options.downloadUrl || '';

        this._listeners = {
            update:   this._updateHeader.bind(this),
            redirect: this.redirect.bind(this),
            download: this.download.bind(this)
        };
    },

    isBound: function() {
        return this._header !== undefined;
    },

    bind: function(element) {
        Assert.not(this.isBound(), 'creme.reports.PreviewController is already bound.');

        var listeners = this._listeners;
        var header = this._header = $('.report-preview-header', element);

        $('select[name="date_field"]', header).on('change', listeners.update);
        $('button[name="generate"]', header).on('click', listeners.redirect);
        $('button[name="download"]', header).on('click', listeners.download);

        this._updateHeader();
        return this;
    },

    unbind: function() {
        Assert.that(this.isBound(), 'creme.reports.PreviewController is not bound.');

        var listeners = this._listeners;
        var header = this._header;

        if (header !== undefined) {
            $('select[name="date_field"]', header).unbind('change', listeners.update);
            $('button[name="generate"]', header).unbind('click', listeners.redirect);
            $('button[name="download"]', header).unbind('click', listeners.download);
        }

        this._header = undefined;
        return this;
    },

    _updateHeader: function() {
        var header = this._header;
        var has_datefield = !Object.isEmpty($('[name="date_field"]', header).val());

        $('.date-filter', header).toggle(has_datefield);

        if (!has_datefield) {
            $('.ui-creme-daterange', header).creme().widget().reset();
        }
    },

    redirect: function() {
        creme.utils.goTo(this._redirectUrl, $('form', this._header).serialize());
    },

    download: function() {
        creme.utils.goTo(this._downloadUrl, $('form', this._header).serialize());
    }
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

                return $('<a class="popover-list-item" title="%s" alt="%s">%s</a>'.format(label, label, label)).on('click', function(e) {
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
