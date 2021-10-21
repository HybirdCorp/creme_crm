/* eslint operator-linebreak: ["error", "before"] */
/* globals FunctionFaker */

(function($) {
    "use strict";

    window.QUnitDialogMixin = {
        beforeEach: function() {
            $('<div class="ui-dialog-within-container"></div>').appendTo('body');
        },

        afterEach: function() {
            this.shutdownDialogs();

            // detach dialog container (limits movement of dialogs within it)
            $('.ui-dialog-within-container').detach();
        },

        withScrollBackFaker: function(block) {
            return new FunctionFaker({
                instance: creme.utils,
                method: 'scrollBack'
            }).with(block.bind(this));
        },

        shutdownDialogs: function() {
            $('.chzn-drop').detach();

            // close all opened popover
            $('.popover').trigger('modal-close');

            // close opened dialogs
            $('.ui-dialog-content').dialog('destroy');
        },

        assertClosedPopover: function() {
            equal(0, $('body > .popover').length, 'is popover not opened');
        },

        assertOpenedPopover: function() {
            var dialogs = $('body > .popover');
            equal(1, dialogs.length, 'is popover not opened');
            return dialogs;
        },

        assertPopoverTitle: function(title) {
            equal(title, $('body > .popover .popover-title:not(.hidden)').text(), 'dialog title');
        },

        assertClosedDialog: function() {
            equal(0, $('.ui-dialog').length, 'is dialog not opened');
        },

        assertDialogTitle: function(title) {
            equal(title, $('.ui-dialog .ui-dialog-title').text(), 'dialog title');
        },

        assertDialogTitleHtml: function(html) {
            this.equalHtml(html, $('.ui-dialog .ui-dialog-title'), 'dialog title html');
        },

        assertOpenedDialogs: function(count) {
            count = count || 1;

            var dialogs = $('.ui-dialog');

            equal(count, dialogs.length, '%d dialog(s) have to be opened'.format(count));

            return dialogs.sort(function(a, b) {
                var za = parseInt($(a).css('z-index')),
                    zb = parseInt($(b).css('z-index'));

                za = isNaN(za) ? 0 : za;
                zb = isNaN(zb) ? 0 : zb;

                return za - zb;
            }).get();
        },

        assertOpenedDialog: function(message) {
            var dialogs = $('.ui-dialog');

            equal(1, dialogs.length, 'is dialog opened');

            if (message !== undefined) {
                equal(message, $('.ui-dialog p').text(), 'dialog message');
            }

            return dialogs;
        },

        assertOpenedConfirmDialog: function(message) {
            var dialogs = $('.ui-dialog');

            equal(1, dialogs.length, 'is dialog opened');

            if (message !== undefined) {
                equal(message, $('.ui-dialog h4').text(), 'confirm dialog message');
            }

            return dialogs;
        },

        assertOpenedAlertDialog: function(message, header) {
            var dialogs = $('.ui-dialog .ui-creme-dialog-warn');

            equal(1, dialogs.length, 'is alert dialog opened');

            if (message !== undefined) {
                equal(message, $('.ui-dialog .ui-creme-dialog-warn .message').text(), 'alert dialog message');
            }

            if (header !== undefined) {
                equal(header,  $('.ui-dialog .ui-creme-dialog-warn .header').text(), 'alert dialog header');
            }

            return dialogs;
        },

        closeTopDialog: function() {
            var dialogs = $('.ui-dialog .ui-dialog-content').get();

            dialogs = dialogs.sort(function(a, b) {
                var a_zindex = $(a).attr('z-index');
                var b_zindex = $(b).attr('z-index');

                return (a_zindex > b_zindex) ? 1 : ((b_zindex > a_zindex) ? -1 : 0);
            }).reverse();

            equal(true, dialogs.length > 0);
            $(dialogs[0]).dialog('close');
        },

        closeDialog: function() {
            equal(1, $('.ui-dialog').length, 'single form dialog allowed');
            $('.ui-dialog-content').dialog('close');
        },

        submitFormDialog: function(data) {
            data = data || {};

            equal(1, $('.ui-dialog').length, 'single form dialog allowed');
            equal(1, $('.ui-dialog button[name="send"]').length, 'single form submit button allowed');

            for (var key in data) {
                $('.ui-dialog form [name="' + key + '"]').val(data[key]);
            }

            var formHtml = $('.ui-dialog form').html();
            $('.ui-dialog button[name="send"]').trigger('click');

            return formHtml;
        },

        acceptConfirmDialog: function() {
            equal(1, $('.ui-dialog').length, 'single confirm dialog allowed');
            equal(1, $('.ui-dialog button[name="ok"]').length, 'single confirm ok button allowed');

            $('.ui-dialog button[name="ok"]').trigger('click');
        },

        findDialogButtonsByLabel: function(label, dialog) {
            dialog = dialog || $('.ui-dialog');

            return dialog.find('.ui-dialog-buttonset .ui-button-text')
                         .filter(function() {
                             return $(this).text().indexOf(label) !== -1;
                         })
                         .map(function() {
//                             return $(this).parents('button:first').get(0);
                             return $(this).parents('button').first().get(0);
                         });
        },

        frameContentDataAsDict: function(response) {
            var data = response.data();

            return {
                content: response.content,
                data: Object.getPrototypeOf(data).jquery ? $('<div>').append(data).html() : data,
                type: response.type
            };
        },

        mockFormSubmitCalls: function(name) {
            var frameContentDataAsDict = this.frameContentDataAsDict.bind(this);

            return this.mockListenerCalls(name).map(function(e) {
                return [e[0], frameContentDataAsDict(e[1]), e[2]];
            });
        },

        assertOverlayState: function(element, expected) {
            expected = $.extend({
                status: undefined,
                active: false
            }, expected || {});

            var overlay = $('.ui-creme-overlay', element);

            equal(overlay.length, expected.active ? 1 : 0, 'has overlay');
            equal(overlay.attr('status'), expected.status, 'overlay status:' + expected.status);
            equal(overlay.hasClass('overlay-active'), expected.active, 'overlay isactive');
        }
    };

}(jQuery));
