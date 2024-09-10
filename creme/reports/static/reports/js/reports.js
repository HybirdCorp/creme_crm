/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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
 * Requires : creme, jQuery, creme.utils, creme.ajax, creme.dialogs
 */

(function($) {
"use strict";

creme.reports = creme.reports || {};

/* TODO : Refactor this controller with polymorphic inputs to allows filters
 * like the "Nth Month from now" or "N years ago"
 *
 * TODO : Deprecate daterange which is only used here ?
 */

creme.reports.PreviewController = creme.component.Component.sub({
    _init_: function(options) {
        options = options || {};

        this._redirectUrl = options.previewUrl || '';
        this._downloadUrl = options.downloadUrl || '';

        this._listeners = {
            update:   this._updateHeader.bind(this),
            redirect: this.redirect.bind(this),
            download: this.download.bind(this)
        };
    },

    isBound: function() {
        return this._header !== undefined;
    },

    bind: function(element) {
        Assert.not(this.isBound(), 'creme.reports.PreviewController is already bound.');

        var listeners = this._listeners;
        var header = this._header = $('.report-preview-header', element);

        $('select[name="date_field"]', header).on('change', listeners.update);
        $('button[name="generate"]', header).on('click', listeners.redirect);
        $('button[name="download"]', header).on('click', listeners.download);

        this._updateHeader();
        return this;
    },

    unbind: function() {
        Assert.that(this.isBound(), 'creme.reports.PreviewController is not bound.');

        var listeners = this._listeners;
        var header = this._header;

        if (header !== undefined) {
            $('select[name="date_field"]', header).unbind('change', listeners.update);
            $('button[name="generate"]', header).unbind('click', listeners.redirect);
            $('button[name="download"]', header).unbind('click', listeners.download);
        }

        this._header = undefined;
        return this;
    },

    _updateHeader: function() {
        var header = this._header;
        var range = $('.ui-creme-daterange', header);
        var needsRange = !Object.isEmpty($('[name="date_field"]', header).val());

        $('.date-filter', header).toggle(needsRange);

        if (needsRange && range.length > 0) {
            range.creme().widget().reset();
        }
    },

    redirect: function() {
        creme.utils.goTo(this._redirectUrl, $('form', this._header).serialize());
    },

    download: function() {
        creme.utils.goTo(this._downloadUrl, $('form', this._header).serialize());
    }
});

}(jQuery));
