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
            var count = (this._listview.getSelectedEntitiesAsArray() || []).length;

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

    $.fn.list_view = function(options) {
        var isMethodCall = Object.isString(options);
        var args = Array.prototype.slice.call(arguments, 1);

        $.fn.list_view.defaults = {
            user_page:          '#user_page',
            selected_rows:      '#selected_rows',
            selectable_class:   'selectable',
            selected_class:     'selected',
            id_container:       '[name="entity_id"]',
            checkbox_selector:  '[name="select_one"]',
            all_boxes_selector: '[name="select_all"]',
            beforeSubmit:       null,
            afterSubmit:        null,
            o2m:                false,
            entity_separator:   ',',
            serializer:         'input[name][type!="submit"], select[name]',
            submitHandler:      null, // Use handleSubmit in it to easy list view's management
            kd_submitHandler:   null, // Same as submitHandler but for key down events,
            reload_url:         null,
            historyHandler:     null,
            actionBuilders:     null
        };

        var _noop = function() {};

        var publicMethods = ["countEntities", "getSelectedEntities",
                             "getSelectedEntitiesAsArray",
                             "option", "serializeMe", "ensureSelection",
                             "getSubmit", "getKdSubmit",
                             "setSubmit", "setKdSubmit",
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
                var selected_ids = [];
                var self = $(this);
                var me = this;

                $.data(this, 'list_view', this);

                me.beforeSubmit     = (Object.isFunc(opts.beforeSubmit))     ? opts.beforeSubmit     : false;
                me.afterSubmit      = (Object.isFunc(opts.afterSubmit))      ? opts.afterSubmit      : false;
                me.submitHandler    = (Object.isFunc(opts.submitHandler))    ? opts.submitHandler    : false;
                me.kd_submitHandler = (Object.isFunc(opts.kd_submitHandler)) ? opts.kd_submitHandler : false;
                me.historyHandler   = (Object.isFunc(opts.historyHandler))   ? opts.historyHandler   : false;
                me.is_loading = false;

                this._actionBuilders = new creme.lv_widget.ListViewActionBuilders(this);
                self.trigger('listview-setup-actions', [this._actionBuilders]);

                /* **************** Getters & Setters **************** */
                this.getActionBuilders = function() {
                    return me._actionBuilders;
                };

                this.getSelectedEntities = function() {
                    return $(opts.selected_rows, self).val();
                };

                this.getSelectedEntitiesAsArray = function() {
                    var selected = this.getSelectedEntities();
                    return (selected !== "") ? selected.split(opts.entity_separator) : [];
                };

                this.countEntities = function() {
                    return this.getSelectedEntitiesAsArray().length;
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

                this.setKdSubmit = function(fn) {
                    if (Object.isFunc(fn)) {
                        me.kd_submitHandler = fn;
                    }
                };

                this.getSubmit = function() {
                    if (me.submitHandler) {
                        return me.submitHandler;
                    } else {
                        return _noop; // Null handler
                    }
                };

                this.getKdSubmit = function() {
                    if (me.kd_submitHandler) {
                        return me.kd_submitHandler;
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
                this.ensureSelection = function() {
                    if (!this.hasSelection()) {
                        creme.dialogs.warning(gettext("Please select at least one entity."));
                        return false;
                    }
                    return true;
                };

                this.enableSortButtons = function() {
                    self.find('.columns_top .column.sortable')
                        .each(function() {
                            var column = $(this);
                            var column_key = column.attr('data-column-key');
                            var sort_key = self.find('input[name="sort_key"]');
                            var sort_order = self.find('input[name="sort_order"]');

                            column.on('click', 'button:not(:disabled)', function(e) {
                                e.preventDefault();
                                e.stopPropagation();

                                creme.lv_widget.handleSort(sort_key, sort_order, column_key, this, me.getSubmit());
                            });
                        });
                };

                /* global creme_media_url */
                this.enableFilters = function() {
                    /* TODO: (genglert) we need a better system to initialize search widget, where each widget
                             manage it's initialization, so an external app can easily add its own widgets.
                    */
                    self.find('.columns_bottom .column input[type="text"]')
                        .bind('keydown', function(event) {
                             event.stopPropagation();
                             me.getKdSubmit()(event, this);
                         });

                    self.find('.columns_bottom .column select')
                        .bind('change', function(event) {
                             event.stopPropagation();
                             me.getSubmit()(this);
                         });

//                    var date_inputs = self.find('.columns_bottom .column.datefield input');
                    var date_inputs = self.find('.columns_bottom .column .lv-search-daterange input');

                    date_inputs.bind('keydown', function(event) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    me.getKdSubmit()(event, this);
                               });

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
                    self.on('click', '.' + opts.selectable_class,
                        function(e) {
                            var $target = $(e.target);

                            // Ignore clicks on links, they should not select the row
                            var isClickFromLink = $target.is('a') || $target.parents('a').first().length === 1;
                            if (isClickFromLink) {
                                return;
                            }

                            var entity_id = $(this).find(opts.id_container).val();
                            var entity_id_index = $.inArray(entity_id, selected_ids);  // selected_ids.indexOf(entity_id);

                            if (!$(this).hasClass(opts.selected_class)) {
                                if (entity_id_index === -1) {
                                    if (opts.o2m) {
                                        selected_ids = [];
                                        self.find('.' + opts.selected_class).removeClass(opts.selected_class);
                                    }
                                    selected_ids.push(entity_id);
                                    $(opts.selected_rows, self).val(selected_ids.join(opts.entity_separator));
                                }

                                if (!$(this).hasClass(opts.selected_class)) {
                                    $(this).addClass(opts.selected_class);
                                }

                                if (!opts.o2m) {
                                    $(this).find(opts.checkbox_selector).check();
                                }
                                $(this).trigger('row-selection-changed', {selected: true});
                            } else {
                                self.find(opts.all_boxes_selector).uncheck();
                                if (entity_id_index !== -1) {
                                    selected_ids.splice(entity_id_index, 1);
                                }
                                $(opts.selected_rows, self).val(selected_ids.join(opts.entity_separator));
                                if ($(this).hasClass(opts.selected_class)) {
                                    $(this).removeClass(opts.selected_class);
                                }
                                if (!opts.o2m) {
                                    $(this).find(opts.checkbox_selector).uncheck();
                                }
                                $(this).trigger('row-selection-changed', {selected: false});
                            }
                        }
                    );
                };

                // Firefox keeps the checked state of inputs on simple page reloads
                // we could 1) incorporate those pre-selected rows into our initial selected_ids set
                //          2) force all checkboxes to be unchecked by default. Either in js here, or
                //             possibly in HTML (maybe by using lone inputs instead of having them in a <form>)
                this.clearRowSelection = function() {
                    $(opts.selected_rows, self).val('');
                    $(opts.selected_rows, self).trigger('row-selection-changed', {selected: false});

                    self.find('.' + opts.selectable_class + ' .choices input[type="checkbox"],' +
                              opts.all_boxes_selector)
                        .prop('checked', false);
                };
                /* **************************************************** */

                /* **************** Check all boxes part **************** */
                this.enableCheckAllBoxes = function() {
                    self.find(opts.all_boxes_selector)
                    .bind('click',
                        function(e) {
                            var entities = self.find('.' + opts.selectable_class);

                            if ($(this).is(':checked')) {
                                entities.each(function() {
                                    var entity_id = $(this).find(opts.id_container).val();
                                    var entity_id_index = $.inArray(entity_id, selected_ids); // selected_ids.indexOf(entity_id);

                                    if (entity_id_index === -1) {
                                        selected_ids.push(entity_id);
                                    }

                                    if (!$(this).hasClass(opts.selected_class)) {
                                        $(this).addClass(opts.selected_class);
                                    }

                                    if (!opts.o2m) {
                                        $(this).find(opts.checkbox_selector).check();
                                    }
                                    $(this).trigger('row-selection-changed', {selected: true});
                                });
                                $(opts.selected_rows, self).val(selected_ids.join(opts.entity_separator));
                            } else {
                                entities.each(function() {
                                    if ($(this).hasClass(opts.selected_class)) {
                                        $(this).removeClass(opts.selected_class);
                                    }

                                    if (!opts.o2m) {
                                        $(this).find(opts.checkbox_selector).uncheck();
                                    }
                                    $(this).trigger('row-selection-changed', {selected: false});
                                });
                                selected_ids = [];
                                $(opts.selected_rows, self).val('');
                            }
                        }
                    );
                };

                /* **************************************************** */

                /* **************** Submit part **************** */

                // Remove this part in ajax lv for handling multi-page selection,
                // if that you want implement the "coloration" selection on submit
                this.flushSelected = function() {
                    $(opts.selected_rows, self).val('');
                    selected_ids = [];
                };

                this.disableEvents = function() {
                    self.off('click', '.' + opts.selectable_class);
                    if (!opts.o2m) self.find(opts.all_boxes_selector).unbind('click');
                };

                this.enableEvents = function() {
                    this.enableRowSelection();
                    this.enableSortButtons();
                    this.enableFilters();
                    this.enableActions();
                    // TODO: add inner edit launch event here
                    if (!opts.o2m) this.enableCheckAllBoxes();
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

                this.serializeMe = function() {
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

                this.handleSubmit = function(options, target, extra_data) {
                    if (me.is_loading) {
                        return;
                    }

                    options = $.extend({
                        success: _noop,
                        error: _noop,
                        complete: _noop
                    }, options || {});

                    var next_url = me.reload_url || window.location.pathname;
                    var parameters = $.extend(this.serializeMe(), extra_data || {});
                    me.setParameter(parameters, $(target).attr('name'), $(target).val());

                    var beforeComplete = options.beforeComplete;
                    var beforeCompleteWrapper = function(request, status) {
                        // Calling our beforeComplete callback
                        me.is_loading = false;
                        me.enableEvents();

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

                    me.disableEvents();
                    me.is_loading = true;

                    creme.utils.ajaxQuery(next_url, {
                                              action: 'POST',
                                              warnOnFail: false,
                                              waitingOverlay: true
                                          }, parameters)
                               .onDone(options.success)
                               .onFail(options.error)
                               .onComplete(function(event, data, status) {
                                   beforeCompleteWrapper(data, status);
                                   complete(data, status);
                                })
                               .onComplete(options.complete)
                               .start();

                    this.flushSelected();
                };

                this.init = function() {
                    this.clearRowSelection();
                    this.enableEvents();
                };

                this.init();
            } else {
                if (Object.isFunc(this[options])) {
                    this[options].apply(this, args);
                }
            }
        });
    }; // $.fn.list_view
})(jQuery);
