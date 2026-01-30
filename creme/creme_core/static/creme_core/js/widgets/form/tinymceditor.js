(function($) {
"use strict";

tinymce.IconManager.add('creme', {
    icons: {
        'title': (
             '<svg width="24" height="24" viewBox="0 0 18 18">' +
                '<path d="M13.62 10.08 12.1 4.66h-.06l-1.5 5.42zM5.7 11.13 4.53 7.02h-.08l-1.13 4.11zM17.31 15h-2.25l-.95-3.25h-4.07L9.09 15H6.84l-.69-2.33H2.87L2.17 15H0l3.3-9.59h2.5l2.17 6.34L10.86 3h2.52l3.94 12z"/>' +
             '</svg>'
        )
    }
});

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
    'emoticons',
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

function buildTinyMCEBaseURLs(url) {
    var base;

    if (!url.match(/^(http|https):\/\//)) {
        base = '${protocol}//${host}/'.template(_.urlAsDict(window.location.href));
        url = base + url;
    } else {
        base = '${protocol}//${host}/'.template(_.urlAsDict(url));
    }

    return {
        document_base_url: url,
        base_url: url,
        base_uri: new tinymce.util.URI(tinymce.documentBaseURL, {
            base_uri: base
        })
    };
};

function setupTinyMCE(options) {
    return new Promise(function(resolve, reject) {
        try {
            tinymce.init(Object.assign({
                plugins: BUNDLE_PLUGINS
            }, options || {}, {
                license_key: 'gpl',
                suffix: '.min',  // only gets minified scripts '.min.js'
                skin: 'oxide'
                // content_css: false,
                // content_style: `${contentUiSkinCss}\n${contentCss}`,
            })).then(resolve);
        } catch (e) {
            reject(e);
        }
    });
};

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

/*
var EDITOR_DEFAULT_TEMPLATES = [
    {name: 'name', label: gettext('Fullname')},
    {name: 'first_name', label: gettext('First name')},
    {name: 'last_name', label: gettext('Last name')},
    {name: 'civility', label: gettext('Civility')}
];
*/

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
            uploadURL: element.data('uploadUrl') || '',
            uploadField: element.data('uploadField') || 'file',
            csrftoken: null,
            toolbar: element.data('toolbar') || 'full',
            disabledToolbarMode: element.data('disabledToolbar') || false,
            placeholder: element.data('placeholder') || element.attr('placeholder') || gettext('Type here...'),
            maxWidth: element.data('editorWidth'),
            minHeight: element.data('editorHeight'),
            isDisabled: element.prop('disabled'),
            isReadOnly: element.prop('readonly'),
            baseURL: element.data('baseUrl') || 'tiny_mce/8.3.2/'
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

        this._editorSetup = setupTinyMCE(Object.assign({
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
        var plugins = availablePlugins();
        var editorOptions = {
            readonly: options.isReadonly,
            disabled: options.isDisabled,
            placeholder: options.placeholder,
            icons: 'creme'
        };

        if (options.baseURL) {
            Object.assign(editorOptions, buildTinyMCEBaseURLs(options.baseURL));
        }

        if (options.uploadURL) {
            editorOptions.images_upload_handler = this._editorUploadHandler(options);
        } else {
            toolbarItems.toolbar = _.without(toolbarItems.toolbar, 'image');
            plugins = _.without(plugins, 'image');
        }

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
