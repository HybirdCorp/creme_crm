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
            var count = (this._listview.selectedRows() || []).length;

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
                selectionMode: creme.lv_widget.ListViewSelectionMode.SINGLE
            }, options || {});

            this._listview = listview;
            this.selectionMode(options.selectionMode);
        },

        isBound: function() {
            return Object.isNone(this._element) === false;
        },

        bind: function(element) {
            if (this.isBound()) {
                throw new Error('ListViewSelectionController is already bound');
            }

            var self = this;

            element.on('click', 'tr.selectable', function(e) {
                var target = $(e.target);

                // Ignore clicks on links, they should not select the row
                var isClickFromLink = target.is('a') || target.parents('a:first').length === 1;

                if (!isClickFromLink) {
                    self.toggle($(this));
                }
            });

            element.on('click', '[name="select_all"]', function(e) {
                self.toggleAll($(this).prop('checked'));
            });

            this._element = element;
            return this;
        },

        store: function() {
            return this._element.find('.lv-state-field[name="selected_rows"]');
        },

        _updateStore: function() {
            var data = this.selectables().filter('.selected')
                                         .find('[name="entity_id"]')
                                         .map(function() { return this.value; })
                                         .get().join(',');

            this.store().val(data);
        },

        selectionMode: function(mode) {
            if (mode === undefined) {
                return this._selectionMode;
            }

            this._selectionMode = creme.lv_widget.checkSelectionMode(mode);
            return this;
        },

        isMultiple: function() {
            return this.selectionMode() === creme.lv_widget.ListViewSelectionMode.MULTIPLE;
        },

        isSingle: function() {
            return this.selectionMode() === creme.lv_widget.ListViewSelectionMode.SINGLE;
        },

        isEnabled: function() {
            return this.selectionMode() !== creme.lv_widget.ListViewSelectionMode.NONE;
        },

        selected: function() {
            var value = this.store().val();
            return value ? value.split(',') : [];
        },

        count: function() {
            return this.selected().length;
        },

        selectables: function() {
            return this._element.find('tr.selectable');
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
            if (!this.isEnabled()) {
                return this;
            }

            if (!this.isMultiple()) {
                if (rows.length > 1 && state !== false) {
                    throw new Error('Unable to toggle/select more than one row at once');
                }

                this._updateSelection(this.selectables().not(rows), false);
            }

            return this._updateSelection(rows, state);
        },

        toggleAll: function(state) {
            if (!this.isEnabled()) {
                return this;
            }

            return this.toggle(this.selectables(), state);
        }
    });

    var ListViewController = creme.component.Component.sub({
        _init_: function(options) {
            options = $.extend({
                selectionMode:  creme.lv_widget.ListViewSelectionMode.SINGLE,
                reloadUrl:      null,
                submitOnKey:    $.ui.keyCode.ENTER
            }, options || {});

            this._events = new creme.component.EventHandler();
            this._actionBuilders = new creme.lv_widget.ListViewActionBuilders(this);
            this._selections = new ListViewSelectionController(this, {
                selectionMode: options.selectionMode
            });

            this._element = null;
            this._loading = false;

            this.selectionMode(options.selectionMode);
            this.reloadUrl(options.reloadUrl);
            this.submitOnKey(options.submitOnKey);
        },

        isBound: function() {
            return Object.isNone(this._element) === false;
        },

        isLoading: function() {
            return this._loading;
        },

        element: function() {
            return this._element;
        },

        selectionMode: function(value) {
            if (value === undefined) {
                return this._selectionMode;
            }

            value = creme.lv_widget.checkSelectionMode(value);
            this._selections.selectionMode(value);
            this._selectionMode = value;
            return this;
        },

        selectedRows: function() {
            return this.isBound() ? this._selections.selected() : [];
        },

        selectedRowsCount: function() {
            return this.isBound() ? this._selections.count() : 0;
        },

        hasSelectedRows: function() {
            return this.selectedRowsCount() > 0;
        },

        isSelectionEnabled: function() {
            return this.isBound() && this._selections.isEnabled();
        },

        isSingleSelectionMode: function() {
            return this.isBound() && this._selections.isSingle();
        },

        isMultipleSelectionMode: function() {
            return this.isBound() && this._selections.isMultiple();
        },

        clearSelectedRows: function() {
            if (this.isBound()) {
                this._selections.toggleAll(false);
            }
        },

        reloadUrl: function(value) {
            return Object.property(this, '_reloadUrl', value);
        },

        actionBuilders: function() {
            return this._actionBuilders;
        },

        submitOnKey: function(value) {
            return Object.property(this, '_submitOnKey', value);
        },

        on: function(event, listener, decorator) {
            this._events.on(event, listener, decorator);
            return this;
        },

        off: function(event, listener) {
            this._events.off(event, listener);
            return this;
        },

        one: function(event, listener) {
            this._events.one(event, listener);
            return this;
        },

        trigger: function(event, data) {
            if (this.isBound()) {
                this._element.trigger('listview-' + event, (data || []).concat([this]));
            }

            this._events.trigger(event, data, this);
            return this;
        },

        stateField: function(key) {
            return this._element.find('.lv-state-field[name="' + key + '"]');
        },

        state: function() {
            var fields = this._element.find('.lv-state-field');
            var names = Array.copy(arguments);

            if (names.length > 0) {
                fields = fields.filter(function() {
                    return names.indexOf($(this).attr('name')) !== -1;
                });
            }

            return creme.ajax.serializeFormAsDict(fields);
        },

        nextStateUrl: function(data) {
            var link = new creme.ajax.URL(this.reloadUrl());
            return link.updateSearchData(data || {}).href();
        },

        toggleSort: function(column) {
            var prevState = this.state('sort_key', 'sort_order');
            var order = 'ASC';

            if (column === prevState.sort_key[0]) {
                order = prevState.sort_order[0] === 'ASC' ? 'DESC' : 'ASC';
            }

            return this.submitState({
                'sort_key': [column],
                'sort_order': [order]
            });
        },

        _updateLoadingState: function(state) {
            if (state !== this.isLoading()) {
                /* TODO : Toggle css class like bricks
                this._element.toggleClass('is-loading', state);
                */

                this._loading = state;

                if (state) {
                    creme.utils.showPageLoadOverlay();
                } else {
                    creme.utils.hidePageLoadOverlay();
                }
            }
        },

        _updateLoadingProgress: function(percent) {
            var element = this._element;
            $('.list-header-container', element).attr('data-loading-progress', percent);
            this.trigger('submit-state-progress', [percent]);
        },

        reload: function(listeners) {
            this.submitState({}, listeners);
        },

        submitState: function(data, listeners) {
            var self = this;
            var reloadUrl = this.reloadUrl();
            var state = $.extend(this.state(), data || {});
            var nextStateUrl = this.nextStateUrl(state);
            var element = this._element;

            if (this.isLoading()) {
                return new creme.component.Action(function() {
                    this.cancel();
                }).on(listeners || {}).start();
            }

            var queryData = $.extend({}, state, {content: 1});
            var queryOptions = {
                action: 'POST',
                onDownloadProgress: function(evt) {
                    var percent = 100;

                    if (evt.lengthComputable && evt.total > 0) {
                        percent = Math.trunc(Math.max((evt.loaded / evt.total) * 100, 0) / 20) * 20;
                    }

                    self._updateLoadingProgress(percent);
                }
            };

            creme.ajax.query(reloadUrl, queryOptions, queryData)
                      .onStart(function() {
                          self._updateLoadingState(true);
                          self.clearSelectedRows();
                          self.trigger('submit-state-start', [nextStateUrl]);
                       })
                      .onComplete(function(event, data) {
                          self._updateLoadingState(false);
                          self.trigger('submit-state-complete', [nextStateUrl, data]);
                       })
                      .onDone(function(event, data) {
                          var content = $(data.trim());
                          creme.widget.destroy(element);
                          element.replaceWith(content);
                          creme.widget.create(content);
                          self.trigger('submit-state-done', [nextStateUrl, data]);
                       })
                      .on(listeners || {})
                      .start();

            return this;
        },

        bind: function(element) {
            if (this.isBound()) {
                throw new Error('Listview component is already bound');
            }

            this._element = element;
            this._selections.bind(element);

            this.trigger('setup-actions', [this._actionBuilders]);

            this._bindColumnSort(element);
            this._bindColumnFilters(element);
            this._bindShortKeys(element);
            this._bindActions(element);

            return this;
        },

        _bindColumnSort: function(element) {
            var self = this;

            element.on('click', '.lv-columns-header .lv-column.sortable button:not(:disabled)', function(e) {
                e.preventDefault();
                e.stopPropagation();

                var column = $(this).parent('.lv-column:first');
                self.toggleSort(column.attr('data-column-key'));
            });
        },

        _bindShortKeys: function(element) {
            var self = this;
            var handleSubmitKey = function(e) {
                if (e.keyCode === self.submitOnKey()) {
                    e.preventDefault();
                    self.submitState(creme.ajax.serializeFormAsDict($(e.target)));
                }
            };

            element.on('keydown', '.lv-search-header .lv-column input[type="text"]', handleSubmitKey);
            element.on('keydown', '.lv-search-header .lv-column .lv-search-daterange input', handleSubmitKey);
        },

        /* global creme_media_url */
        _bindColumnFilters: function(element) {
            /* TODO: (genglert) we need a better system to initialize search widget, where each widget
                     manage it's initialization, so an external app can easily add its own widgets.
             */
            var self = this;

            element.find('.lv-search-header .lv-column select')
                   .bind('change', function(e) {
                        e.stopPropagation();
                        self.submitState(creme.ajax.serializeFormAsDict($(this)));
                    });

            var dateinputs = element.find('.lv-search-header .lv-column .lv-search-daterange input');

            dateinputs.each(function() {
                $(this).datepicker({
                    showOn: 'both',
                    dateFormat: $(this).attr('data-format'),
                    buttonImage: creme_media_url('images/icon_calendar.gif'),
                    buttonImageOnly: true
                });
            });
        },

        _bindActions: function(element) {
            var self = this;

            element.find('a[data-action]').each(function() {
                var link = new creme.lv_widget.ListViewActionLink(self);
                link.bind($(this));
            });

            element.find('.row-actions-trigger').map(function() {
                return new ListViewActionMenu($(this), {
                    classes: 'row-actions-popover listview-actions-popover',
                    listview: self
                });
            });

            element.find('.header-actions-trigger').map(function() {
                return new ListViewActionMenu($(this), {
                    classes: 'header-actions-popover listview-actions-popover',
                    anchor: $(this).find('span'),
                    listview: self
                });
            });
        }
    });

    creme.utils.newJQueryPlugin({
        name: 'list_view',
        create: function(options) {
            return new ListViewController(options).bind($(this));
        },
        methods: [
            'selectedRowsCount', 'selectedRows', 'hasSelectedRows',
            'state', 'submitState', 'reload',
            'actionBuilders'
        ],
        properties: [
            'selectionMode', 'reloadUrl', 'submitOnKey', 'isLoading'
        ]
    });

