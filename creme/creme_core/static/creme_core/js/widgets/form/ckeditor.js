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
        'bold', 'italic', 'underline', 'strikethrough', '|',
        'numberedList', 'bulletedList', '|',
        'fontbackgroundcolor', 'fontcolor', 'fontfamily', 'fontsize'
    ],
    template: [
        'undo', 'redo', '|',
        'bold', 'italic', 'underline', 'strikethrough', '|',
        'numberedList', 'bulletedList', '|',
        'outdent', 'indent', '|',
        'fontbackgroundcolor', 'fontcolor', 'fontfamily', 'fontsize', '|',
        'link', 'blockquote', 'inserttable', 'imageinsert', '|', 'placeholder'
    ],
    full: [
        'undo', 'redo', '|',
        'heading', '|',
        'bold', 'italic', 'underline', 'strikethrough', 'subscript', 'superscript', '|',
        'numberedList', 'bulletedList', '|',
        'outdent', 'indent', '|',
        'fontbackgroundcolor', 'fontcolor', 'fontfamily', 'fontsize', '|',
        'link', 'blockquote', 'horizontalline', 'inserttable', 'imageinsert'
    ]
};

var CKEDITOR_DEFAULT_PLACEHOLDERS = [
    {name: 'name', label: gettext('Fullname')},
    {name: 'first_name', label: gettext('First name')},
    {name: 'last_name', label: gettext('Last name')},
    {name: 'civility', label: gettext('Civility')}
];

creme.form.CKEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            uploadURL: element.data('ckeditorUpload'),
            csrftoken: null,
            updateSourceDelay: element.data('ckeditorUpdateDelay') || 0,
            toolbar: element.data('ckeditorToolbar') || 'full',
            toolbarExtra: element.data('ckeditorToolbarExtra') || '',
            hideDisabledToolbar: element.data('ckeditorHideDisabledToolbar') || false,
            placeholders: CKEDITOR_DEFAULT_PLACEHOLDERS,
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

        this._setup = ClassicEditor.create(element.get(0), editorOptions);
        this._setup.then(function(editor) {
            element.addClass('creme-ckeditor-hidden');
            element.parent().find('.ck.ck-editor').css('max-width', editorOptions.maxWidth);

            self._editor = editor;
            self._element = element;

            element.data('ck-editor', editor);

            editor.model.document.on('change:data', _.debounce(function(e, data) {
                editor.updateSourceElement();
            }, options.updateSourceDelay));

            editor.on('change:isReadOnly', function() {
                self._updateToolbarVisibility();
            });

            self.isReadOnly(options.isReadOnly);
            self.isDisabled(options.isDisabled);
            self.hideDisabledToolbar(options.hideDisabledToolbar);
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
        return this;
    },

    isReadOnly: function(state) {
        if (state === undefined) {
            return this._element.prop('readonly');
        }

        this._element.prop('readonly', state);
        this._toggleEditorReadOnly(this.isDisabled() || this.isReadOnly());
        return this;
    },

    hideDisabledToolbar: function(state) {
        if (state === undefined) {
            return this._hideDisabledToolbar;
        }

        this._hideDisabledToolbar = state;
        this._updateToolbarVisibility();
        return this;
    },

    _updateToolbarVisibility: function() {
        if (!Object.isNone(this._editor)) {
            var toolbar = $(this._editor.ui.view.toolbar.element);
            var disabled = this.isDisabled() || this.isReadOnly();

            toolbar.toggleClass('ck-hide-toolbar', this.hideDisabledToolbar() && disabled);
        }
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

    _ckeditorToolbarItems: function(options) {
        var items = CKEDITOR_TOOLBARS[options.toolbar || 'full'];
        var extras = !Object.isEmpty(options.toolbarExtra) ? (
            Array.isArray(options.toolbarExtra) ? options.toolbarExtra : options.toolbarExtra.split(',')
        ) : [];

        Assert.that(items.length > 0, 'CkEditor toolbar "${toolbar}" does not exist', options);

        return extras ? items.concat(extras) : items;
    },

    _ckeditorOptions: function(element, options) {
        var csrftoken = options.csrftoken || creme.ajax.cookieCSRF();
        var toolbarItems = this._ckeditorToolbarItems(options);
        var editorOptions = {};

        if (options.uploadURL) {
            editorOptions.simpleUpload = {
                uploadUrl: options.uploadURL,  // The URL that the images are uploaded to.
                withCredentials: true,  // Enable the XMLHttpRequest.withCredentials property.
                headers: {  // Headers sent along with the XMLHttpRequest to the upload server.
                    'X-CSRFToken': csrftoken
                }
            };
        } else {
            toolbarItems = _.without(toolbarItems, 'imageupload');
        }

        if (!Object.isEmpty(options.placeholders)) {
            editorOptions.placeholderConfig = {
                dropdownTitle: gettext('Placeholder'),
                types: options.placeholders.map(function(item) {
                    return Object.isString(item) ? { name: item } : item;
                })
            };
        } else {
            toolbarItems = _.without(toolbarItems, 'placeholder');
        }

        if (!Object.isEmpty(options.maxWidth)) {
            switch (options.maxWidth) {
                case 'fit-input':
                    editorOptions.maxWidth = element.width();
                    break;
                default:
                    editorOptions.maxWidth = options.maxWidth;
            }
        }

        editorOptions = $.extend(editorOptions, {
            toolbar: {
                items: toolbarItems,
                shouldNotGroupWhenFull: true
            },
            image: {
                toolbar: [
                    'imageStyle:inline', 'imageStyle:wrapText', 'imageStyle:breakText', '|',
                    'toggleImageCaption', 'imageTextAlternative'
                ]
            },
            table: {
                contentToolbar: [ 'tableRow', 'tableColumn', 'mergeTableCells' ]
            }
        });

        return editorOptions;
    },

    element: function() {
        return this._element;
    },

    ckeditorSetup: function() {
        return this._setup;
    },

    ckeditor: function() {
        return this._editor;
    },

    insertHtml: function(html, position) {
        var editor = this.ckeditor();

        Assert.not(Object.isNone(editor), 'CkEditor instance does not exist');

        var model = editor.model;
        var data = editor.data;

        if (position === undefined) {
            position = model.document.selection.getFirstPosition();
        } else if (Number.isInteger(position)) {
            position = model.createPositionAt(model.document.getRoot(), position);
        } else {
            position = model.createPositionAt(position);
        }

        var viewFragment = data.processor.toView(html);
        var modelFragment = data.toModel(viewFragment);

        model.insertContent(modelFragment);
        return this;
    },

    destroy: function() {
        if (!Object.isNone(this._editor)) {
            this._editor.destroy();
            this._editor = null;
            this._setup = null;
            this._element.data('ck-editor', null);
            this._element.removeClass('creme-ckeditor-hidden');
        }

        return this;
    }
});

}(jQuery));
