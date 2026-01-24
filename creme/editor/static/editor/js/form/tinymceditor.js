/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2026 Hybird
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

/* globals TinyMCEBundle */

(function($) {
"use strict";

tinymce.IconManager.add('creme', {
    icons: {
        'title': '<svg width="24" height="24" viewBox="0 -960 960 960"><path d="M420-160v-520H200v-120h560v120H540v520H420Z"/></svg>'
    }
});

/*
var BUNDLE_PLUGINS = [
    'accordion',
    'advlist',
    'anchor',
    'autolink',
    'autoresize',
    'autosave',
    'charmap',
    'code',
    'codesample',
    'directionality',
    // 'emoticons',
    'fullscreen',
    'help',
    'image',
    'importcss',
    'insertdatetime',
    'link',
    'lists',
    'media',
    'nonbreaking',
    'pagebreak',
    'preview',
    'quickbars',
    'save',
    'searchreplace',
    'table',
    'visualblocks',
    'visualchars',
    'wordcount'
];

function availablePlugins() {
    return BUNDLE_PLUGINS.slice();
};

function setupTinyMCE(options) {
    return new Promise(function(resolve, reject) {
        try {
            tinymce.init(Object.assign({
                plugins: BUNDLE_PLUGINS
            }, options || {}, {
                license_key: 'gpl',
                // skin: false,
                // content_css: false,
                // content_style: `${contentUiSkinCss}\n${contentCss}`,
                setup: function(editor) {
                    resolve(editor);
                }
            }));
        } catch (e) {
            reject(e);
        }
    });
};
*/

var EDITOR_TOOLBARS = {
    simple: {
        menubar: false,
        toolbar: [
            'undo', 'redo', '|',
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'numlist', 'bullist', '|',
            'backcolor', 'forecolor', 'fontfamily', 'fontsize'
        ],
        insert_quickbars: []
    },
    template: {
        menubar: false,
        toolbar: [
            'undo', 'redo', '|',
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'numlist', 'bullist', '|',
            'outdent', 'indent', '|',
            'backcolor', 'forecolor', 'fontfamily', 'fontsize', '|',
            'link', 'unlink', '|', 'blockquote', 'table', 'image' //, '|', 'placeholder'
        ],
        insert_quickbars: [
            'quickimage', 'quicktable'
        ]
    },
    full: {
        menubar: false,
        toolbar: [
            'undo', 'redo', '|',
            'heading', '|',
            'bold', 'italic', 'underline', 'strikethrough', 'subscript', 'superscript', '|',
            'alignleft', 'aligncenter', 'alignright', 'alignjustify',
            'numlist', 'bullist', '|',
            'outdent', 'indent', '|',
            'backcolor', 'forecolor', 'fontfamily', 'fontsize', '|',
            'link', 'unlink', '|', 'blockquote', 'hr', 'tables', 'image'
        ],
        toolbar_groups: {
            heading: {
                icon: 'title',
                tooltip: gettext('Heading'),
                items: 'h1 h2 h3 h4 h5'
            },
            tables: {
                icon: 'table',
                tooltip: gettext('Table'),
                items: (
                    'table tabledelete | tableprops tablerowprops tablecellprops |' +
                    'tableinsertrowbefore tableinsertrowafter tabledeleterow |' +
                    'tableinsertcolbefore tableinsertcolafter tabledeletecol'
                )
            }
        },
        insert_quickbars: [
            'quickimage', 'quicktable'
        ]
    }
};

var EDITOR_DEFAULT_PLACEHOLDERS = [
    {name: 'name', label: gettext('Fullname')},
    {name: 'first_name', label: gettext('First name')},
    {name: 'last_name', label: gettext('Last name')},
    {name: 'civility', label: gettext('Civility')}
];

function parseWidth(value, element) {
    return value === 'fit-input' ? element.width() : value;
}

function parseHeight(value, element) {
    switch (value) {
        case 'fit-input':
            return element.height() + 'px';
        case 'fit-rows':
            var rows = parseInt(element.attr('rows')) || 0;
            return rows ? rows + 'em' : element.height() + 'px';
        default:
            return value;
    }
}

creme.TinyMCEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            uploadURL: element.data('upload'),
            uploadField: element.data('uploadField') || 'file',
            csrftoken: null,
            toolbar: element.data('toolbar') || 'full',
            disabledToolbarMode: element.data('disabledToolbar') || false,
            placeholders: EDITOR_DEFAULT_PLACEHOLDERS,
            maxWidth: element.data('editorWidth'),
            minHeight: element.data('editorHeight'),
            isDisabled: element.prop('disabled'),
            isReadOnly: element.prop('readonly')
        }, options || {});

        Assert.not(element.is('.creme-tinymce-hidden'), 'TinyMCE instance is already active');

        var self = this;
        var editorOptions = this._editorOptions(element, options);

        if (Object.isEmpty(element.attr('id'))) {
            element.attr('id', _.uniqueId('creme-tinymce__'));
        }

        this._onPreValidate = function() {
            if (this._editor && this._editor.isDirty()) {
                this._editor.save();
            }
        }.bind(this);

        this._editorSetup = TinyMCEBundle.setup(Object.assign({
            target: element.get(0)
        }, editorOptions)).then(function(editor) {
            self._editor = editor;
            element.addClass('creme-tinymce-hidden');
            element.data('tiny-editor', editor);
            element.on('html5-pre-validate', self._onPreValidate);
        });
    },

    editorSetup: function() {
        return this._editorSetup;
    },

    isDisabled: function(state) {
        if (state === undefined) {
            return this._element.prop('disabled');
        }

        this._element.prop('disabled', state);
        this._toggleEditorDisabled(this.isDisabled());
        return this;
    },

    isReadOnly: function(state) {
        if (state === undefined) {
            return this._element.prop('readonly');
        }

        this._element.prop('readonly', state);
        this._toggleEditorReadOnly(this.isDisabled());
        return this;
    },

    _toggleEditorReadOnly: function(state) {
        if (!Object.isNone(this._editor)) {
            var prev = this._editor.options.get('readonly');
            if (prev !== state) {
                this._editor.options.get('readonly', state);
            }
        }
    },

    _toggleEditorDisabled: function(state) {
        if (!Object.isNone(this._editor)) {
            var prev = this._editor.options.get('disabled');
            if (prev !== state) {
                this._editor.options.get('disabled', state);
            }
        }
    },

    _editorToolbarItems: function(options) {
        var items;

        if (Array.isArray(options.toolbar)) {
            items = {
                toolbar: options.toolbar.slice(),
                insert_quickbars: []
            };
        } else {
            items = EDITOR_TOOLBARS[options.toolbar || 'full'] || {};
            Assert.that(items.toolbar.length > 0, 'TinyMCEditor toolbar "${toolbar}" does not exist', options);
        }

        return items;
    },

    _editorUploadHandler: function(options) {
        return function(blobInfo, progressCb) {
            return new Promise(function(resolve, reject) {
                var formData = new FormData();
                formData.append(options.uploadField, blobInfo.blob(), blobInfo.filename());

                creme.ajax.query(options.uploadURL, formData).onUploadProgress(function(e) {
                    progressCb(e.loadedPercent);
                }).onFail(function(e) {
                    reject(gettext("Unable to upload this image"));
                }).onDone(function() {
                    resolve();
                });
            });
        };
    },

    _editorOptions: function(element, options) {
        var toolbarItems = this._editorToolbarItems(options);
        var plugins = TinyMCEBundle.availablePlugins();
        var editorOptions = {
            readonly: options.isReadonly,
            disabled: options.isDisabled,
            placeholder: options.placeholders[element.attr('name')] || gettext('Type here...'),
            icons: 'creme'
        };

        if (options.uploadURL) {
            editorOptions.images_upload_handler = this._editorUploadHandler(options);
        } else {
            toolbarItems.toolbar = _.without(toolbarItems.toolbar, 'image');
            plugins = _.without(plugins, 'image');
        }

        /*
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
        */

        if (!Object.isEmpty(options.maxWidth)) {
            editorOptions.max_width = parseWidth(options.maxWidth, element);
        }

        editorOptions = $.extend(editorOptions, {
            plugins: plugins,
            quickbars_insert_toolbar: (toolbarItems.insert_quickbars || []).join(' '),
            toolbar: (toolbarItems.toolbar || []).join(' '),
            menubar: (toolbarItems.menubar || []).join(' '),
            toolbar_groups: toolbarItems.toolbar_groups || {},
            toolbar_mode: 'floating',
            max_height: parseHeight(options.maxHeight)
        });

        return editorOptions;
    },

    element: function() {
        return this._element;
    },

    editor: function() {
        return this._editor;
    },

    insertHtml: function(html) {
        var editor = this.editor();

        Assert.not(Object.isNone(editor), 'TinyMCE instance does not exist');
        editor.insertContent(html);

        return this;
    },

    destroy: function() {
        if (!Object.isNone(this._editor)) {
            this._editor.remove();
            this._editor = null;
            this._element.data('tiny-editor', null);
            this._element.off('html5-pre-validate', this._onPreValidate);
        }

        return this;
    }
});

}(jQuery));
