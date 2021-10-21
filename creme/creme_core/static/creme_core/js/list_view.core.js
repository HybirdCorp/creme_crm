/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021 Hybird

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU Affero General Public License as published by the Free
    Software Foundation, either version 3 of the License, or (at your option) any
    later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
    details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
******************************************************************************/

(function($) {
    "use strict";

    var ListViewColumnFilterBuilders = creme.component.FactoryRegistry.sub({
        _build_select: function(element, options, list) {
            new creme.component.Chosen().activate(element);
            this._element = element.on('change', function(e) {
                e.stopPropagation();
                list.submitState(creme.ajax.serializeFormAsDict($(this)));
            });

            return element;
        },

        /* global creme_media_url */
        _build_daterange: function(element, options, list) {
            $(element).find('input').each(function() {
                $(this).datepicker({
                    showOn: 'both',
                    dateFormat: $(this).data('format'),
                    buttonImage: creme_media_url('images/icon_calendar.gif'),
                    buttonImageOnly: true
                });
            });

            $(element).on('change', 'input', function(e) {
                list.submitState(creme.ajax.serializeFormAsDict(
                    $(element).find('input')
                ));
            });

            $(element).on('keydown', 'input', function(e) {
                if (e.keyCode === list.submitOnKey()) {
                    list.submitState(creme.ajax.serializeFormAsDict(
                        $(element).find('input')
                    ));
                }
            });

            return element;
        },

        _build_text: function(element, options, list) {
            $(element).on('keydown', function(e) {
                if (e.keyCode === list.submitOnKey()) {
                    e.preventDefault();
                    list.submitState(creme.ajax.serializeFormAsDict($(e.target)));
                }
            });

            return element;
        },

        _build_auto: function(element, options, list) {
            creme.widget.create($(element), options);

            $(element).on('change', function(e) {
                var input = creme.widget.input(element);
                list.submitState(creme.ajax.serializeFormAsDict($(input)));
            });

            return element;
        },

        _optWidgetBuilder: function(element) {
            return this.get(element.attr('data-lv-search-widget'));
        },

        _optWidgetData: function(element) {
            var script = $('script[type$="/json"]', element);

            try {
                if (!Object.isEmpty(script)) {
                    var data = creme.utils.JSON.readScriptText(script);
                    return Object.isEmpty(data) ? {} : JSON.parse(data);
                }
            } catch (e) {
                console.warn(e);
            }

            return {};
        },

        create: function(element, list) {
            var data = this._optWidgetData(element);
            var builder = this._optWidgetBuilder(element);

            if (Object.isFunc(builder)) {
                return builder(element, data, list);
            }
        }
    });

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
        // we should improve api to use this feature in other cases (like hatbar
        // buttons)
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
//                var isClickFromLink = target.is('a') || target.parents('a:first').length === 1;
                var isClickFromLink = target.is('a') || target.parents('a').first().length === 1;

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
            this._columnFilterBuilders = new ListViewColumnFilterBuilders(this);
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
                return this._selections.selectionMode();
            }

            this._selections.selectionMode(value);
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

        columnFilterBuilders: function() {
            return this._columnFilterBuilders;
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
                /*
                 * TODO : Toggle css class like bricks
                 * this._element.toggleClass('is-loading', state);
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

            this._bindActions(element);

            this._bindColumnSort(element);
            this._bindColumnFilters(element);

            this.trigger('bind-complete');
            return this;
        },

        _bindColumnSort: function(element) {
            var self = this;

            element.on('click', '.lv-columns-header .lv-column.sortable button:not(:disabled)', function(e) {
                e.preventDefault();
                e.stopPropagation();

//                var column = $(this).parent('.lv-column:first');
                var column = $(this).parent('.lv-column').first();
                self.toggleSort(column.attr('data-column-key'));
            });
        },

        _bindColumnFilters: function(element) {
            var self = this;

            this.trigger('setup-column-filters', [this._columnFilterBuilders]);

            element.find('.lv-column [data-lv-search-widget]').each(function() {
                self._columnFilterBuilders.create($(this), self);
            });
        },

        _bindActions: function(element) {
            var self = this;

            this.trigger('setup-actions', [this._actionBuilders]);

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

            this.trigger('bind-actions-complete', [this._actionBuilders]);
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
            'actionBuilders', 'columnFilterBuilders'
        ],
        properties: [
            'selectionMode', 'reloadUrl', 'submitOnKey', 'isLoading'
        ]
    });
})(jQuery);
