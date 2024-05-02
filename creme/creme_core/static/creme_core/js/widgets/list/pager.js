/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2024  Hybird

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

creme.list = creme.list || {};

creme.list.Pager = creme.component.Component.sub({
    _init_: function(options) {
        this._options = $.extend({
            debounceDelay: 50
        }, options || {});
        this._events = new creme.component.EventHandler();
        this._element = null;
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

    _cleanPageInput: function(input) {
        var page = parseInt(input.val());
        var max = parseInt(input.attr('max'));

        if (isNaN(page) || page < 1 || (!isNaN(max) && page > max)) {
            page = null;
        }

        input.toggleClass('invalid-page', Object.isNone(page));
        return page;
    },

    _goToChosenPage: function(input) {
        this.refresh(this._cleanPageInput(input));
    },

    _resizeChooseInput: function(input) {
        var canvas2d = this.canvas2d();
        var value = Object.isNone(input.val()) ? '' : input.val();

        canvas2d.font = input.css('font-size') + ' ' + input.css('font-family');
        var width = canvas2d.measureText(value).width;

        input.css('width', width + 25);
        return input;
    },

    _initializeChooseLink: function(choose) {
        var self = this;
        var input = $('input', choose).first();

        var debounce = function(cb) {
            if (self._options.debounceDelay > 0) {
                return _.debounce(cb, self._options.debounceDelay);
            } else {
                return cb;
            }
        };

        choose.on('click', function(e) {
                   e.stopPropagation();
                   choose.addClass('active');

                   input.val(input.attr('data-initial-value'));

                   self._cleanPageInput(input);
                   self._resizeChooseInput(input);

                   input.select().trigger('focus');
               });

        input.on('propertychange input change paste', debounce(function() {
                  self._cleanPageInput(input);
              }))
             .on('propertychange input change paste keydown', debounce(function() {
                  self._resizeChooseInput(input);
              }))
             .on('keyup', function(e) {
                 if (e.keyCode === 13) {
                     e.preventDefault();
                     self._goToChosenPage(input);
                 } else if (e.keyCode === 27) {
                     e.preventDefault();
                     input.trigger('focusout');
                 }
              })
             .on('blur focusout', function() {
                 choose.removeClass('active');
              });
    },

    refresh: function(page) {
        if (!Object.isEmpty(page)) {
            this._events.trigger('refresh', page);
        }
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('Pager is already bound');
        }

        var self = this;

        $('a.pager-link', element).on('click', function(e) {
            e.preventDefault();

            if ($(this).is('.is-disabled') === false) {
                self.refresh($(this).attr('data-page'));
            }
        });

        $('.pager-link-choose', element).each(function() {
            self._initializeChooseLink($(this));
        });

        this._element = element;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    }
});
}(jQuery));
