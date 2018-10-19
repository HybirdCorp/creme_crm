/* eslint operator-linebreak: ["error", "before"] */

(function($) {
    "use strict";

    window.QUnitDialogMixin = {
        assertClosedDialog: function() {
            equal(0, $('.ui-dialog').length, 'is dialog not opened');
        },

        assertDialogTitle: function(title) {
            equal(title, $('.ui-dialog .ui-dialog-title').text(), 'dialog title');
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
            $('.ui-dialog button[name="send"]').click();

            return formHtml;
        },

        acceptConfirmDialog: function() {
            equal(1, $('.ui-dialog').length, 'single confirm dialog allowed');
            equal(1, $('.ui-dialog button[name="ok"]').length, 'single confirm ok button allowed');

            $('.ui-dialog button[name="ok"]').click();
        },

        findDialogButtonsByLabel: function(label, dialog) {
            dialog = dialog || $('.ui-dialog');

            return dialog.find('.ui-dialog-buttonset .ui-button-text')
                         .filter(function() {
                             return $(this).text().indexOf(label) !== -1;
                         })
                         .map(function() {
                             return $(this).parents('button:first').get(0);
                         });
        }
    };

}(jQuery));
