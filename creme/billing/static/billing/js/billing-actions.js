/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018  Hybird

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

creme.billing = creme.billing || {};

creme.billing.ExportDocumentAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _download: function(url, format) {
        this.done();
        creme.utils.goTo(url + '?' + $.param({format: format}));
    },

    _run: function(options) {
        options = $.extend({
            formats: []
        }, this.options(), options || {});

        var self = this;
        var url = options.url;
        var count = options.formats.length;

        if (count > 1) {
            creme.dialogs.choice(gettext("Select the export format of your billing document"), {
                             required: true,
                             choices: options.formats
                          })
                         .onOk(function(event, data) {
                             self._download(url, data);
                          })
                         .onClose(function(event, data) {
                             self.cancel();
                          })
                         .open();
        } else if (count === 1) {
            self._download(url, options.formats[0].value);
        } else {
            creme.dialogs.warning(gettext("No such export format for billing documents."))
                         .onClose(function() {
                             self.cancel();
                         })
                         .open();
        }
    }
});

creme.billing.EXPORT_FORMATS = [
   // {value:'odt', label: gettext("Document open-office (ODT)")},
   {value: 'pdf', label: gettext("Pdf file (PDF)")}
];

// TODO remove this after menu hat-bar refactor using action-links
creme.billing.exportAs = function(url, formats) {
    new creme.billing.ExportDocumentAction({
        url: url,
        formats: formats || creme.billing.EXPORT_FORMATS
    }).start();
};

// TODO remove this after menu hat-bar refactor using action-links
creme.billing.generateInvoiceNumber = function(url) {
    return creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true, reloadOnSuccess: true})
                      .start();
};

var billingLinesActions = {
    'billing-line-addonfly': function(url, options, data, e) {
        return new creme.component.Action(function() {
            var count = data.count ? parseInt(data.count) : 0;
            creme.billing.showEmptyForm($(e.currentTarget), data.ctype_id, data.prefix, count);
            this.done();
        });
    },

    'billing-line-saveall': function(url, options, data, e) {
        var brick = this._brick;

        return new creme.component.Action(function() {
            if (creme.billing.formsHaveErrors()) {
                creme.dialogs.alert('<p>' + gettext('There are some errors in your lines.') + '</p>').open();
            } else {
                var formsData = {};

                creme.billing.modifiedBLineForms().each(function() {
                    var container = $(this);
                    formsData[container.attr('ct_id')] = $.toJSON(creme.billing.serializeForm(container));
                });

                if (formsData.length === 0) {
                    console.log('Forms not modified !');
                    return this.cancel();
                }

                creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true, warnOnFailTitle: gettext('Errors report')}, formsData)
                           .onDone(function() { brick.refresh(); })
                           .onFail(this.fail.bind(this))
                           .start();
            }
        });
    },

    'billing-line-clearonfly': function(url, action, data, e) {
        var brick = this._brick;

        return new creme.component.Action(function() {
            creme.billing.hideEmptyForm(data.ctype_id, data.prefix, data.count);
            $('[data-action="billing-line-addonfly"]', brick._element).removeClass('forbidden');
            this.done();
        });
    }
};

$(document).on('brick-setup-actions', '.brick.billing-lines-brick', function(e, brick, actions) {
                actions.registerAll(billingLinesActions);
            })
           .on('brick-ready', function(e, brick, options) {
                creme.billing.initLinesBrick(brick);
            });

}(jQuery));
