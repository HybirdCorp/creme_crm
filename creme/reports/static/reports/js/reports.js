/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

creme.reports.load = function(options, hfilters_url, efilters_url) {
    options = options || {};

    if (Object.isEmpty(options)) {
        return;
    }

    var ct_id = $(options.ct).val();
    var $hf = $(options.hf);
    this.loadHeaderFilters(hfilters_url, ct_id, $hf);

    var $filter = $(options.filter);
    this.loadEntityFilters(efilters_url, ct_id, $filter);
};

// TODO: Could use creme.forms.Select.optionsFromData & creme.forms.Select.fill with a hack for default/error options?
var __loadFilters = function(url, ct_id, $target_select, parameters) {
    if ($target_select.size() !== 1) {
        return;
    }

    var params = $.extend({
        'err_label':     gettext("None available"),
        'always_option': null, // Always the 1st option in non-empty success cases
        'empty_option':  null,
        'error_option':  null
    }, parameters);

    var default_option = $('<option value="">' + params.err_label + '</option>');

    var success_cb = function(data) {
        $target_select.empty();

        if (Object.isEmpty(data)) {
            if (params.empty_option) {
                $target_select.append(params.empty_option);
            } else {
                $target_select.append(default_option);
            }
        } else if (params.always_option) {
            $target_select.append(params.always_option);
        }

        for (var i in data) {
            var d = data[i];
            $target_select.append($('<option value="' + d[0] + '">' + d[1] + '</option>'));
        }
    };

    var error_cb = function(data, err) {
        // WTF: 'error_option' not used ?!
        if (params.error_option) {
            $target_select.empty().append(params.empty_option);
        } else {
            $target_select.empty().append(default_option);
        }
    };

    creme.ajax.query(url)
              .onDone(success_cb)
              .onFail(error_cb)
              .get();
};

creme.reports.loadHeaderFilters = function(url, ct_id, $target_select) {
    url = url + '?' + $.param({ct_id: ct_id});
    var params = {
        'always_option': $('<option value="">' + gettext("No selected view") + '</option>')
    };
    __loadFilters(url, ct_id, $target_select, params);
};

creme.reports.loadEntityFilters = function(url, ct_id, $target_select) {
    url = url + '?' + $.param({ct_id: ct_id});
    var $all_opt = $('<option value="">' + gettext("All") + '</option>');
    var params = {
        'empty_option': $all_opt,
        'always_option': $all_opt,
        'error_option': $all_opt
    };
    __loadFilters(url, ct_id, $target_select, params);
};

creme.reports.toggleDisableOthers = function(me, others) {
    var is_checked = me.checked; // More generic with all node types ?
    $.each(others, function(i, n) {
        $(n).attr('disabled', is_checked);
    });
};

creme.utils.converters.register('creme.graphael.BargraphData', 'jqplotData', function(data) {
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
        } else if ($.isArray(value)) {
            item = [tick, clean_float(value[0]), value[1]];
        } else {
            item = [tick, value, undefined];
        }

        jqplotData.push(item);
    }

    return jqplotData.length ? [jqplotData] : [];
});

/* 
 * Moved to reports-actions.js
creme.reports.exportReport = function(title, filterform_url, export_preview_url, export_url) {
    // The export view uses the 'callback_url' feature of inner_popup (maybe only used here).
    // Emulate it for this case.
    // TODO : filterform should be used as select and redirection url build in js.
    creme.dialogs.form(filterform_url, {'title': title || ''})
                 .on('frame-activated', function(event, frame) {
                      new creme.reports.PreviewController(export_preview_url, export_url).bind(frame.delegate());
                  })
                 .onFormSuccess(function(event, data, statusText, dataType) {
                      creme.utils.goTo($(data).attr('redirect'));
                  })
                 .open({width: 1024});
});
*/

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

    bind: function(element) {
        if (this._header !== undefined) {
            throw new Error('creme.reports.PreviewController is already bound.');
        }

        var listeners = this._listeners;
        var header = this._header = $('.report-preview-header', element);

        $('select[name="date_field"]', header).change(listeners.update);
        $('button[name="generate"]', header).click(listeners.redirect);
        $('button[name="download"]', header).click(listeners.download);

        this._updateHeader();
        return this;
    },

    unbind: function(element) {
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
        creme.utils.goTo(this._redirectUrl + '?' + $('form', this._header).serialize());
    },

    download: function() {
        creme.utils.goTo(this._downloadUrl + '?' + $('form', this._header).serialize());
    }
});

// TODO : TEMPORARY HACK !
creme.reports.toggleDaysField = function(operator, types) {
    var is_visible = operator.val() && types && types.indexOf(operator.val()) !== -1;
    var days_field = $(operator).parents('.block-form:first').find('[name=\"days\"]');

    days_field.parents('tr:first').toggleClass('hidden', !is_visible);
};

creme.reports.ChartController = creme.component.Component.sub({
    // _init_: function(preview_url, export_url) {
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

                return $('<a class="popover-list-item" title="%s" alt="%s">%s</a>'.format(label, label, label)).click(function(e) {
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

        $('.graph-controls-type .graph-control-value', element).click(function(e) {
            e.stopPropagation();
            chartPopover.fill(popoverContent(chartPopover, properties.charts, state.chart))
                        .toggle(this);
        });

        $('.graph-controls-sort .graph-control-value', element).click(function(e) {
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
