/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017-2018  Hybird

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
 * Requires : Creme
 */

(function($) {
"use strict";

creme.opportunities = creme.opportunities || {};

creme.opportunities.QuoteController = creme.component.Component.sub({
    _init_: function(options) {
        this._options = options || {};
    },

    bind: function(brick) {
        if (this.isBound()) {
            throw new Error('QuoteController is already bound');
        }

        brick.element().on('click', 'input.opportunities-current-quote[data-url]:not(.is-loading):not([disabled])', function(e) {
            e.preventDefault();
            e.stopPropagation();

            var url = $(this).attr('data-url');

            if (Object.isEmpty(url) === false) {
                $(this).addClass('is-loading');

                creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true})
                           .onDone(function() { brick.refresh(); })
                           .start();
            }
        });

        this._brick = brick;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});

}(jQuery));
