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

/*
 * Displays a <select> as a link with the selected option as label.
 *
 * @param {String} dropdownMode | data-dropdown-mode
 *    auto    : Use 'toggle' mode if 2 options and 'popover' for more
 *    popover : Displays a popover to select the next value
 *    toggle  : Go to the next value without showing a popover.
 *
 * @param {String} dropdownAlt | data-dropdown-alt
 *    Tooltip of the link
 */
creme.form.DropDown = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            mode: element.data('dropdownMode') || 'auto',
            title: element.data('dropdownAlt') || ''
        }, options || {});

        this._element = element;
        this._element.addClass('ui-dropdown-hidden');
        this._element.on('change', this._onChange.bind(this));

        this.mode(options.mode);

        this._selection = $('<a class="ui-dropdown-selection" title="${title}">${label}</a>'.template({
            title: options.title,
            label: this._optionLabel(this._element.val())
        })).insertAfter(element);

        this._selection.on('click', function(e) {
            e.preventDefault();
            this.select();
        }.bind(this));
    },

    destroy: function() {
        this._element.off('change', this._onChange.bind(this));
        this._element.removeClass('ui-dropdown-hidden');
        delete this._popover;
    },

    _onOpen: function() {
        this._popover.content().on('click', '.popover-list-item', function(e) {
            e.preventDefault();
            this.val($(e.target).data('value'));
            this._popover.close();
        }.bind(this));
    },

    _onClose: function() {
        this._popover.content().off('click', '.popover-list-item');
    },

    _onChange: function() {
        var label = this._optionLabel(this._element.val());
        this._selection.text(label);
    },

    _popoverHtml: function() {
        var choices = creme.model.ChoiceGroupRenderer.parse(this._element);

        return choices.filter(function(choice) {
            return !choice.selected;
        }).map(function(choice) {
            return '<a class="popover-list-item" title="${label}" alt="${label}" data-value="${value}">${label}</a>'.template(choice);
        }).join('');
    },

    _openPopover: function() {
        if (Object.isNone(this._popover)) {
            this._popover = new creme.dialog.Popover();
            this._popover.on({
                closed: this._onClose.bind(this),
                opened: this._onOpen.bind(this)
            });
        }

        this._popover.fill(this._popoverHtml());
        this._popover.open(this._selection);
    },

    _optionLabel: function(value) {
        return this._element.find('option').filter(function() {
            return $(this).attr('value') === value;
        }).map(function() {
            return $(this).text();
        }).get(0);
    },

    _optionValueAfter: function(value) {
        var next = this._element.find('option').filter(function() {
            return $(this).attr('value') === value;
        }).next();

        return next.length > 0 ? next.attr('value') : this._element.find('option:first').attr('value');
    },

    element: function() {
        return this._element;
    },

    mode: function(mode) {
        return Object.property(this, '_mode', mode);
    },

    val: function(value) {
        if (value === undefined) {
            return this._element.val();
        }

        this._element.val(value).trigger('change');
    },

    next: function() {
        this.val(this._optionValueAfter(this.val()));
    },

    select: function() {
        switch (this.mode()) {
            case 'popover':
                this._openPopover();
                break;
            case 'toggle':
                this.next();
                break;
            default:
                if (this._element.find('option').length > 2) {
                    this._openPopover();
                } else {
                    this.next();
                }
        }
    }
});

creme.utils.newJQueryPlugin({
    name: 'dropdown',
    create: function(options) {
        return new creme.form.DropDown($(this), options);
    },
    destroy: function(instance) {
        instance.destroy();
    },
    methods: [
        'select', 'next'
    ],
    properties: [
        'mode'
    ]
});

}(jQuery));
