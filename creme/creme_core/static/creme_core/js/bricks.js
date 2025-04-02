/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2025  Hybird

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

creme.bricks = creme.bricks || {};

creme.bricks.dialogCenterPosition = function(dialog) {
    // TODO: simplify this code with new dialog center(constraint) feature
    /*
     * var outer_height = $('.header-menu').outerHeight();
     * dialog.center({top: outer_height});
     */
    var outer_height = $('.header-menu').outerHeight();

    if (dialog.dialog().parents('.ui-dialog').first().position().top < outer_height) {
        dialog.position({
            my: 'center top',
            at: 'center top+' + (2 * outer_height),
            of: window
        });
    }
};

// TODO: a specific 'creme.bricks.Dialog' should be a better idea (combine 'action-link' and 'brick-dialog-action'?)
creme.bricks.dialogActionButtons = function(dialog) {
    var buttons = $('a.brick-dialog-action', dialog.content()).map(function(index) {
        var link = $(this);
        var label = link.contents().map(function() {
                                            return this.nodeType === 3 ? this.data : '';
                                        }).get().join('');

        return {
            'text': label,
            'click': function(e) {
                e.preventDefault();
                creme.utils.goTo(link.attr('href'));
            }
        };
    }).get();

    if (Object.isEmpty(buttons) === false) {
        buttons = buttons.concat(dialog.dialog().dialog('option', 'buttons'));
        dialog.replaceButtons(buttons);

        if (dialog.options.fitFrame) {
            dialog.fitToFrameSize();
        }
    }
};


creme.bricks.defaultDialogOptions = function(url, title) {
    var width = $(window).innerWidth();

    return {
        resizable: true,
        draggable: true,
        width: width * 0.8,
        maxWidth: width,
        url: url,
        title: title,
        validator: 'innerpopup'
    };
};


creme.bricks.BrickMenu = creme.component.Component.sub({
    _init_: function(brick, options) {
        this._options = $.extend({
            direction: 'right'
        }, options || {});

        this._brick = brick;
        this._disabled = true;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('BrickMenu is already bound');
        }

        var toggle = this.toggle.bind(this);
        var content = this._menuContent(element);
        var is_disabled = this._disabled = $('a', content).length < 1;

        this._element = element;
        this._dialog = new creme.dialog.Popover(this._options).fill(content);

        $('.brick-header-menu', element).toggleClass('is-disabled', is_disabled)
                                        .on('click', function(e) {
                                            toggle(e.target);
                                         });
    },

    unbind: function() {
        if (!this.isBound()) {
            throw new Error('BrickMenu is not bound');
        }

        this.close();

        this._dialog = null;
        this._element = null;
        this._disabled = true;
    },

    _menuContent: function(element) {
        return $('.brick-menu-buttons', element);
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    isDisabled: function() {
        return !this.isBound() || this._disabled;
    },

    isOpened: function() {
        return this.isBound() && this._dialog.isOpened();
    },

    toggle: function(anchor) {
        if (!this.isDisabled() && !this._brick.isLoading()) {
            this._dialog.toggle(anchor);
        }
    },

    close: function() {
        if (this.isBound()) {
            this._dialog.close();
        }
    },

    open: function(anchor) {
        if (!this.isDisabled() && !this._brick.isLoading()) {
            this._dialog.open(anchor);
        }
    }
});

creme.bricks.BrickSelectionController = creme.component.Component.sub({
    _init_: function(options) {
        this._options = $.extend({
            rows:     'tr',
            renderer: this._defaultItemStateRenderer,
            parser:   this._defaultItemStateParser
        }, options || {});

        var model = this._model = new creme.model.Array();
        model.bind('update', this._onItemUpdate.bind(this));

        this._selections = new creme.model.SelectionController().model(model);
    },

    _defaultItemStateRenderer: function(item) {
        item.ui.toggleClass('is-selected', item.selected);
    },

    _defaultItemStateParser: function(item, index) {
        return item.is('.is-selected');
    },

    _onItemUpdate: function(event, next, start, end, previous, action) {
        next.forEach(this._options.renderer);
    },

    bind: function(element) {
        var options = this._options;
        var parser = options.parser;

        this._model.reset($(options.rows, element).map(function(index) {
            var item = $(this);
            item.attr('data-row-index', index);

            return {
                selected: parser(item, index),
                ui: item
            };
        }).get());

        return this;
    },

    state: function() {
        return this._selections;
    }
});

