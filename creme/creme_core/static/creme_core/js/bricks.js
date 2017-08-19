/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2017  Hybird

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

(function($) {"use strict";

creme.bricks = creme.bricks || {};

creme.bricks.dialogCenterPosition = function(dialog) {
    var outer_height = $('.header-menu').outerHeight()

//    if (dialog.dialog().parents('.ui-dialog:first').position().top < $('.header-menu').outerHeight()) {
    if (dialog.dialog().parents('.ui-dialog:first').position().top < outer_height) {
        dialog.position({
            my: 'center top',
//            at: 'center top+' + (2 * $('.header-menu').outerHeight()),
            at: 'center top+' + (2 * outer_height),
            of: window
        });
    }
};

creme.bricks.dialogActionButtons = function(dialog) {
    var buttons = $('a.brick-dialog-action', dialog.content()).map(function(index) {
        var link = $(this);
        var label = link.contents().map(function(){return this.nodeType == 3 ? this.data : '';}).get().join('');

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

creme.bricks.DialogAction = creme.dialog.DialogAction.sub({
    _init_: function(options, listeners) {
        this._super_(creme.dialog.DialogAction, '_init_', options);
        this._listeners = listeners || {};
    },

    _openPopup: function(options) {
        var self = this;
        var options = $.extend(this.options(), options || {});

        this._dialog = new creme.dialog.Dialog(options).onClose(this._onClose.bind(this))
                                                       .on('frame-activated', function() {
                                                            creme.bricks.dialogActionButtons(this);
                                                            creme.bricks.dialogCenterPosition(this);
                                                        })
                                                       .on(this._listeners)
                                                       .open();
    }
});

creme.bricks.FormDialogAction = creme.dialog.FormDialogAction.sub({
    _init_: function(options, listeners) {
        this._super_(creme.dialog.FormDialogAction, '_init_', options);
        this._listeners = listeners || {};
    },

    _openPopup: function(options) {
        var self = this;
        var options = $.extend(this.options(), options || {});

        this._dialog = new creme.dialog.FormDialog(options).onFormSuccess(function(event, data) {self._onSubmit(data);})
                                                           .onClose(function() {self.cancel();})
                                                           .on('frame-update', function() {creme.bricks.dialogCenterPosition(this);})
                                                           .on(this._listeners)
                                                           .open();
    }
});

creme.bricks.BrickPager = creme.component.Component.sub({
    _init_: function(brick, options) {
        this._brick = brick;
        this._options = options || {};
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

    canvas2d: function() {
        if (Object.isNone(this._canvas2d)) {
            this._canvas2d = document.createElement('canvas').getContext('2d');
        }

        return this._canvas2d;
    },

    _getPage: function(input) {
        var page = parseInt(input.val());
        var max = parseInt(input.attr('max'));

        if (isNaN(page) || page < 1 || (!isNaN(max) && page > max)) {
            return null;
        }

        return page;
    },

    _goToChosenPage: function(input) {
        var page = this._getPage(input);

        if (page !== null) {
            this.refresh(page);
        }
    },

    _resizeChooseInput: function(input) {
        var canvas2d = this.canvas2d();
        var value = Object.isNone(input.val()) ? '' : input.val();

        canvas2d.font = input.css('font-size') + ' ' + input.css('font-family');
        var width = canvas2d.measureText(value).width;

        input.css('width', width + 25);
    },

    _initializeChooseLink: function(choose) {
        var self = this;
        var input = $('input:first', choose);

        choose.click(function(e) {
                   e.stopPropagation();
                   choose.addClass('active');

                   input.val(input.attr('data-initial-value'));
                   self._resizeChooseInput(input);

                   input.toggleClass('invalid-page', Object.isNone(self._getPage(input)))
                        .select()
                        .focus();
                });

        input.bind('propertychange input change paste', $.debounce(function() {
                  input.toggleClass('invalid-page', Object.isNone(self._getPage(input)));
             }, 50))
             .bind('propertychange input change paste keydown', $.debounce(function() {
                  self._resizeChooseInput(input);
             }, 50))
             .bind('keyup', function(e) {
                 if (e.keyCode === 13) {
                     e.preventDefault();
                     self._goToChosenPage(input);
                 } else if (e.keyCode === 27) {
                     e.preventDefault();
                     input.focusout();
                 }
             })
             .bind('focusout', function() {
                 choose.removeClass('active');
             });
    },

    refresh: function(page) {
        // TODO: simpler param -> key == 'page' ??
        var extra_params = {};
        extra_params[this._brick._id + '_page'] = page;

        this._events.trigger('refresh', extra_params);
    },

    bind: function(element) {
        var self = this;

        $('.brick-pagination > a', element).each(function() {
            $(this).click(function(e) {
                        e.preventDefault();
                        self.refresh($(this).attr('data-page'));
                    });
        });

        $('.brick-pagination .brick-pagination-choose', element).each(function() {
            self._initializeChooseLink($(this));
        });
    }
});

creme.bricks.BrickMenu = creme.dialogs.Popover.sub({
    _init_: function(brick, options) {
        var options = $.extend({
            content: '',
            direction: 'right'
        }, options || {});

        this._super_(creme.dialogs.Popover, '_init_', options);
        this._brick = brick;

        var self = this;
        var content = this._menuContent();
        var is_disabled = this._disabled = $('a', content).length < 1;

        $('.brick-header-menu', this._brick._element).toggleClass('is-disabled', is_disabled)
                                                     .click(function(e) {
                                                          self.toggle(e);
                                                      });

        var dialog = this._dialog = new creme.dialogs.Popover(options);
        dialog.fill(content);
    },

    _menuContent: function() {
        return $('.brick-menu-buttons', this._brick._element);
    },

    toggle: function(e) {
        if (!this._brick.isLoading() && !this._disabled) {
            this._dialog.toggle(e.target);
        }
    },

    close: function() {
        this._dialog.close();
    }
});

creme.bricks.BrickActionLink = creme.action.ActionLink.sub({
    _init_: function(brick, options) {
        this._super_(creme.action.ActionLink, '_init_', options);
        this._brick = brick;
        this.builders(this._brickActionBuilder.bind(this));
    },

    _brickActionBuilder: function(actiontype) {
        var brick = this._brick;
        var builder = brick['_action_' + actiontype];

        if (Object.isFunc(builder)) {
            builder = builder.bind(brick);

            return function(url, options, data, e) {
                if (!brick.isLoading()) {
                    brick.closeMenu();
                    return builder(url, options, data, e);
                }
            }
        }
    }
})

creme.bricks.BrickSelectionController = creme.component.Component.sub({
    _init_: function(options) {
        this._options = $.extend({
            rows:     'tr',
            renderer: this._defaultItemStateRenderer,
            parser:   this._defaultItemStateParser,
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

//Sigh...
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

    bind: function(element) {
        var brick = this._brick;
        var events = this._events;
        var selections = this._selections.bind($('tbody', element));

        $('.row-selector-all', element).click(function(e) {
            if (!brick.isLoading()) {
                selections.state().toggleAll($(this).prop('checked'));
            }
        });

        $('td[data-selectable-selector-column]', element).click(function(e) {
            if (!brick.isLoading()) {
                var row = $(this).parents('tr:first');
                selections.state().toggle(row.attr('data-row-index'), !row.is('.is-selected'));
            }
        });

        selections.state().on('change', function() {
            var count = selections.state().selected().length;
            var total = selections.state().selectables().length;

            $('th[data-selectable-selector-column] input[type="checkbox"]', element).prop('checked', count === total);
            brick.setSelectionState(count, total);
        });

        $('.brick-table-sortable', element).click(function(e) {
            if (!brick.isLoading()) {
//                brick.refresh($(this).attr('data-column-sort-url'));
                var link = $(this);

                // TODO: simpler param -> key == 'order_by' ??
                var extra_params = {};
                var order = link.attr('data-sort-order') === 'desc' ? '': '-';
                extra_params[brick._id + '_order'] =  order + link.attr('data-sort-field');

                brick.refresh(extra_params);
            }
        });

        $('table[-table-floating-header]', element).each(function() {
            var table = $(this);

            table.floatThead({
                scrollContainer: function(table) {
                    return table.closest('.brick-scrollable-container');
                }
            });
        });

        $('.brick-reorderable-items', element).sortable ({
            placeholder: 'brick-reorderable-placeholder',
            handle:      '[data-reorderable-handle-column]',
            beforeStart: function (e, ui) {
                var widths = ui.item.find('td').map (function() {
                    return this.offsetWidth;
                }).get();

                var height = ui.item.height();

                ui.item.data ('creme-layout-state', {
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
                    $(this).css('width', state.widths [index]);
                });

                // The placeholder suffers the same problem, it has no content so the table is relaid out and the columns widths are lost
                // So: make the placeholder size match the item's original size more closely
                ui.placeholder.find('td').each (function (index, element) {
                    // 1): pretend columns with the same widths are still in the table
                    $(this).css('width', state.widths [index]);
                });

                // 2: pretend the row still has the same height, in order to not offset the siblings
                ui.placeholder.height (state.height);
//                ui.placeholder[0].innerHTML = '<td colspan="50">' + gettext('Drop here to reorder') + '</td>';
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
                brick.doAction('update', url, {}, {target: next}, {
                    done: function() {
                        item.attr('data-reorderable-item-order', next);
                    },
                    fail: function() {
                        brick.refresh();
                    }
                });
            }
        });
    },

    unbind: function(element) {
        $('table[-table-floating-header]', element).each(function() {
            $(this).floatThead('destroy');
        });

        $('.brick-reorderable-items', element).sortable ('destroy');
    }
});


/**
* Constructor for Dependencies.
* The dependencies are used to filter which Bricks have to be reloaded.
* They consist in a set of strings (NB: generally they are a string representation of server-side models)
* If a Brick (the 'source') is modified & must be reloaded, the other Brick which should be reloaded are
* Bricks which have a not-empty intersection betwen their dependencies & the source's dependencies
* (see intersect()).
* Notice that the dependency string '*' is special ; it's a wildcard. If you build a Dependencies instance
* with a wildcard in the list, this instance's intersect() will always return <true>.
*
* @param deps: - A sequence (ie: indexing + 'length' attribute) of strings.
               - An instance of creme.bricks.Dependencies.
*/
creme.bricks.Dependencies = function(deps) {
    this._wildcard = false;
    this._deps = null;

    // TODO: use Set() when OK in all browsers
    //       https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set
    var deps_set = {};

    if (creme.bricks.Dependencies.prototype.isPrototypeOf(deps)) {
        this._wildcard = deps._wildcard;
        jQuery.extend(deps_set, deps._deps);
    } else {
        for (var i = 0; i < deps.length; i++) {
            var dep = deps[i];

            if (dep === '*') {
                this._wildcard = true;
                return;
            }

            deps_set[dep] = true;
        }
    }

    this._deps = deps_set;
};
creme.bricks.Dependencies.prototype = {
    intersect: function(other_deps_obj) {
        if (this._wildcard || other_deps_obj._wildcard) {
            return true;
        }

        var this_deps = this._deps;
        var other_deps = Object.keys(other_deps_obj._deps);

        for (var i = 0; i < other_deps.length; i++) {
            if (this_deps[other_deps[i]]) {
                return true;
            }
        }

        return false;
    },

    add: function(other_deps_obj) {
        if (!this._wildcard) {
            if (other_deps_obj._wildcard) {
                this._wildcard = true;
                this._deps = null;
            } else {
                var this_deps = this._deps;
                var other_deps = Object.keys(other_deps_obj._deps);

                for (var i = 0; i < other_deps.length; i++) {
                    this_deps[other_deps[i]] = true;
                }
            }
        }

        return this;
    },

    is_empty: function() {
        return !this._wildcard && (Object.keys(this._deps).length === 0);
    }
};

creme.bricks.Brick = creme.component.Component.sub({
    _init_: function(options) {
        var self = this;
        var options = $.extend({
                            overlayDelay: 200,
                            deferredStateSaveDelay: 1000
                        }, options || {});

        this._options = options;
        this._events = new creme.component.EventHandler();

        this._state = {};
        this._deferredStateSave = $.debounce(this.saveState.bind(this), options.deferredStateSaveDelay);

        this._overlay = new creme.dialog.Overlay();
        this._pager = new creme.bricks.BrickPager(this)
                                      .on('refresh', function(event, url) {
                                            self.refresh(url);
                                      });
        this._table = new creme.bricks.BrickTable(this);
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
    },

    bind: function(element) {
        if (Object.isNone(this._element) === false) {
            throw 'brick component is already bound !';
        }

        this._id = element.attr('id');

        this._stateSaveURL = $('body').attr('data-brick-state-url');
        if (!this._stateSaveURL) {
            this._stateSaveURL = '';
            console.warn('It seems there is no brick state URL in this page (see <body data-brick-state-url="..." > attribute)!');
        }

        this._defaultLoadingMessage = element.find('.brick-loading-indicator-title').html();
        this._element = element;

        var self = this;

        $('[data-action]', element).each(function() {
            self._initializeActionButton($(this));
        });

        this._state = {
            collapsed: element.is('.is-collapsed'),
            reduced:   element.is('.is-content-reduced')
        }

        this._table.bind(element);
        this._pager.bind(element);
        this._overlay.bind($('.brick-content', element));
        this._menu = new creme.bricks.BrickMenu(this);
    },

    unbind: function(element) {
        if (Object.isNone(this._element)) {
            throw 'brick component is not bound !';
        }

        this._table.unbind(element);
        this._overlay.unbind(element).update(false);
        this.closeMenu();
    },

    title: function() {
        return $('.brick-header .brick-title', this._element).attr('title');
    },

    toggleMenu: function() {
        this._menu.toggle();
    },

    closeMenu: function() {
        return this._menu.close();
    },

    table: function() {
        return this._table;
    },

    setSelectionState: function(count, total) {
        var indicator = $('.brick-selection-indicator', this._element);
        var title = indicator.find('.brick-selection-title');

        indicator.toggleClass('has-selection', count > 0);
        title.text(title.attr(pluralidx(count) ? 'data-plural-format' : 'data-title-format').format(count));
    },

    state: function() {
        return $.extend({}, this._state);
    },

    setState: function(state) {
        this._state = $.extend(this._state, state || {});
        this._renderState();
        this._events.trigger('state-update', [this._state], this);
        this._deferredStateSave();
        return this;
    },

    toggleState: function(key) {
        var state = this.state();
        state[key] = !state[key];
        return this.setState(state);
    },

    saveState: function() {
        var state = this._state;

        creme.ajax.query(this._stateSaveURL, {action: 'post'}, {
                       id:                this._id,
                       is_open:           state.collapsed ? 0 : 1,
                       show_empty_fields: state.reduced ? 0 : 1,
                   })
                   .start();
    },

    _renderState: function() {
        var element = this._element;
        var state = this._state;

        element.toggleClass('is-collapsed', state.collapsed)
               .toggleClass('is-content-reduced', state.reduced);
    },

    _initializeActionButton: function(button) {
        var self = this;
        var link = new creme.bricks.BrickActionLink(this).bind(button);

        if (button.is('.is-async-action')) {
            var setLoadingState = this.setLoadingState.bind(this);

            link.on('action-link-start', function(event, url, options, data) {
                    setLoadingState(true, options.loading);
                 })
                .on('action-link-complete', function() {setLoadingState(false);});
        }

        return link;
    },

    doAction: function(action, url, options, data, listeners) {
        var listeners = listeners || {};
        var actiontype = action.replace(/\-/g, '_').toLowerCase();
        var builder = this['_action_' + actiontype];

        if (Object.isFunc(builder) && !this.isLoading()) {
            builder = builder.bind(this);
            builder(url, options, data).on(listeners).start();
        }
    },

    _toggleStateAction: function(key, e, active_label, inactive_label) {
        var toggle = this.toggleState.bind(this, key);
        return new creme.component.Action(function() {
            var state = toggle().state()[key];
            var link = $(e.target).parents('[data-action]:first');
            link.find('.brick-action-title').text(state ? inactive_label : active_label);
            this.done();
        });
    },

    _action_collapse: function(url, options, data, e) {
        return this._toggleStateAction('collapsed', e, data.inlabel, data.outlabel);
    },

    _action_reduce_content: function(url, options, data, e) {
        return this._toggleStateAction('reduced', e, data.inlabel, data.outlabel);
    },

    _action_form: function(url, options, data) {
        var options = $.extend(this._defaultDialogOptions(url), options || {});

        return new creme.bricks.FormDialogAction(options);
    },

    _action_form_refresh: function(url, options, data) {
        var self = this;
        return this._action_form(url, options, data).onDone(function() {self.refresh();});
    },

    _action_add: function(url, options, data) {
/*
        var self = this;
        return this._action_form(url, options, data).onDone(function() {self.refresh();});
*/
        return this._action_form_refresh(url, options, data);
    },

    _action_edit: function(url, options, data) {
/*
        var self = this;
        return this._action_form(url, options, data).onDone(function() {self.refresh();});
*/
        return this._action_form_refresh(url, options, data);
    },

    _action_link: function(url, options, data) {
/*
        var self = this;
        return this._action_form(url, options, data).onDone(function() {self.refresh();});
*/
        return this._action_form_refresh(url, options, data);
    },

    /* TODO: factorise with _action_update() */
    _action_delete: function(url, options, data) {
        var self = this;
        var options = $.extend({action: 'post'}, options || {});
        var action = creme.utils.confirmAjaxQuery(url, options, data)
                                .onDone(function() {self.refresh();});

        return action;
    },

    _action_update: function(url, options, data) {
        var self = this;
        var options = $.extend({action: 'post', reloadBrick: true}, options || {});
        var action = options.confirm ? creme.utils.confirmAjaxQuery(url, options, data) :
                                       creme.utils.ajaxQuery(url, options, data);

        return action.onDone(function() {self.refresh();});
    },

    /* TODO: factorise with _action_update() */
    _action_update_redirect: function(url, options, data) {
        var options = $.extend({action: 'post'}, options || {});
        var action = options.confirm ? creme.utils.confirmAjaxQuery(url, options, data) :
                                       creme.utils.ajaxQuery(url, options, data);

        return action.onDone(function(event, data, xhr) {
            creme.utils.goTo(data);
        });
    },

    _action_add_relationships: function(url, options, data) {
        // NOTE: the options parameter here is never used/filled at the moment, options are actually passed as __name=value
        //       and available in the data parameter. The only other option in creme.relations.addRelationTo being __mutiple.
        return creme.relations.addRelationTo(data.subject_id, data.rtype_id, data.ctype_id, {multiple: data.multiple});
    },

    _defaultDialogOptions: function(url, title) {
        var width = $(window).innerWidth();

        return {
            resizable: true,
            draggable: true,
            width: width * 0.8,
            maxWidth: width,
            url: url,
            title: title,
            compatible: true
        };
    },

    _action_view: function(url, options, data) {
        var options = $.extend(this._defaultDialogOptions(url, data.title), options || {});

        return new creme.bricks.DialogAction(options);
    },

    _action_refresh: function(uri_extra_params) {
        return new creme.bricks.BricksReloader(uri_extra_params).sourceBrick(this).action();
    },

    _action_redirect: function(url, options, data) {
        var context = {
            location: window.location.href.replace(/.*?:\/\/[^\/]*/g, '') // remove 'http://host.com'
        };

        return new creme.component.Action(function() {
            creme.utils.goTo(creme.utils.templatize(url, context).render());
        })
    },

    dependencies: function() {
        var deps_list = [];
        var deps_str = this._element.attr('data-brick-deps');

        if (deps_str !== undefined) {
            try {
                deps_list = JSON.parse(deps_str);
            } catch (e) {
                console.warn('Invalid "data-brick-deps" attribute:', e);
            }
        }

        return new creme.bricks.Dependencies(deps_list);
    },

    isLoading: function() {
        return this._element.is('.is-loading');
    },

    readOnly: function() {
        var read_only = false;
        var read_only_str = this._element.attr('data-brick-readonly');

        if (read_only_str !== undefined) {
            try {
                read_only = Boolean(JSON.parse(read_only_str));
            } catch (e) {
                console.warn('Invalid "data-brick-readonly" attribute:', e);
            }
        }

        return read_only;
    },

    reloadingInfo: function() {
        var info = null;
        var info_str = this._element.attr('data-brick-reloading-info');

        if (info_str !== undefined) {
            try {
                info = JSON.parse(info_str);
            } catch (e) {
                console.warn('Invalid "data-brick-reloading-info" attribute:', e);
            }
        }

        return info;
    },

    setLoadingState: function(state, message) {
        if (state != this.isLoading()) {
            var message = message || this._defaultLoadingMessage;
            var element = this._element;

            element.toggleClass('is-loading', state)
                   .find('.brick-loading-indicator-title').html(message)
                   .trigger(state ? 'brick-loading-start' : 'brick-loading-complete');
        }
    },

    setDownloadStatus: function(percent) {
        var element = this._element;
        $('.brick-header', element).attr('data-loading-progress', percent);
        element.trigger('brick-loading-progress', [percent]);
    },

    refresh: function(uri_extra_params) {
        this._action_refresh(uri_extra_params).start();
    },

    redirect: function(url, option, data) {
        this._action_redirect(url, option, data).start();
    }
});

creme.bricks.replaceContent = function(block, content) {
    if (block.is('.brick')) {
        creme.widget.destroy(block);
        block.replaceWith(content);
        creme.widget.create(content);
    } else {
        // TODO: remove in 1.8
        block.replaceWith(content);
        creme.blocks.initialize(content);
    }
};

creme.bricks.BricksReloader = function(uri_extra_params) {
    this._bricksContainer = null;  // DOM Node which contains the bricks to reload. Generally it's <body>, but it can be a <div> in an inner-popup for example.
    this._url = null;
    this._brickFilter = null;

    this.uri_extra_params = uri_extra_params;
};
creme.bricks.BricksReloader.prototype = {
    containerFromNode: function(node) {
        var container = (node === undefined ? $('[data-bricks-reload-url]').first():
                                              node.parents('[data-bricks-reload-url]').first()
                        );

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

        if (brick.readOnly() || src_deps.is_empty()) {
            var source_id = brick._id;

            this._brickFilter = function(other_brick) {
                return other_brick._id === source_id;
            };
        } else {
            this._brickFilter = function(other_brick) {
                return src_deps.intersect(other_brick.dependencies());
            };
        }

        return this;
    },

    action: function() {
        if (!this._bricksContainer) {
            this.containerFromNode();
        }

        if (!this._url || this._brickFilter === null) {
            return;
        }

        var bricks = [];
        var extra_data = {}; // Additional information (per brick) sent to the server.
        var brickFilter = this._brickFilter;

        $('.brick', this._bricksContainer).each(function() {
            var brick = $(this).creme().widget().brick();

            if (brickFilter(brick)) {
                bricks.push(brick);

                var brick_extra_data = brick.reloadingInfo();
                if (brick_extra_data) {
                    extra_data[brick._id] = brick_extra_data;  // TODO: getter for _id ?
                }
            }
        });

        if (bricks.length === 0) {
            console.debug('No brick collected ; so we avoid the reloading query');

            return new creme.component.Action();
        }

        // TODO: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/Arrow_functions
        var uri = this._url + '&' + $.param({brick_id: bricks.map(function(brick) {return brick._id;}),
                                             extra_data: $.toJSON(extra_data)
                                            });

        if (this.uri_extra_params) {
            uri += '&' + $.param(this.uri_extra_params);
        }

        var queryOptions = {
            backend: {
                sync: false,
                dataType: 'json',
            },
            onDownloadProgress: function(evt) {
                var percent = 100;

                if (evt.lengthComputable && event.total > 0) {
                    percent = Math.trunc(Math.max((evt.loaded / evt.total) * 100, 0) / 20) * 20;
                }

                bricks.forEach(function(brick) {brick.setDownloadStatus(percent);});
            }
        };

        bricks.forEach(function(brick) {
            // TODO: Brick method ?
            brick._overlay.content('')
                 .update(true, 'wait', brick._options.overlayDelay);
        });

        return creme.ajax.query(uri, queryOptions)
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
                                  creme.bricks.replaceContent($('[id="' + entry[0] + '"]'), $($.trim(entry[1])));
                              });
                          });
    }
};


creme.bricks.BrickLauncher = creme.widget.declare('brick', {
    _create: function(element, options, cb, sync, args) {
        var brick = this._brick = new creme.bricks.Brick();

        element.trigger('brick-before-bind', [brick, options, element]);
        brick.bind(element);

        element.addClass('widget-ready');
        element.trigger('brick-ready', [brick, options]);
    },

    _destroy: function(element) {
        this._brick.unbind(element);
        creme.widget.shutdown(element);
    },

    brick: function(element) {
        return this._brick;
    },
});

}(jQuery));
