/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2025  Hybird

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

// HACK : force the right urls in tinymce globals
function setUpTinymce(url) {
    var base;

    if (!url.match(/^(http|https):\/\//)) {
        base = '${protocol}//${host}/'.template(_.urlAsDict(window.location.href));
        url = base + url;
    } else {
        base = '${protocol}//${host}/'.template(_.urlAsDict(url));
    }

    tinymce.documentBaseURL = url;
    tinymce.baseURL = tinymce.documentBaseURL;
    tinymce.baseURI = new tinymce.util.URI(tinymce.documentBaseURL, {
        base_uri: base
    });
}

creme.widget.Editor = creme.widget.declare('ui-creme-editor', {
    options: {
        datatype: 'string',
        basepath: '/tiny_mce'
    },

    _create: function(element, options, cb, sync) {
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        if (!this._enabled) {
            $(element).attr('disabled', '');
        }

        var id = element.attr('id') || _.uniqueId('tinymce-');
        element.attr('id', id);

        setUpTinymce(options.basepath);

        var editor = this._editor = new tinymce.Editor(id, {
            mode: 'textareas',
            theme: 'advanced',
            height: 300,
            language: 'en',
            document_base_url: 'tiny_mce/',
            plugins: [
                'spellchecker',
                'pagebreak',
                'style',
                'layer',
                'table',
                'save',
                'advhr',
                'advimage',
                'advlink',
                'emotions',
                'iespell',
                'inlinepopups',
                'insertdatetime',
                'preview',
                'media',
                'searchreplace',
                'print',
                'contextmenu',
                'paste',
                'directionality',
                'fullscreen',
                'noneditable',
                'visualchars',
                'nonbreaking',
                'xhtmlxtras',
                'template',
                'fullpage'
            ].join(','),
            theme_advanced_buttons1: [
                'save', 'newdocument', '|',
                'bold', 'italic', 'underline', 'strikethrough', '|',
                'justifyleft', 'justifycenter', 'justifyright', 'justifyfull', '|',
                'styleselect', 'formatselect', 'fontselect', 'fontsizeselect'
            ].join(','),
            theme_advanced_buttons2: [
                'cut', 'copy', 'paste', 'pastetext', 'pasteword', '|',
                'search', 'replace', '|',
                'bullist', 'numlist', '|',
                'outdent', 'indent', 'blockquote', '|',
                'undo', 'redo', '|',
                'link', 'unlink', 'anchor', 'image', 'cleanup', 'code', '|',
                'insertdate', 'inserttime', 'preview', '|',
                'forecolor', 'backcolor'
            ].join(','),
            theme_advanced_buttons3: [
                'tablecontrols', '|',
                'hr', 'removeformat', 'visualaid', '|',
                'sub', 'sup', '|',
                'charmap', 'emotions',
                'iespell', 'media', 'advhr', '|',
                'print', '|', 'ltr', 'rtl', '|',
                'fullscreen'
            ].join(','),
            theme_advanced_buttons4: [
                'insertlayer', 'moveforward', 'movebackward', 'absolute', '|',
                'styleprops', 'spellchecker', '|',
                'cite', 'abbr', 'acronym', 'del', 'ins', 'attribs', '|',
                'visualchars', 'nonbreaking', 'blockquote', 'pagebreak', '|',
                'insertfile', 'insertimage'
            ].join(','),
            theme_advanced_toolbar_location: 'top',
            theme_advanced_toolbar_align: 'left',
            theme_advanced_path_location: 'bottom',
            theme_advanced_resizing: true
        });

        editor.render();

        this._onPreValidate = function() {
            if (this._editor) {
                this._editor.save();
            }
        }.bind(this);

        element.on('html5-pre-validate', this._onPreValidate);

        creme.object.invoke(cb, element);
        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        if (this._editor) {
            this._editor.remove();
        }

        element.off('html5-pre-validate', this._onPreValidate);
    },

    editor: function(element) {
        return this._editor;
    }
});

}(jQuery));