// Sigh...
// jQuery UI 1.11 Sortable: the 'start' event is sent *after* the dragged item has been modified to absolute positioning,
// which destroys the table layout. So: hijack the start of the process to send an event before this happens.
// HACK: can break in later versions than 1.11
if ($.ui.sortable.prototype._nativeMouseStart === undefined) {
    var _nativeMouseStart = $.ui.sortable.prototype._mouseStart;
    $.ui.sortable.prototype._nativeMouseStart = _nativeMouseStart;

    $.ui.sortable.prototype._mouseStart = function (event, overrideHandle, noActivation) {
        this._trigger('beforeStart', event, this._uiHash());
        _nativeMouseStart.apply(this, [event, overrideHandle, noActivation]);
    };
}
// Sigh... - end

creme.bricks.BrickTable = creme.component.Component.sub({
    _init_: function(brick, options) {
        this._options = options || {};
        this._brick = brick;
        this._selections = new creme.bricks.BrickSelectionController({
            rows: 'tr',
            renderer: function(item) {
                item.ui.toggleClass('is-selected', item.selected);
                $('input[type="checkbox"]', item.ui).prop('checked', item.selected);
            }
        });
        this._events = new creme.component.EventHandler();
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

    selections: function() {
        return this._selections.state();
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    _updateSelectionState: function() {
        var state = this._selections.state();
        var count = state.selected().length;
        var total = state.selectables().length;

        $('th[data-selectable-selector-column] input[type="checkbox"]', this._element).prop('checked', count === total);
        this._brick.setSelectionState(count, total);
    },

    toggleSelection: function(index, state) {
        if (!this._brick.isLoading()) {
            this._selections.state().toggle(index, state);
        }
    },

    toggleSelectionAll: function(state) {
        if (!this._brick.isLoading()) {
            this._selections.state().toggleAll(state);
        }
    },

    toggleSort: function(field, ascending) {
        if (!this._brick.isLoading()) {
          // TODO: simpler param -> key == 'order_by' ??
          var params = {};
          var order = ascending ? '' : '-';
          params[this._brick.type_id() + '_order'] = order + field;

          this._brick.refresh(params);
        }
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('BrickTable is already bound');
        }

        var self = this;
        var brick = this._brick;
        var events = this._events;
        var selections = this._selections.bind($('tbody', element));

        this._element = element;

        element.on('change', '.row-selector-all', function(e) {
            self.toggleSelectionAll($(this).prop('checked'));
        });

        element.on('click', 'td[data-selectable-selector-column]', function(e) {
            var row = $(this).parents('tr').first();
            var index = parseInt(row.attr('data-row-index'));
            self.toggleSelection(index, !row.is('.is-selected'));
        });

        selections.state().on('change', function() {
            self._updateSelectionState();
        });

        element.on('click', '.brick-table-sortable', function(e) {
            var link = $(this);

            self.toggleSort(link.attr('data-sort-field'),
                            link.attr('data-sort-order') === 'desc');
        });

        $('table[-table-floating-header]', element).each(function() {
            var table = $(this);

            table.floatThead({
                scrollContainer: function(table) {
                    return table.closest('.brick-scrollable-container');
                }
            });
        });

        $('.brick-reorderable-items', element).sortable({
            placeholder: 'brick-reorderable-placeholder',
            handle:      '[data-reorderable-handle-column]',
            beforeStart: function (e, ui) {
                var widths = ui.item.find('td').map(function() {
                    return this.offsetWidth;
                }).get();

                var height = ui.item.height();

                ui.item.data('creme-layout-state', {
                    height: height,
                    widths: widths
                });
            },
            start: function (e, ui) {
                ui.item.appendTo(this).addClass('is-dragging');

                // As soon as jQuery UI starts the draggable interaction: the item is positioned absolutely, ruining the table layout.
                // So: restore the item to its original layout state

                var state = ui.item.data('creme-layout-state');

                ui.item.find('td').each(function (index) {
                    $(this).css('width', state.widths[index]);
                });

                // The placeholder suffers the same problem, it has no content so the table is relaid out and the columns widths are lost
                // So: make the placeholder size match the item's original size more closely
                ui.placeholder.find('td').each(function (index, element) {
                    // 1): pretend columns with the same widths are still in the table
                    $(this).css('width', state.widths[index]);
                });

                // 2: pretend the row still has the same height, in order to not offset the siblings
                ui.placeholder.height(state.height);
                events.trigger('row-drag-start', [e, ui.item]);
            },
            stop: function (e, ui) {
                ui.item.removeClass('is-dragging');
                ui.item.find('td').removeAttr('style');
                events.trigger('row-drag-stop', [ui.item], this);
            }
        });

        events.on('row-drag-stop', function(event, item) {
            var url  = item.attr('data-reorderable-item-url');
            var next = item.index() + 1;
            var prev = parseInt(item.attr('data-reorderable-item-order'));

            if (next !== prev) {
                brick.action('update', url, {}, {target: next})
                     .on({
                         done: function() { item.attr('data-reorderable-item-order', next); },
                         fail: function() { brick.refresh(); }
                      })
                     .start();
            }
        });

        return this;
    },

    unbind: function() {
        if (this.isBound() === false) {
            throw new Error('BrickTable is not bound');
        }

        $('table[-table-floating-header]', this._element).each(function() {
            $(this).floatThead('destroy');
        });

        $('.brick-reorderable-items', this._element).sortable('destroy');

        this._element = null;
        return this;
    }
});


/**
* Constructor for Dependencies.
* The dependencies are used to filter which Bricks have to be reloaded.
* They consist in a set of strings (NB: generally they are a string representation of server-side models)
* If a Brick (the 'source') is modified & must be reloaded, the other Brick which should be reloaded are
* Bricks which have a not-empty intersection between their dependencies & the source's dependencies
* (see intersect()).
* Notice that the dependency string '*' is special ; it's a wildcard. If you build a Dependencies instance
* with a wildcard in the list, this instance's intersect() will always return <true>.
*
* @param deps: - A sequence (i.e. indexing + 'length' attribute) of strings.
               - An instance of creme.bricks.Dependencies.
*/
creme.bricks.Dependencies = function(deps) {
    this._wildcard = false;
    this._deps = {};

    this.add(deps);
};

creme.bricks.Dependencies.prototype = {
    intersect: function(other) {
        if (this._wildcard || other._wildcard) {
            return true;
        }

        var this_deps = this._deps;
        var other_deps = other.keys();

        for (var i = 0; i < other_deps.length; i++) {
            if (this_deps[other_deps[i]]) {
                return true;
            }
        }

        return false;
    },

    add: function(deps) {
        deps = deps || [];

        if (this._wildcard) {
            return this;
        }

        if (creme.bricks.Dependencies.prototype.isPrototypeOf(deps)) {
            this._wildcard = deps._wildcard;

            if (deps._wildcard) {
                this._deps = {};
            } else {
                this._deps = $.extend(this._deps, deps._deps);
            }
        } else if (Array.isArray(deps)) {
            // TODO: use Set() when OK in all browsers
            //       https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set
            for (var i = 0; i < deps.length; i++) {
                var key = deps[i];

                if (key === '*') {
                    this._wildcard = true;
                    this._deps = {};
                    break;
                }

                this._deps[key] = true;
            }
        } else if (Object.isString(deps)) {
            return this.add([deps]);
        } else {
            throw new Error('Unable to add invalid dependency data', deps);
        }

        return this;
    },

    keys: function() {
        return Object.keys(this._deps);
    },

    isWildcard: function() {
        return this._wildcard;
    },

    isEmpty: function() {
        return !this._wildcard && (Object.keys(this._deps).length === 0);
    }
};

creme.bricks.Brick = creme.component.Component.sub({
    _init_: function(options) {
        var self = this;
        options = $.extend({
                        overlayDelay: 200,
                        deferredStateSaveDelay: 1000
                    }, options || {});

        this._options = options;
        this._events = new creme.component.EventHandler();

        this._state = {};
        this._dependencies = new creme.bricks.Dependencies();
        this._actionLinks = [];
        this._actionBuilders = new creme.bricks.BrickActionBuilders(this);

        if (options.deferredStateSaveDelay > 0) {
            this._deferredStateSave = _.debounce(this.saveState.bind(this),
                                                 options.deferredStateSaveDelay);
        } else {
            this._deferredStateSave = this.saveState.bind(this);
        }

        this._overlay = new creme.dialog.Overlay();
        this._pager = new creme.list.Pager()
                                      .on('refresh', function(event, page) {
                                           var data = {};
                                           data[self.type_id() + '_page'] = page;
                                           self.refresh(data);
                                       });
        this._table = new creme.bricks.BrickTable(this);
        this._menu = new creme.bricks.BrickMenu(this);
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
            this._element.trigger('brick-' + event, [this].concat(data || []));
        }

        this._events.trigger(event, data, this);
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    element: function() {
        return this._element;
    },

    _bindStateSaveURL: function() {
        var url = this._stateSaveURL = $('body').attr('data-brick-state-url') || '';

        if (!url) {
            console.warn('It seems there is no brick state URL in this page (see <body data-brick-state-url="..." > attribute)');
        }

        return url;
    },

    _bindDependencies: function(element) {
        var data = _.cleanJSON(element.attr('data-brick-deps')) || [];
        var deps = this._dependencies = new creme.bricks.Dependencies(data);

        return deps;
    },

    _bindActionLinks: function(element) {
        var self = this;

        this.trigger('setup-actions', [this._actionBuilders]);

        var links = this._actionLinks = $('[data-action]', element).map(function() {
            return self._initializeActionButton($(this));
        });

        return links;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw Error('brick component is already bound');
        }

        // brick is not bound so brick.trigger() doesn't send the 'brick-*' event to the element.
        this.trigger('before-bind', [element]);
        element.trigger('brick-before-bind', [this, element]);

        this._id = element.attr('id');
        this._element = element;
        this._defaultLoadingMessage = element.find('.brick-loading-indicator-title').html();
        this._state = {
            collapsed: element.is('.is-collapsed'),
            reduced:   element.is('.is-content-reduced')
        };

        this._bindStateSaveURL();
        this._bindDependencies(element);
        this._bindActionLinks(element);

        this._table.bind(element);
        this._pager.bind(element);
        this._overlay.bind($('.brick-content', element));
        this._menu.bind(element);

        this.trigger('bind', [element]);

        return this;
    },

    unbind: function() {
        if (this.isBound() === false) {
            throw Error('brick component is not bound');
        }

        var element = this._element;

        this.trigger('before-unbind', [element]);

        this._table.unbind();
        this._overlay.unbind().update(false);
        this._menu.unbind();

        this.closeMenu();

        this._element = undefined;
        this._state = {};
        this._actionLinks = [];
        this._defaultLoadingMessage = '';
        this._stateSaveURL = '';

        this.trigger('unbind', [element]);
        element.trigger('brick-unbind', [this, element]);

        return this;
    },

    id: function() {
        return this._id;
    },

    /* NB: corresponds to the Brick.id on server side */
    type_id: function() {
        return this._element.attr('data-brick-id');
    },

    title: function() {
        return $('.brick-header .brick-title', this._element).attr('title');
    },

    toggleMenu: function() {
        this._menu.toggle();
        return this;
    },

    closeMenu: function() {
        this._menu.close();
        return this;
    },

    menu: function() {
        return this._menu;
    },

    table: function() {
        return this._table;
    },

    setSelectionState: function(count, total) {
        count = Math.max(0, count || 0);
        total = Math.max(0, total || 0);

        if (this.isBound()) {
            var indicator = $('.brick-selection-indicator', this._element);
            var title = indicator.find('.brick-selection-title');
            var message = title.attr('data-title-format') || '';
            var plural = title.attr('data-plural-format');
            var has_selection = count > 0;

            if (pluralidx(count)) {
                message = plural || message;
            }

            indicator.toggleClass('has-selection', has_selection);
            title.text(has_selection && Object.isString(message) ? message.format(count, total) : '');
        }

        return this;
    },

    state: function() {
        return $.extend({}, this._state);
    },

    setState: function(state) {
        this._state = $.extend(this._state, state || {});
        this._renderState();
        this.trigger('state-update', [this._state]);
        this._deferredStateSave();
        return this;
    },

    toggleState: function(key) {
        var state = this.state();
        state[key] = !state[key];
        return this.setState(state);
    },

    saveState: function() {
        if (this.isBound()) {
            var state = this._state;

            if (!Object.isEmpty(this._stateSaveURL)) {
                creme.ajax.query(this._stateSaveURL, {action: 'post'}, {
                               brick_id:          this.type_id(),
                               is_open:           state.collapsed ? 0 : 1,
                               show_empty_fields: state.reduced ? 0 : 1
                           })
                           .start();
            }
        }

        return this;
    },

    _renderState: function() {
        var element = this._element;
        var state = this._state;

        element.toggleClass('is-collapsed', state.collapsed)
               .toggleClass('is-content-reduced', state.reduced);
    },

    _initializeActionButton: function(button) {
        var link = new creme.bricks.BrickActionLink(this).bind(button);

        // TODO : move this to BrickActionLink ?
        if (button.is('.is-async-action')) {
            var setLoadingState = this.setLoadingState.bind(this);

            link.on('action-link-start', function(event, url, options, data) {
                    setLoadingState(true, options.loading);
                 })
                .onComplete(function() {
                    setLoadingState(false);
                 });
        }

        return link;
    },

    _getActionBuilder: function(actiontype) {
        return this._actionBuilders.get(actiontype);
    },

    _buildAction: function(actiontype, url, options, data, event) {
        options = options || {};
        data = data || {};

        var builder = this._getActionBuilder(actiontype);

        if (Object.isFunc(builder)) {
            return builder(url, options, data, event);
        }
    },

    action: function(actiontype, url, options, data) {
        var self = this;

        if (!this.isBound()) {
            return new creme.component.Action(function() {
                this.cancel('brick is not bound', self);
            });
        }

        if (this.isLoading()) {
            return new creme.component.Action(function() {
                this.cancel('brick is in loading state', self);
            });
        }

        var action = this._buildAction(actiontype, url, options, data);

        if (Object.isNone(action)) {
            action = new creme.component.Action(function() {
                this.fail('no such action "' + actiontype + '"', self);
            });
        }

        return action;
    },

    getActionBuilders: function() {
        return this._actionBuilders;
    },

    _defaultDialogOptions: function(url, title) {
        return creme.bricks.defaultDialogOptions(url, title);
    },

    dependencies: function() {
        return this._dependencies;
    },

    isLoading: function() {
        return this.isBound() && this._element.is('.is-loading');
    },

    readOnly: function() {
        return this.isBound() && (this._element.attr('data-brick-readonly') === 'true');
    },

    reloadingInfo: function() {
        if (!this.isBound()) {
            return {};
        }

        var data = this._element.attr('data-brick-reloading-info') || '';

        if (data) {
            try {
                return JSON.parse(data);
            } catch (e) {
                console.warn('Invalid "data-brick-reloading-info" attribute:', e);
            }
        }

        return {};
    },

    setLoadingState: function(state, message) {
        if (this.isBound() && state !== this.isLoading()) {
            message = message || this._defaultLoadingMessage;
            var element = this._element;

            element.toggleClass('is-loading', state)
                   .find('.brick-loading-indicator-title').html(message);

            element.trigger(state ? 'brick-loading-start' : 'brick-loading-complete');
        }

        return this;
    },

    setDownloadStatus: function(percent) {
        if (this.isBound()) {
            var element = this._element;
            $('.brick-header', element).attr('data-loading-progress', percent);
            this.trigger('brick-loading-progress', [percent]);
        }

        return this;
    },

    refresh: function(uri_extra_params, listeners) {
        if (this.isBound()) {
            var reloader = new creme.bricks.BricksReloader(uri_extra_params);
            var action = reloader.sourceBrick(this)
                                 .action();

            action.on(listeners || {}).start();
        }

        return this;
    },

    redirect: function(url, option, data) {
        this._buildAction('redirect', url, option, data).start();
        return this;
    }
});