//    var _PUBLIC_METHODS = [
//        "countEntities", "getSelectedEntities",
//        "option", "serializeState",
//        "submitState",
//        "setReloadUrl", "getReloadUrl", "isLoading", "getActionBuilders"
//    ];
//
//    var _noop = function() {};
//
//    $.fn.list_view = function(options) {
//        var isMethodCall = Object.isString(options);
//        var args = Array.prototype.slice.call(arguments, 1);
//
//        $.fn.list_view.defaults = {
//            selectionMode:      creme.lv_widget.ListViewSelectionMode.SINGLE,
//            reloadUrl:          null,
//            historyHandler:     null,
//            actionBuilders:     null,
//            submitOnKey:        $.ui.keyCode.ENTER
//        };
//
//        if (isMethodCall) {
//            if (_PUBLIC_METHODS.indexOf(options) === -1) {
//                throw new Error(options + ' is not a public list_view method');
//            }
//
//            var instance = $.data(this.get(0), 'list_view');
//            return (instance ? instance[options].apply(instance, args)
//                             : undefined);
//        }
//
//        var opts = $.extend($.fn.list_view.defaults, options);
//
//        return this.each(function() {
//            var self = $(this);
//            var me = new ListViewController($(this), opts);
//
//            $.data(this, 'list_view', me);
//
//            me.reloadUrl = opts.reloadUrl;
//            me.historyHandler = (Object.isFunc(opts.historyHandler)) ? opts.historyHandler : false;
//            me.is_loading = false;
//
//            this._actionBuilders = new creme.lv_widget.ListViewActionBuilders(this);
//            this._selections = new ListViewSelectionController(self, {
//                selectionMode: opts.selectionMode
//            });
//
//            self.trigger('listview-setup-actions', [this._actionBuilders]);
//
//            /* **************** Getters & Setters **************** */
//            this.getActionBuilders = function() {
//                return me._actionBuilders;
//            };
//
//            this.getSelectedEntities = function() {
//                return me._selections.selected();
//            };
//
//            this.isSelectionEnabled = function() {
//                return me._selections.isEnabled();
//            };
//
//            this.isSingleSelectionMode = function() {
//                return me._selections.isSingle();
//            };
//
//            this.isMultipleSelectionMode = function() {
//                return me._selections.isMultiple();
//            };
//
//            this.clearRowSelection = function() {
//                me._selections.toggleAll(false);
//            };
//
//            this.countEntities = function() {
//                return me._selections.count();
//            };
//
//            this.option = function(key, value) {
//                if (Object.isString(key)) {
//                    if (value === undefined) {
//                        return opts[key];
//                    }
//                    opts[key] = value;
//                }
//            };
//
//            this.setReloadUrl = function(url) {
//                me.reloadUrl = url;
//                this.option('reloadUrl', url);
//            };
//
//            this.getReloadUrl = function() {
//                return me.reloadUrl || window.location.href;
//            };
//
//            this.isLoading = function() {
//                return me.is_loading;
//            };
//
//            /* **************** Helpers *************************** */
//            this.reload = function() {
//                me.handleSubmit();
//            };
//
//            this.submitState = function(target, data, listener) {
//                data = data || {};
//
//                if (Object.isEmpty($(target).attr('name')) === false) {
//                    data[$(target).attr('name')] = [$(target).val()];
//                }
//
//                me.handleSubmit(data, listener);
//            };
//
//            this.hasSelection = function() {
//                return (this.countEntities() !== 0);
//            };
//
//            this.toggleSort = function(next, target) {
//                var prevColumn = me.getState('sort_key');
//
//                if (prevColumn === next) {
//                    var prevOrder = me.getState('sort_order', 'ASC');
//                    me.setState('sort_order', prevOrder === 'ASC' ? 'DESC' : 'ASC');
//                } else {
//                    me.setState('sort_key', next);
//                    me.setState('sort_order', 'ASC');
//                }
//
//                me.submitState(target);
//            };
//
//            this.bindSortButtons = function() {
//                self.on('click', '.lv-columns-header .lv-column.sortable button:not(:disabled)', function(e) {
//                    e.preventDefault();
//                    e.stopPropagation();
//
//                    var column = $(this).parent('.lv-column:first');
//                    me.toggleSort(column.attr('data-column-key'), this);
//                });
//            };
//
//            this.bindFiltersShortKeys = function() {
//                var handleSubmitKey = function(e) {
//                    if (e.keyCode === opts.submitOnKey) {
//                        e.preventDefault();
//                        me.submitState(e.target);
//                    }
//                };
//
//                self.on('keydown', '.lv-search-header .lv-column input[type="text"]', handleSubmitKey);
//                self.on('keydown', '.lv-search-header .lv-column .lv-search-daterange input', handleSubmitKey);
//            };
//
//            this.bindRowSelection = function() {
//                self.on('click', 'tr.selectable', function(e) {
//                    var $target = $(e.target);
//
//                    // Ignore clicks on links, they should not select the row
//                    var isClickFromLink = $target.is('a') || $target.parents('a').first().length === 1;
//                    if (isClickFromLink) {
//                        return;
//                    }
//
//                    me._selections.toggle($(this));
//                });
//
//                self.on('click', '[name="select_all"]', function(e) {
//                    me._selections.toggleAll($(this).prop('checked'));
//                });
//            };
//
//            /* global creme_media_url */
//            this.buildColumnFilters = function() {
//                /* TODO: (genglert) we need a better system to initialize search widget, where each widget
//                         manage it's initialization, so an external app can easily add its own widgets.
//                */
//                self.find('.lv-search-header .lv-column select')
//                    .bind('change', function(event) {
//                         event.stopPropagation();
//                         me.submitState(this);
//                     });
//
//                    /*var date_inputs = self.find('.lv-search-header .lv-column.datefield input');*/
//                var date_inputs = self.find('.lv-search-header .lv-column .lv-search-daterange input');
//
//                date_inputs.each(function() {
//                   $(this).datepicker({
//                       showOn: 'both',
//                       dateFormat: $(this).attr('data-format'),
//                       buttonImage: creme_media_url('images/icon_calendar.gif'),
//                       buttonImageOnly: true
//                   });
//                });
//            };
//
//            this.buildActions = function() {
//                self.find('a[data-action]').each(function() {
//                    var link = new creme.lv_widget.ListViewActionLink(me);
//                    link.bind($(this));
//                });
//
//                self.find('.row-actions-trigger').map(function() {
//                    return new ListViewActionMenu($(this), {
//                        classes: 'row-actions-popover listview-actions-popover',
//                        listview: me
//                    });
//                });
//
//                self.find('.header-actions-trigger').map(function() {
//                    return new ListViewActionMenu($(this), {
//                        classes: 'header-actions-popover listview-actions-popover',
//                        anchor: $(this).find('span'),
//                        listview: me
//                    });
//                });
//            };
//
//            /* **************** Row selection part **************** */
//
//            // Firefox keeps the checked state of inputs on simple page reloads
//            // we could 1) incorporate those pre-selected rows into our initial selected_ids set
//            //          2) force all checkboxes to be unchecked by default. Either in js here, or
//            //             possibly in HTML (maybe by using lone inputs instead of having them in a <form>)
//
//            /* **************************************************** */
//
//            /* **************** Submit part **************** */
//
//            this.enableEvents = function() {
//                this.bindRowSelection();
//                this.bindSortButtons();
//                this.bindFiltersShortKeys();
//
//                this.buildColumnFilters();
//                this.buildActions();
//                // TODO: add inner edit launch event here
//            };
//
//            this.getState = function(key, defaults) {
//                var value = self.find('.lv-state-field[name="' + key + '"]').val();
//                return Object.isNone(value) ? defaults : value;
//            };
//
//            this.setState = function(key, value) {
//                self.find('.lv-state-field[name="' + key + '"]').val(value);
//            };
//
//            this.serializeState = function() {
//                var data = {};
//
//                self.find('.lv-state-field').serializeArray().forEach(function(e) {
//                    var key = e.name, value = e.value;
//
//                    if (!Object.isEmpty(key) && !Object.isNone(value)) {
//                        if (data[key] === undefined) {
//                            data[key] = [value];
//                        } else {
//                            data[key].push(value);
//                        }
//                    }
//                });
//
//                return data;
//            };
//
//            this.nextStateUrl = function(data) {
//                var link = new creme.ajax.URL(me.getReloadUrl());
//                return link.updateSearchData(data || {}).href();
//            };
//
//            this.handleSubmit = function(data, listener) {
//                data = data || {};
//
//                // TODO : handle multiple listeners. needs before() feature in creme.component.EventHandler
//                listener = $.extend({
//                    done: _noop,
//                    fail: _noop,
//                    complete: _noop,
//                    cancel: _noop
//                }, listener || {});
//
//                if (me.isLoading()) {
//                    listener.cancel('cancel');
//                    listener.complete('cancel');
//                    return;
//                }
//
//                var nextUrl = me.getReloadUrl();
//                var state = $.extend(me.serializeState(), data || {});
//
//                var beforeComplete = listener.beforeComplete;
//                var beforeCompleteWrapper = function(request, status) {
//                    // Calling our beforeComplete callback
//                    me.is_loading = false;
//
//                    // Then user callback
//                    if (Object.isFunc(beforeComplete)) {
//                        beforeComplete(request, status);
//                    }
//                };
//
//                var complete = function(request, status) {
//                    if (Object.isFunc(me.historyHandler)) {
//                        return me.historyHandler(me.nextStateUrl(state));
//                    }
//                };
//
//                creme.utils.ajaxQuery(
//                                nextUrl, {
//                                    action: 'POST',
//                                    warnOnFail: false,
//                                    waitingOverlay: true
//                                },
//                                $.extend({}, state, {content: 1}))
//                           .onStart(function() {
//                                me.is_loading = true;
//                                me.clearRowSelection();
//                            })
//                           .onDone(function(event, data) {
//                                var content = $(data.trim());
//                                creme.widget.destroy(self);
//                                self.replaceWith(content);
//                                creme.widget.create(content);
//                            })
//                           .onComplete(function(event, data, status) {
//                                beforeCompleteWrapper(data, status);
//                                complete(data, status);
//                            })
//                           .onComplete(listener.complete)
//                           .onFail(listener.fail)
//                           .onDone(listener.done)
//                           .start();
//
//                return this;
//            };
//
//            this.clearRowSelection();
//            this.enableEvents();
//        });
//    }; // $.fn.list_view
})(jQuery);
