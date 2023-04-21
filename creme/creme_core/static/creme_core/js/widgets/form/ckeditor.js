/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2022-2023 Hybird
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

/* globals ClassicEditor */

(function($) {
"use strict";

creme.form = creme.form || {};

var CKEDITOR_TOOLBARS = {
    simple: [
        'undo', 'redo', '|',
        'bold', 'italic', 'underline', '|',
        'numberedList', 'bulletedList', '|',
        'fontbackgroundcolor', 'fontcolor', 'fontfamily', 'fontsize'
    ],
    full: [
        'undo', 'redo', '|',
        'bold', 'italic', 'underline', '|',
        'numberedList', 'bulletedList', '|',
        'outdent', 'indent', '|',
        'fontbackgroundcolor', 'fontcolor', 'fontfamily', 'fontsize', '|',
        'link', 'blockquote', 'inserttable', 'imageupload', 'mediaembed'
    ]
};

creme.form.CKEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            uploadURL: element.data('ckeditorUpload'),
            csrftoken: null,
            updateSourceDelay: element.data('ckeditorUpdateDelay'),
            toolbar: element.data('ckeditorToolbar') || 'full',
            maxWidth: element.data('ckeditorMaxWidth'),
            isDisabled: element.prop('disabled'),
            isReadOnly: element.prop('readonly')
        }, options || {});

        Assert.not(element.is('.creme-ckeditor-hidden'), 'CkEditor instance is already active');

        var self = this;
        var editorOptions = this._ckeditorOptions(element, options);

        if (Object.isEmpty(element.attr('id'))) {
            element.attr('id', _.uniqueId('creme-ckeditor__'));
        }

        ClassicEditor.create(element.get(0), editorOptions).then(function(editor) {
            element.addClass('.creme-ckeditor-hidden');
            element.parent().find('.ck.ck-editor').css('max-width', editorOptions.maxWidth);

            self._editor = editor;
            self._element = element;

            editor.model.document.on('change:data', _.debounce(function(e, data) {
                editor.updateSourceElement();
            }, options.updateSourceDelay));

            self.isReadOnly(options.isReadOnly);
            self.isDisabled(options.isDisabled);
        }).catch(function (e) {
            console.error(e);
        });
    },

    isDisabled: function(state) {
        if (state === undefined) {
            return this._element.prop('disabled');
        }

        this._element.prop('disabled', state);
        this._toggleEditorReadOnly(this.isDisabled() || this.isReadOnly());
    },

    isReadOnly: function(state) {
        if (state === undefined) {
            return this._element.prop('readonly');
        }

        this._element.prop('readonly', state);
        this._toggleEditorReadOnly(this.isDisabled() || this.isReadOnly());
    },

    _toggleEditorReadOnly: function(state) {
        if (!Object.isNone(this._editor)) {
            var prev = this._editor.isReadOnly;
            var id = this._element.attr('id');

            if (id && prev !== state) {
                if (state) {
                    this._editor.enableReadOnlyMode(id);
                } else {
                    this._editor.disableReadOnlyMode(id);
                }
            }
        }
    },

    _ckeditorOptions: function(element, options) {
        var csrftoken = options.csrftoken || creme.ajax.cookieCSRF();
        var toolbarItems = CKEDITOR_TOOLBARS[options.toolbar || 'full'];
        var editorOptions = {
            toolbar: {
                items: toolbarItems,
                shouldNotGroupWhenFull: true
            }
        };

        Assert.that(toolbarItems.length > 0, 'CkEditor toolbar "${toolbar}" does not exist', options);

        if (options.uploadURL) {
            editorOptions.simpleUpload = {
                uploadUrl: options.uploadURL,  // The URL that the images are uploaded to.
                withCredentials: true,  // Enable the XMLHttpRequest.withCredentials property.
                headers: {  // Headers sent along with the XMLHttpRequest to the upload server.
                    'X-CSRFToken': csrftoken
                }
            };
        } else if (toolbarItems.indexOf('imageupload') !== -1) {
            toolbarItems.splice(toolbarItems.indexOf('imageupload'), 1);
        }

        if (!Object.isEmpty(options.maxWidth)) {
            switch (options.maxWidth) {
                case 'fit-input':
                    editorOptions.maxWidth = element.outerWidth();
                    break;
                default:
                    editorOptions.maxWidth = options.maxWidth;
            }
        }

        return editorOptions;
    },

    destroy: function() {
        if (!Object.isNone(this._editor)) {
            this._editor.destroy();
            this._editor = null;
        }
    }
});

}(jQuery));
