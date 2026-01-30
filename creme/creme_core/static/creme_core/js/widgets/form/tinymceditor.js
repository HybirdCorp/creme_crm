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
    var host, baseURI;

    if (url.match(/^(http|https):\/\//)) {
        host = '${protocol}//${host}/'.template(_.urlAsDict(url));
        baseURI = new tinymce.util.URI(url, {
            base_uri: new tinymce.utils.URI(host)
        });
    } else if (url.match(/^file:\/\//)) {
        baseURI = new tinymce.util.URI(url);
    } else {
        host = '${protocol}//${host}/'.template(_.urlAsDict(window.location.href));
        baseURI = new tinymce.util.URI(url, {
            base_uri: new tinymce.util.URI(host)
        });
    }

    return {
        document_base_url: url,
        base_url: url,
        plugin_base_urls: url,
        base_uri: baseURI
    };
};

function setupTinyMCE(options) {
    return new Promise(function(resolve, reject) {
        try {
            tinymce._setBaseUrl = function(baseUrl) {
                this.baseURL = options.base_url;
                this.baseURI = options.base_uri;
            };

            tinymce.init(Object.assign({
                plugins: BUNDLE_PLUGINS
            }, options || {}, {
                license_key: 'gpl',
                suffix: options.suffix || '.min',  // only gets minified scripts '.min.js'
                skin: 'oxide'
                /*
                theme_url: 'themes/${theme}/theme${suffix}.js'.template({
                    theme: options.theme || 'silver',
                    suffix: options.suffix || '.min'
                }),
                model_url: 'models/${model}/model${suffix}.js'.template({
                    model: options.model || 'dom',
                    suffix: options.suffix || '.min'
                }),
                icons_url: 'icons/${icons}/icons${suffix}.js'.template({
                    icons: options.icons || 'default',
                    suffix: options.suffix || '.min'
                })
                */
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
    if (!Object.isEmpty(value)) {
        return value === 'fit-input' ? element.width() + 'px' : value;
    }
}

function parseWidthAsNumber(value, element) {
    if (!Object.isEmpty(value)) {
        var width = (value === 'fit-input' ? element.width() : parseInt(value));
        return isNaN(width) ? undefined : width;
    }
}

function parseHeight(value, element) {
    if (!Object.isEmpty(value)) {
        switch (value) {
            case 'fit-input':
                return element.height() + 'px';
            case 'fit-rows':
                var rows = parseInt(element.attr('rows')) || 0;
                return rows > 0 ? rows + 'em' : element.height() + 'px';
            default:
                return value;
        }
    }
}

function parseHeightAsNumber(value, element) {
    if (!Object.isEmpty(value)) {
        switch (value) {
            case 'fit-input':
                return element.height();
            case 'fit-rows':
                var rows = parseInt(element.attr('rows')) || 0;
                var fontSize = Math.ceil(parseFloat(window.getComputedStyle(element.get(0)).fontSize));
                return rows ? rows * fontSize : element.height();
            default:
                return parseInt(value);
        }
    }
}

function parseResize(value) {
    value = String(value || '').toLowerCase();
    Assert.in(value, ['both', 'height', 'none', 'no'], 'The allowResize value "${value}" is invalid.');

    return (value === 'both') ? value : (value === 'height');
}

creme.TinyMCEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            uploadURL: element.data('uploadUrl') || '',
            uploadField: element.data('uploadField') || 'file',
            uploadOnChange: true,
            csrftoken: null,
            toolbar: element.data('toolbar') || 'full',
            placeholder: element.data('placeholder') || element.attr('placeholder') || gettext('Type here...'),
            width: element.data('editorWidth'),
            minWidth: element.data('editorMinWidth'),
            maxWidth: element.data('editorMaxWidth'),
            height: element.data('editorHeight'),
            minHeight: element.data('editorMinHeight'),
            maxHeight: element.data('editorMaxHeight'),
            isDisabled: element.prop('disabled'),
            isReadOnly: element.prop('readonly'),
            baseURL: element.data('baseUrl') || '/tiny_mce/8.3.2/',
            allowCrossOrigin: false,
            allowResize: element.data('resize') || 'no'
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

        this._element = element;
        this._editorSetup = setupTinyMCE(Object.assign({
            target: element.get(0)
        }, editorOptions)).then(function(editors) {
            var editor = self._editor = editors[0];
            element.addClass('creme-tinymce-hidden');
            element.data('tiny-editor', editor);
            element.on('html5-pre-validate', self._onPreValidate);
            element.prop('disabled', options.isDisabled);
            element.prop('readonly', options.isReadOnly);
        });
    },

    editorSetup: function() {
        return this._editorSetup;
    },

    isDisabled: function(state) {
        if (state === undefined) {
            return this._element.prop('disabled');
        }

        this._toggleEditorDisabled(state);
        this._element.prop('disabled', state);
        return this;
    },

    isReadOnly: function(state) {
        if (state === undefined) {
            return this._editor.mode.isReadOnly();
        }

        this._toggleEditorReadOnly(state);
        this._element.prop('readonly', state);
        return this;
    },

    _toggleEditorReadOnly: function(state) {
        if (!Object.isNone(this._editor)) {
            var prev = this._editor.mode.isReadOnly();
            if (prev !== state) {
                this._editor.mode.set(state ? 'readonly' : 'design');
            }
        }
    },

    _toggleEditorDisabled: function(state) {
        if (!Object.isNone(this._editor)) {
            var prev = this.isDisabled();
            if (prev !== state) {
                this._editor.ui.setEnabled(!state);
            }
        }
    },

    _editorToolbarItems: function(options) {
        var items;
        var toolbar = options.toolbar || 'full';

        if (Array.isArray(toolbar)) {
            items = {
                menubar: false,
                toolbar: toolbar.slice(),
                insert_quickbars: []
            };
        } else {
            items = EDITOR_TOOLBARS[toolbar];
            Assert.that(items !== undefined, 'TinyMCEditor toolbar "${toolbar}" does not exist', options);
        }

        return items;
    },

    _editorUploadHandler: function(options) {
        return function(blobInfo, progressCb) {
            return new Promise(function(resolve, reject) {
                var formData = new FormData();
                formData.append(options.uploadField, blobInfo.blob(), blobInfo.filename());

                creme.ajax.query(options.uploadURL, {action: 'post'}, formData).onUploadProgress(function(e) {
                    progressCb(e.loadedPercent);
                }).onFail(function(e) {
                    reject(gettext("Unable to upload this image"));
                }).onDone(function(e, data) {
                    resolve(_.cleanJSON(data, data));
                }).start();
            });
        };
    },

    _editorOptions: function(element, options) {
        var toolbarItems = this._editorToolbarItems(options);
        var plugins = availablePlugins();
        var editorOptions = {
            readonly: options.isReadOnly,
            disabled: options.isDisabled,
            placeholder: options.placeholder,
            icons: 'creme'
        };

        if (_.isFunction(options.allowCrossOrigin)) {
            editorOptions.crossorigin = options.allowCrossOrigin;
        } else if (_.isString(options.allowCrossOrigin)) {
            editorOptions.crossorigin = function() {
                return options.allowCrossOrigin;
            };
        }

        if (options.baseURL) {
            Object.assign(editorOptions, buildTinyMCEBaseURLs(options.baseURL));
        }

        if (options.uploadURL) {
            editorOptions.images_upload_handler = this._editorUploadHandler(options);
            editorOptions.automatic_uploads = !!options.uploadOnChange;
        } else {
            toolbarItems.toolbar = _.without(toolbarItems.toolbar, 'image');
            plugins = _.without(plugins, 'image');
        }

        editorOptions.width = parseWidth(options.width, element);
        editorOptions.max_width = parseWidthAsNumber(options.maxWidth, element);
        editorOptions.min_width = parseWidthAsNumber(options.minWidth, element);

        editorOptions.height = parseHeight(options.height, element);
        editorOptions.max_height = parseHeightAsNumber(options.maxHeight, element);
        editorOptions.min_height = parseHeightAsNumber(options.minHeight, element);

        editorOptions = $.extend(editorOptions, {
            plugins: plugins,
            quickbars_insert_toolbar: (toolbarItems.insert_quickbars || []).join(' '),
            toolbar: (toolbarItems.toolbar || []).join(' '),
            menubar: (toolbarItems.menubar || []).join(' '),
            toolbar_groups: toolbarItems.toolbar_groups || {},
            toolbar_mode: 'floating',
            resize: parseResize(options.allowResize)
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
        editor.save();

        return this;
    },

    destroy: function() {
        if (!Object.isNone(this._editor)) {
            this._editor.remove();
            this._editor = null;
            this._editorSetup = null;
            this._element.data('tiny-editor', null);
            this._element.off('html5-pre-validate', this._onPreValidate);
        }

        return this;
    }
});

}(jQuery));