creme.bricks.replaceContent = function(block, content) {
    creme.widget.destroy(block);
    block.replaceWith(content);
    creme.widget.create(content);
};

creme.bricks.BricksReloader = function(uri_extra_params) {
    this._bricksContainer = null;  // DOM Node which contains the bricks to reload. Generally it's <body>, but it can be a <div> in an inner-popup for example.
    this._url = null;
    this._brickFilter = null;

    this.uri_extra_params = uri_extra_params;
};
creme.bricks.BricksReloader.prototype = {
    containerFromNode: function(node) {
        var container;

        if (node === undefined) {
            container = $('[data-bricks-reload-url]').first();
        } else {
            container = node.parents('[data-bricks-reload-url]').first();
        }

        if (container.length === 1) {
            var url = container.attr('data-bricks-reload-url');

            if (url) {
                this._bricksContainer = container;
                this._url = url;
            } else {
                console.warn('It seems that the brick reload URL is empty (see <body data-bricks-reload-url="..." > attribute)!');
            }
        } else {
            console.warn('It seems there is no brick reload URL in this page (see <body data-bricks-reload-url="..." > attribute)!');
        }

        return this;
    },

    dependencies: function(deps) {
        var deps_obj = new creme.bricks.Dependencies(deps);

        this._brickFilter = function(brick) {
            return deps_obj.intersect(brick.dependencies());
        };

        return this;
    },

    sourceBrick: function(brick) {
        this.containerFromNode(brick._element);
        var src_deps = brick.dependencies();
        var source_id = brick.id();

        if (Object.isEmpty(source_id)) {
            console.warn('It seems there the brick to reload has no "id".');
            this._brickFilter = null;
            return this;
        }

        if (Object.isEmpty(brick.type_id())) {
            console.warn('It seems there the brick to reload has no "data-brick-id".');
            this._brickFilter = null;
            return this;
        }

        if (brick.readOnly() || src_deps.isEmpty()) {
            this._brickFilter = function(other_brick) {
                return other_brick.id() === source_id;
            };
        } else {
            this._brickFilter = function(other_brick) {
                return other_brick.id() === source_id || src_deps.intersect(other_brick.dependencies());
            };
        }

        return this;
    },

    action: function() {
        var failAction = function(message) {
            return new creme.component.Action(function() {
                this.fail(message);
            });
        };

        var cancelAction = function(message) {
            return new creme.component.Action(function() {
                this.cancel(message);
            });
        };

        if (!this._bricksContainer) {
            this.containerFromNode();
        }

        if (this._brickFilter === null) {
            return failAction('Missing or invalid source brick');
        }

        var bricks = [];
        var extra_data = {}; // Additional information (per brick) sent to the server.
        var brickFilter = this._brickFilter;

        $('.brick.widget-ready', this._bricksContainer).each(function() {
            var brick = $(this).creme().widget().brick();
            if (brickFilter(brick) && !Object.isEmpty(brick.id()) && !Object.isEmpty(brick.type_id())) {
                bricks.push(brick);

                var brick_extra_data = brick.reloadingInfo();

                if (!Object.isEmpty(brick_extra_data)) {
                    extra_data[brick.type_id()] = brick_extra_data;
                }
            }
        });

        if (bricks.length === 0) {
            console.debug('No brick collected; so we avoid the reloading query');
            return cancelAction('No active brick collected. Avoid the reloading query.');
        }

        // TODO: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/Arrow_functions
        var data = $.extend({
//            brick_id:   bricks.map(function(brick) { return brick.id(); }),
            brick_id:   bricks.map(function(brick) { return brick.type_id(); }),
            extra_data: JSON.stringify(extra_data)
        }, this.uri_extra_params || false);

        var queryOptions = {
            backend: {
                sync: false,
                dataType: 'json'
            },
            progress: function(evt) {
                var percent = _.clamp(evt.loadedPercent || 100, 20, 100);

                bricks.forEach(function(brick) {
                    brick.setDownloadStatus(percent);
                });
            }
        };

        return creme.ajax.query(this._url, queryOptions, data)
                         .onStart(function() {
                              bricks.forEach(function(brick) {
                                  brick.setLoadingState(true);
                                  brick.setDownloadStatus(20);
                              });
                          })
                         .onComplete(function() {
                              bricks.forEach(function(brick) {
                                  brick.setLoadingState(false);
                                  brick._overlay.update(false);
                              });
                          })
                         .onDone(function(event, data) {
                              data.forEach(function(entry) {
                                  creme.bricks.replaceContent(
                                      $('[id="brick-' + entry[0] + '"]'),
                                      $((entry[1] || '').trim())
                                  );
                              });
                          });
    }
};


creme.bricks.BrickLauncher = creme.widget.declare('brick', {
    _create: function(element, options, cb, sync, args) {
        var brick = this._brick = new creme.bricks.Brick();

        brick.bind(element);

        element.addClass('widget-ready');
        brick.trigger('ready', [options]);
    },

    _destroy: function(element) {
        this._brick.unbind(element);
        creme.widget.shutdown(element);
    },

    brick: function(element) {
        return this._brick;
    }
});

}(jQuery));
