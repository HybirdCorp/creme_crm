/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2022 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

creme.form = creme.form || {};

function djangoLocalisation(options) {
    return {
        errorLoading: function () {
            return options.errorLoadingMsg || gettext('The results could not be loaded.');
        },
        inputTooLong: function (args) {
            var overChars = args.input.length - args.maximum;

            if (options.inputTooLongMsg) {
                return options.inputTooLongMsg(args);
            } else {
                return ngettext('Please delete %d character', 'Please delete %d characters', overChars).format(overChars);
            }
        },
        inputTooShort: function (args) {
            var remainingChars = args.minimum - args.input.length;

            if (options.inputTooShortMsg) {
                return options.inputTooShortMsg(args);
            } else {
                return ngettext('Please enter %d or more characters', 'Please enter %d or more characters', remainingChars).format(remainingChars);
            }
        },
        loadingMore: function () {
            return options.loadingMoreMsg || gettext('Loading more results…');
        },
        maximumSelected: function (args) {
            if (options.maximumSelectedMsg) {
                return options.maximumSelectedMsg(args);
            } else {
                return ngettext('You can only select %d item', 'You can only select %d items', args.maximum).format(args.maximum);
            }
        },
        noResults: function () {
            return options.noResultsMsg || gettext('No result');
        },
        searching: function () {
            return options.searchingMsg || gettext('Searching…');
        },
        removeAllItems: function () {
            return options.removeAllItemsMsg || gettext('Remove all items');
        },
        removeItem: function () {
            return options.removeItemMsg || gettext('Remove item');
        },
        search: function() {
            return options.searchMsg || gettext('Search');
        }
    };
}

creme.form.Select2 = creme.component.Component.sub({
    _init_: function(options) {
        this._options = $.extend({
            multiple: false,
            sortable: false,
            clearable: false,
            placeholder: undefined, // gettext("Select one option"),
            placeholderMultiple: undefined // gettext("Select some options")
        }, options || {});
    },

    isBound: function() {
        return !Object.isNone(this._instance);
    },

    options: function() {
        return $.extend({}, this._options);
    },

    localisation: function(options) {
        return djangoLocalisation($.extend({}, this._options, options));
    },

    bind: function(element) {
        Assert.not(this.isBound(), 'Select2 instance is already active');

        var options = this._options;
        var placeholder = options.multiple ? options.placeholderMultiple : options.placeholder;

        element.toggleAttr('data-allow-clear', options.clearable, 'true');
        element.attr('data-placeholder', placeholder);

        var instance = element.select2({
            language: this.localisation(),
            templateSelection: function(data) {
                return data.text;
            }
        });

        if (options.multiple && options.sortable) {
            this._activateSort(element);
        }

        this._instance = instance;
        this.element = element;
        return this;
    },

    unbind: function() {
        if (this.isBound()) {
            if (this._sortable && this._sortable.length > 0) {
                this._sortable.sortable('destroy');
                this._sortable = null;
            }

            this.element.select2('destroy');
            this._instance = null;
            this.element = null;
        }

        return this;
    },

    refresh: function() {
        var data = creme.model.ChoiceGroupRenderer.parse(this.element);

        var selectData = (data || []).filter(function(item) {
            return item.visible;
        }).map(function(item) {
            return {
                id: item.value,
                text: item.label,
                disabled: item.disabled,
                selected: item.selected
            };
        });

        this.element.select2({
            data: selectData
        });

        this.element.trigger('change.select2');
        return this;
    },

    _activateSort: function(element) {
        var choices = element.next('.select2-container').parent();

        this._sortable = choices.sortable({
            items: '.select2-selection__choice',
            // tolerance: 'pointer',
            opacity: 0.5,
            revert:  200,
            delay:   200,
            stop: function() {
                jQuery.fn.select2.amd.require(['select2/utils'], function(Utils) {
                    var sorted = $(choices).find('.select2-selection__choice').map(function() {
                        return Utils.GetData(this, 'data');
                    }).get().map(function(d) {
                        return d.id;
                    });

                    element.val(sorted);
                });
            }
        });
    }
});

}(jQuery));
