/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2019  Hybird

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
 * Dependencies : jQuery / jquery.utils.js
 */

// TODO : To be deleted and all console.log in code also

(function($) {
    "use strict";

    var ListViewActionMenu = creme.component.Component.sub({
        _init_: function(link, options) {
            options = this._options = $.extend({
                direction: 'bottom-right'
            }, options || {});

            var self = this;
            var content = link.find('.listview-actions-container');

            this._listview = options.listview;

            this._dialog = new creme.dialog.Popover(options).fill(content);
            this._dialog.addClass(options.classes || '')
                        .on('opened', function() {
                            self._updateState();
                        });

            link.on('click', function(e) {
                e.stopPropagation();
                self.toggle(options.anchor || e.target);
            });
        },

        // TODO : This method enable action links based on a validation check,
        // we should improve api to use this feature in other cases (like hatbar buttons)
        _updateState: function() {
            var count = (this._listview.getSelectedEntities() || []).length;

            this._dialog.content().find('a[data-row-min], a[data-row-max]').each(function() {
                var min = parseInt($(this).attr('data-row-min'));
                var max = parseInt($(this).attr('data-row-max'));
                var message = '';

                if (!isNaN(min) && min === max && count !== min) {
                    message = ngettext('Select %d row',
                                       'Select %d rows',
                                       min).format(min);
                } else if (!isNaN(min) && count < min) {
                    message = ngettext('Select at least %d row',
                                       'Select at least %d rows',
                                       min).format(min);
                } else if (!isNaN(max) && count > max) {
                    message = ngettext('Select no more than %d row',
                                       'Select no more than %d rows',
                                       max).format(max);
                }

                var disabled = message.length > 0;
                var help = $(this).attr('data-helptext') || '';
                var title = help;

                if (disabled) {
                    title = help ? '%s − %s'.format(help, message) : message;
                }

                $(this).toggleClass('is-disabled', disabled);
                $(this).attr('title', title);
            });
        },

        isOpened: function() {
            return this._dialog.isOpened();
        },

        toggle: function(anchor) {
            this._dialog.toggle(anchor);
            return this;
        },

        close: function() {
            this._dialog.close();
            return this;
        },

        open: function(anchor) {
            this._dialog.open(anchor);
            return this;
        }
    });

    var ListViewSelectionController = creme.component.Component.sub({
        _init_: function(listview, options) {
            options = $.extend({
                multiple: false
            }, options || {});

            this._listview = listview;
            this.multiple(options.multiple);
        },

        store: function() {
            return this._listview.find('#selected_rows');
        },

        _updateStore: function() {
            var data = this.selectables().filter('.selected')
                                         .find('[name="entity_id"]')
                                         .map(function() { return this.value; })
                                         .get().join(',');

            this.store().val(data);
        },

        multiple: function(multiple) {
            return Object.property(this, '_multiple', multiple);
        },

        selected: function() {
            var value = this.store().val();
            return (value !== "") ? value.split(',') : [];
        },

        count: function() {
            return this.selected().length;
        },

        selectables: function() {
            return this._listview.find('tr.selectable');
        },

        _updateSelection: function(rows, state) {
            rows.each(function() {
                var row = $(this);

                row.toggleClass('selected', state);
                row.find('[name="select_one"]').prop("checked", row.is('.selected'));
            });

            this._updateStore();

            rows.each(function() {
                var row = $(this);
                row.trigger('row-selection-changed', {selected: row.is('.selected')});
            });

            return this;
        },

        toggle: function(rows, state) {
            if (!this.multiple()) {
                if (rows.length > 1 && state !== false) {
                    throw new Error('Unable to toggle/select more than one row at once');
                }

                this._updateSelection(this.selectables().not(rows), false);
            }

            return this._updateSelection(rows, state);
        },

        toggleAll: function(state) {
            return this.toggle(this.selectables(), state);
        }
    });

    $.fn.list_view = function(options) {
        var isMethodCall = Object.isString(options);
        var args = Array.prototype.slice.call(arguments, 1);

        $.fn.list_view.defaults = {
            user_page:          '#user_page',
            id_container:       '[name="entity_id"]',
            beforeSubmit:       null,
            afterSubmit:        null,
            o2m:                false,
            serializer:         'input[name][type!="submit"], select[name]',
            submitHandler:      null, // Use handleSubmit in it to easy list view's management
            reload_url:         null,
            historyHandler:     null,
            actionBuilders:     null,
            submitOnKey:        $.ui.keyCode.ENTER
        };

        var _noop = function() {};

        var publicMethods = ["countEntities", "getSelectedEntities",
                             "getSelectedEntities",
                             "option", "serializeState", "ensureSelection",
                             "getSubmit",
                             "setSubmit",
                             "setReloadUrl", "getReloadUrl", "isLoading", "getActionBuilders"];

        if (isMethodCall && $.inArray(options, publicMethods) > -1) {
            var instance = $.data(this.get(0), 'list_view');
            return (instance ? instance[options].apply(instance, args)
                             : undefined);
        }

        return this.each(function() {
            // Constructor
            if (!isMethodCall) {
                var opts = $.extend($.fn.list_view.defaults, options);
                var self = $(this);
                var me = this;

                $.data(this, 'list_view', this);

                me.beforeSubmit     = (Object.isFunc(opts.beforeSubmit))     ? opts.beforeSubmit     : false;
                me.afterSubmit      = (Object.isFunc(opts.afterSubmit))      ? opts.afterSubmit      : false;
                me.submitHandler    = (Object.isFunc(opts.submitHandler))    ? opts.submitHandler    : false;
                me.historyHandler   = (Object.isFunc(opts.historyHandler))   ? opts.historyHandler   : false;
                me.is_loading = false;

                this._actionBuilders = new creme.lv_widget.ListViewActionBuilders(this);
                this._selections = new ListViewSelectionController(self, {multiple: !opts.o2m});

                self.trigger('listview-setup-actions', [this._actionBuilders]);

                /* **************** Getters & Setters **************** */
                this.getActionBuilders = function() {
                    return me._actionBuilders;
                };

                this.getSelectedEntities = function() {
                    return me._selections.selected();
                };

                this.countEntities = function() {
                    return me._selections.count();
                };

                this.option = function(key, value) {
                    if (Object.isString(key)) {
                        if (value === undefined) {
                            return opts[key];
                        }
                        opts[key] = value;
                    }
                };

                this.setSubmit = function(fn) {
                    if (Object.isFunc(fn)) {
                        me.submitHandler = fn;
                    }
                };

                this.getSubmit = function() {
                    if (me.submitHandler) {
                        return me.submitHandler;
                    } else {
                        return _noop; // Null handler
                    }
                };

                this.setReloadUrl = function(url) {
                    me.reload_url = url;
                };

                this.getReloadUrl = function() {
                    return me.reload_url;
                };

                this.isLoading = function() {
                    return me.is_loading;
                };

                /* **************** Helpers *************************** */
                this.reload = function() {
                    me.getSubmit()(null);
                };

                this.hasSelection = function() {
                    return (this.countEntities() !== 0);
                };

                /* TODO : never used. remove it ? */
                /*
                this.ensureSelection = function() {
                    if (!this.hasSelection()) {
                        creme.dialogs.warning(gettext("Please select at least one entity."));
                        return false;
                    }
                    return true;
                };
                */

                this.toggleSort = function(next, target) {
                    var prevColumn = me.getState('sort_key');

                    if (prevColumn === next) {
                        var prevOrder = me.getState('sort_order', 'ASC');
                        me.setState('sort_order', prevOrder === 'ASC' ? 'DESC' : 'ASC');
                    } else {
                        me.setState('sort_key', next);
                        me.setState('sort_order', 'ASC');
                    }

                    me.getSubmit()(target);
                };

                this.enableSortButtons = function() {
                    self.find('.columns_top .column.sortable button:not(:disabled)')
                        .click(function(e) {
                            e.preventDefault();
                            e.stopPropagation();

                            var column = $(this).parent('.column:first');
                            me.toggleSort(column.attr('data-column-key'), this);
                        });
                };

                /* global creme_media_url */
                this.enableFilters = function() {
                    /* TODO: (genglert) we need a better system to initialize search widget, where each widget
                             manage it's initialization, so an external app can easily add its own widgets.
                    */
                    var handleSubmitKey = function(e) {
                        if (e.which === opts.submitOnKey) {
                            e.preventDefault();
                            e.stopPropagation();

                            me.getSubmit()(e.target);
                        }
                    };

                    self.find('.columns_bottom .column input[type="text"]')
                        .bind('keydown', handleSubmitKey);

                    self.find('.columns_bottom .column select')
                        .bind('change', function(event) {
                             event.stopPropagation();
                             me.getSubmit()(this);
                         });

//                    var date_inputs = self.find('.columns_bottom .column.datefield input');
                    var date_inputs = self.find('.columns_bottom .column .lv-search-daterange input');

                    date_inputs.bind('keydown', handleSubmitKey);

                    date_inputs.each(function() {
                       $(this).datepicker({
                           showOn: 'both',
                           dateFormat: $(this).attr('data-format'),
                           buttonImage: creme_media_url('images/icon_calendar.gif'),
                           buttonImageOnly: true});
                    });
                };

                this.enableActions = function() {
                    self.find('a[data-action]').each(function() {
                        var link = new creme.lv_widget.ListViewActionLink(me);
                        link.bind($(this));
                    });

                    self.find('.row-actions-trigger').map(function() {
                        return new ListViewActionMenu($(this), {
                            classes: 'row-actions-popover listview-actions-popover',
                            listview: me
                        });
                    });

                    self.find('.header-actions-trigger').map(function() {
                        return new ListViewActionMenu($(this), {
                            classes: 'header-actions-popover listview-actions-popover',
                            anchor: $(this).find('span'),
                            listview: me
                        });
                    });
                };

                /* **************** Row selection part **************** */
                this.enableRowSelection = function() {
                    self.on('click', 'tr.selectable', function(e) {
                        var $target = $(e.target);

                        // Ignore clicks on links, they should not select the row
                        var isClickFromLink = $target.is('a') || $target.parents('a').first().length === 1;
                        if (isClickFromLink) {
                            return;
                        }

                        me._selections.toggle($(this));
                    });
                };

                this.enableCheckAllBoxes = function() {
                    self.find('[name="select_all"]').bind('click', function(e) {
                        me._selections.toggleAll($(this).prop('checked'));
                    });
                };

                // Firefox keeps the checked state of inputs on simple page reloads
                // we could 1) incorporate those pre-selected rows into our initial selected_ids set
                //          2) force all checkboxes to be unchecked by default. Either in js here, or
                //             possibly in HTML (maybe by using lone inputs instead of having them in a <form>)
                this.clearRowSelection = function() {
                    me._selections.toggleAll(false);
                };
                /* **************************************************** */

                /* **************** Check all boxes part **************** */

                /* **************************************************** */

                /* **************** Submit part **************** */

                this.enableEvents = function() {
                    this.enableRowSelection();
                    this.enableSortButtons();
                    this.enableFilters();
                    this.enableActions();
                    // TODO: add inner edit launch event here
                    if (!opts.o2m) this.enableCheckAllBoxes();
                };

                this.getState = function(key, defaults) {
                    var value = self.find('input[name="' + key + '"]').val();
                    return Object.isNone(value) ? defaults : value;
                };

                this.setState = function(key, value) {
                    self.find('input[name="' + key + '"]').val(value);
                };

                this.serializeState = function() {
                    var data = {};

                    self.find(opts.serializer).serializeArray().forEach(function(e) {
                        me.addParameter(data, e.name, e.value);
                    });

                    data['page'] = data['page'] || $(opts.user_page, self).val();
                    data['selection'] = opts.o2m ? 'single' : 'multiple';

                    delete data['entity_id'];
                    delete data['inner_header_from_url'];

                    return data;
                };

                this.addParameter = function(data, key, value, unique) {
                    if (!Object.isEmpty(key) && !Object.isNone(value)) {
                        if (data[key] === undefined) {
                            data[key] = [value];
                        } else {
                            data[key].push(value);
                        }
                    }
                };

                this.setParameter = function(data, key, value) {
                    if (!Object.isEmpty(key) && !Object.isNone(value)) {
                        data[key] = [value];
                    }
                };

                this.handleSubmit = function(options, target, extra_data) {
                    if (me.isLoading()) {
                        return;
                    }

                    options = $.extend({
                        success: _noop,
                        error: _noop,
                        complete: _noop
                    }, options || {});

                    var next_url = me.reload_url || window.location.pathname;
                    var parameters = $.extend(this.serializeState(), extra_data || {});
                    me.setParameter(parameters, $(target).attr('name'), $(target).val());

                    var beforeComplete = options.beforeComplete;
                    var beforeCompleteWrapper = function(request, status) {
                        // Calling our beforeComplete callback
                        me.is_loading = false;

                        // Then user callback
                        if (Object.isFunc(beforeComplete)) {
                            beforeComplete(request, status);
                        }
                    };

                    var complete = function(request, status) {
                        if (Object.isFunc(me.historyHandler)) {
                            return me.historyHandler(next_url + '?' + $.param(parameters));
                        }
                    };

                    creme.utils.ajaxQuery(next_url, {
                                              action: 'POST',
                                              warnOnFail: false,
                                              waitingOverlay: true
                                          }, parameters)
                               .onStart(function() {
                                    me.is_loading = true;
                                })
                               .onDone(options.success)
                               .onFail(options.error)
                               .onComplete(function(event, data, status) {
                                    beforeCompleteWrapper(data, status);
                                    complete(data, status);
                                })
                               .onComplete(options.complete)
                               .start();

                    this.clearRowSelection();
                };

                this.clearRowSelection();
                this.enableEvents();
            } else {
                if (Object.isFunc(this[options])) {
                    this[options].apply(this, args);
                }
            }
        });
    }; // $.fn.list_view
})(jQuery);
