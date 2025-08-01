/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

/* global creme_media_url */

creme.widget.SelectorList = creme.widget.declare('ui-creme-selectorlist', {
    options: {
        cloneLast: undefined
    },

    _create: function(element, options, cb, sync) {
        var self = this;

        this._isCloneLast = creme.object.isTrue(options.cloneLast);
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        if (!this._enabled) {
            element.attr('disabled', '');
        }

        $('.selectorlist-add', element).on('click', function() {
            if (self._enabled) {
                self.appendLastSelector(element);
            }
        });

        $('.selectorlist-create', element).on('click', function() {
            if (self._enabled) {
                self.createSelector(element);
            }
        });

        var value = this.val(element);

        if (Object.isEmpty(value)) {
            this._update(element);
            value = this.val(element);
        } else {
            this._updateSelectors(element, value);
            this._update(element);
        }

        element.addClass('widget-ready');
        creme.object.invoke(cb, element);
    },

    lastSelector: function(element) {
        return $('ul.selectors > li.selector:last > ul > li > .ui-creme-widget', element);
    },

    selectorModel: function(element) {
        return $('.inner-selector-model > .ui-creme-widget', element);
    },

    selectors: function(element) {
        return $('ul.selectors > li.selector > ul > li > .ui-creme-widget', element);
    },

    selector: function(element, index) {
        return $('ul.selectors > li.selector:nth(' + (index || 0) + ') > ul > li > .ui-creme-widget', element);
    },

    removeSelectorAt: function(element, index) {
        return this.removeSelector(element, this.selector(element, index));
    },

    removeSelector: function(element, selector) {
        if (Object.isEmpty(selector)) {
            return;
        }

        selector.creme().destroy();
        selector.parents('li.selector').first().remove();
        this._update(element);

        return selector;
    },

    appendLastSelector: function(element) {
        var last = this.lastSelector(element);
        var value = this._isCloneLast && last.creme().isActive() ? last.creme().widget().val() : undefined;
        return this.appendSelector(element, value);
    },

    appendSelector: function(element, value, action) {
        action = action || 'select';

        var self = this;

        return this._buildSelector(element, value, {
            done: function(event, selector, value) {
                if (value === undefined) {
                    selector.triggerHandler('action', [action, {
                        cancel: function() {
                            self.removeSelector(element, selector);
                        }
                    }]);
                } else {
                    selector.creme().widget().val(value);
                }
            }
        });
    },

    appendSelectors: function(element, values, action) {
        var self = this;

        return values.map(function(value) {
            return self.appendSelector(element, value, action);
        });
    },

    createSelector: function(element, value) {
        return this.appendSelector(element, value, 'create');
    },

    _buildSelector: function(element, value, listeners) {
        var self = this;
        var selector_model = this.selectorModel(element).clone();

        if (Object.isEmpty(selector_model)) {
            creme.object.invoke(listeners.fail, 'fail');
            return;
        }

        var selector_item = $('<li>').addClass('selector');
        var selector_layout = $('<ul>').addClass('ui-layout hbox').css('display', 'block').appendTo(selector_item);

        var img_title = gettext('Delete');
        var delete_button = $('<img/>').attr('src', creme_media_url('images/delete_22.png'))
                                       .attr('alt', img_title)
                                       .attr('title', img_title)
                                       .attr('style', 'vertical-align:middle;')
                                       .addClass('delete')
                                       .on('click', function() {
                                            if (self._enabled) {
                                                self.removeSelector(element, $('> ul > li > .ui-creme-widget', selector_item));
                                            }
                                        });

        selector_layout.append($('<li>').append(selector_model));
        selector_layout.append($('<li>').append(delete_button));

        $('ul.selectors', element).append(selector_item);

        selector_model.on('change', function() {
            self._update(element);
        });

        var selector = creme.widget.create(selector_model, {disabled: !this._enabled}, function() {
            selector_model.on('change-multiple', function(e, data) {
                self.appendSelectors(element, data.slice(1));
            });

            creme.object.invoke(listeners.done, 'done', selector_model, value);
        }, true);

        if (selector === undefined) {
            selector_item.remove();
            creme.object.invoke(listeners.fail, 'fail');
        }

        return selector;
    },

    _update: function(element) {
        var values = creme.widget.values_list(this.selectors(element));
        creme.widget.input(element).val('[' + values.join(',') + ']');
    },

    _updateSelectors: function(element, data) {
        var self = this;
        var values = creme.widget.cleanval(data, []);

        if (typeof values !== 'object') {
            return;
        }

        $('ul.selectors', element).empty();

        values.forEach(function(value) {
            self.appendSelector(element, value);
        });
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.widget.input(element).val();
        }

        this._updateSelectors(element, value);
        this._update(element);
    }
});

}(jQuery));
