/* Import TinyMCE */
const tinymce = require('tinymce/tinymce');

/* Default icons are required. After that, import custom icons if applicable */
require('tinymce/icons/default');

/* Required TinyMCE components */
require('tinymce/themes/silver');
require('tinymce/models/dom');

/* Import the default skin (oxide). Replace with a custom skin if required. */
require('tinymce/skins/ui/oxide/skin.css');

const BUNDLE_PLUGINS = [
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

/* Import plugins - include the relevant plugin in the 'plugins' option. */
for (const plugin of BUNDLE_PLUGINS) {
    require(`tinymce/plugins/${plugin}`);
}

require('tinymce/plugins/help');
require('tinymce/plugins/help/js/i18n/keynav/en');

/* content UI CSS is required (using the default oxide skin) */
const contentUiSkinCss = require('tinymce/skins/ui/oxide/content.css');

/* The default content CSS can be changed or replaced with appropriate CSS for the editor content. */
const contentCss = require('tinymce/skins/content/default/content.css');

/* Initialize TinyMCE */
exports.setup = function(options) {
    return new Promise(function(resolve, reject) {
        try {
            tinymce.init(Object.assign({
                /* All plugins need to be imported and added to the plugins option. */
                plugins: BUNDLE_PLUGINS,
            }, options || {}, {
                license_key: 'gpl',
                skin: false,
                content_css: false,
                content_style: `${contentUiSkinCss}\n${contentCss}`,
                setup: function(editor) {
                    resolve(editor);
                }
            }));
        } catch (e) {
            reject(e);
        }
    });
};

exports.availablePlugins = function() {
    return BUNDLE_PLUGINS.slice();
}
