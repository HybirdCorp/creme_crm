(function($) {

QUnit.module("creme.TinyMCEditor", new QUnitMixin(QUnitAjaxMixin,
                                                  QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/upload': backend.responseJSON(200, {})
        });

        this.setMockBackendPOST({
            'mock/upload': backend.responseJSON(200, {})
        });
    },

    afterEach: function() {
        $('.creme-tinymce-hidden').each(function() {
            var editor = $(this).data('tiny-editor');
            if (!!editor && !editor.removed) {
                editor.remove();
            }
        });
    },

    createEditorHtml: function(options) {
        options = options || {};
        var baseURL = this.qunitUserAgent() ? '/tiny_mce/8.3.2/' : '/base/tiny_mce/8.3.2/';

        return '<textarea ${id} ${args} ${baseURL} ${disabled} ${readonly}></textarea>'.template({
            id: options.id ? 'id="${id}"'.template(options) : '',
            args: [
                options.uploadURL ? 'data-upload-url="${uploadURL}"'.template(options) : '',
                options.uploadField ? 'data-upload-field="${uploadField}"'.template(options) : '',
                options.width ? 'data-editor-width="${width}"'.template(options) : '',
                options.minWidth ? 'data-editor-min-width="${minWidth}"'.template(options) : '',
                options.maxWidth ? 'data-editor-max-width="${maxWidth}"'.template(options) : '',
                options.height ? 'data-editor-height="${height}"'.template(options) : '',
                options.minHeight ? 'data-editor-min-height="${minHeight}"'.template(options) : '',
                options.maxHeight ? 'data-editor-max-height="${maxHeight}"'.template(options) : ''
            ].join(' '),
            disabled: options.disabled ? 'disabled' : '',
            readonly: options.readonly ? 'readonly' : '',
            baseURL: 'data-base-url="${baseURL}"'.template({baseURL: baseURL})
        });
    }
}));

QUnit.test('creme.TinyMCEditor (create, no id)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-tinymce-hidden'));
    assert.equal('', element.attr('id') || '');

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(true, element.is('.creme-tinymce-hidden'));
        assert.equal(true, element.attr('id').startsWith('creme-tinymce__'));

        assert.equal(element, editor.element());
        assert.equal(editor.editor(), element.data('tiny-editor'));
    });
});

QUnit.test('creme.TinyMCEditor (create, id)', function(assert) {
    var element = $(this.createEditorHtml({id: 'my_textarea'})).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-tinymce-hidden'));

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(true, element.is('.creme-tinymce-hidden'));
        assert.equal('my_textarea', element.attr('id'));

        assert.equal(element, editor.element());
        assert.equal(editor.editor(), element.data('tiny-editor'));
    });
});

QUnit.test('creme.TinyMCEditor (destroy)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-tinymce-hidden'));

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(true, element.is('.creme-tinymce-hidden'));
        assert.equal(element, editor.element());
        assert.equal(editor.editor(), element.data('tiny-editor'));

        editor.destroy();

        assert.equal(false, element.is('.creme-tinymce-hidden'));
        assert.equal(null, editor.editor());
        assert.equal(null, editor.editorSetup());
        assert.equal(true, Object.isNone(element.data('tiny-editor')));
    });
});

QUnit.test('creme.TinyMCEditor (already bound)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        this.assertRaises(function() {
            return new creme.TinyMCEditor(element);
        }, Error, 'Error: TinyMCE instance is already active');
    });
});

QUnit.test('creme.TinyMCEditor (invalid toolbar)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    this.assertRaises(function() {
        return new creme.TinyMCEditor(element, {toolbar: 'unknown'});
    }, Error, 'Error: TinyMCEditor toolbar "unknown" does not exist');
});

QUnit.test('creme.TinyMCEditor (empty toolbar)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element, {toolbar: []});

    this.awaitsPromise(editor.editorSetup(), function() {
        var toolbar = element.parent().find('.tox-toolbar__primary');

        assert.equal(1, toolbar.length);
        assert.equal(false, editor.isReadOnly());
        // assert.equal(false, editor.hideDisabledToolbar());
        assert.equal('', toolbar.html());
    });
});

QUnit.test('creme.TinyMCEditor (empty menubar)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element, {menubar: []});

    this.awaitsPromise(editor.editorSetup(), function() {
        var menubar = element.parent().find('.tox-menubar');

        assert.equal(1, menubar.length);
        assert.equal(false, editor.isReadOnly());
        // assert.equal(false, editor.hideDisabledToolbar());
        assert.equal('', menubar.html());
    });
});

QUnit.parameterize('creme.TinyMCEditor (upload)', [
   ['', false],
   ['mock/upload', true]
], function(url, enabled, assert) {
   var element = $(this.createEditorHtml({uploadURL: url})).appendTo(this.qunitFixture('field'));
   var editor = new creme.TinyMCEditor(element, {
       toolbar: ['image']
   });

   this.awaitsPromise(editor.editorSetup(), function() {
       assert.equal(enabled, element.parent().find('[data-mce-name="image"][type="button"]').length > 0);
   });
});

QUnit.parameterize('creme.TinyMCEditor (maxWidth)', [
    ['200px', 200],
    ['fit-input', 300]
], function(maxWidth, expected, assert) {
    var element = $(this.createEditorHtml({maxWidth: maxWidth})).css('width', '300px').appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    assert.equal(element.data('editorMaxWidth'), maxWidth);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(expected, element.parent().find('.tox.tox-tinymce').outerWidth());
    });
});

QUnit.parameterize('creme.TinyMCEditor (minWidth)', [
    ['200px', 200],
    ['fit-input', 100]
], function(minWidth, expected, assert) {
    var element = $(this.createEditorHtml({minWidth: minWidth})).css('width', '100px').appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    assert.equal(element.data('editorMinWidth'), minWidth);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(expected, element.parent().find('.tox.tox-tinymce').outerWidth());
    });
});

QUnit.parameterize('creme.TinyMCEditor (width)', [
    ['200px', 200],
    ['fit-input', 300]
], function(width, expected, assert) {
    var element = $(this.createEditorHtml({width: width})).css('width', '300px').appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    assert.equal(element.data('editorWidth'), width);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(expected, element.parent().find('.tox.tox-tinymce').outerWidth());
    });
});

/*
QUnit.parameterize('creme.TinyMCEditor (height)', [
    ['200px', '200px'],
    ['fit-input', '300px'],
    ['fit-rows', '13em']
], function(height, expected, assert) {
    var element = $(this.createEditorHtml({height: height}));
    element.css('height', '300px')
           .attr('rows', 13)
           .appendTo(this.qunitFixture('field'));

    assert.equal(element.data('editorHeight'), height);

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(
            'visibility:hidden;height:${height};'.template({height: expected}),
            element.parent().find('.tox.tox-tinymce').attr('style')
        );
    });
});

QUnit.parameterize('creme.TinyMCEditor (minHeight)', [
    ['200px', 200],
    ['fit-input', 300],
    ['fit-rows', 13 * 13]
], function(minHeight, expected, assert) {
    var element = $(this.createEditorHtml({minHeight: minHeight}));
    element.css('height', '300px')
           .css('font-size', '13px')
           .attr('rows', 13)
           .appendTo(this.qunitFixture('field'));

    assert.equal(element.data('editorMinHeight'), minHeight);

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(
            'visibility:hidden;height:${height};'.template({height: expected}),
            element.parent().find('.tox.tox-tinymce').attr('style')
        );
    });
});

QUnit.parameterize('creme.TinyMCEditor (maxHeight)', [
    ['200px', 200],
    ['fit-input', 300],
    ['fit-rows', 13 * 13]
], function(maxHeight, expected, assert) {
    var element = $(this.createEditorHtml({maxHeight: maxHeight}));
    element.css('height', '300px')
           .css('font-size', '13px')
           .attr('rows', 13)
           .appendTo(this.qunitFixture('field'));

    assert.equal(element.data('editorMaxHeight'), maxHeight);

    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(
            'visibility:hidden;height:${height};'.template({height: expected}),
            element.parent().find('.tox.tox-tinymce').attr('style')
        );
    });
});
*/

// QUnit.test('creme.TinyMCEditor (updateSourceDelay, no delay)', function(assert) {
//    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
//    var editor = new creme.TinyMCEditor(element, {updateSourceDelay: 0});
//
//    this.awaitsPromise(editor.editorSetup(), function() {
//        assert.equal('', element.val());
//        editor.insertHtml('<p>Test!</p>');
//
//        var done = assert.async();
//
//        setTimeout(function() {
//            assert.equal('<p>Test!</p>', element.val());
//            done();
//        });
//    });
// });

// QUnit.test('creme.TinyMCEditor (updateSourceDelay)', function(assert) {
//    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
//    var editor = new creme.TinyMCEditor(element, {updateSourceDelay: 300});
//
//    this.awaitsPromise(editor.editorSetup(), function() {
//        assert.equal('', element.val());
//        editor.insertHtml('<p>Test!</p>');
//
//        var done = assert.async(2);
//
//        setTimeout(function() {
//            assert.equal('', element.val());
//            done();
//        }, 100);
//
//        setTimeout(function() {
//            assert.equal('<p>Test!</p>', element.val());
//            done();
//        }, 350);
//    });
// });

QUnit.test('creme.TinyMCEditor (insertHtml)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element, {updateSourceDelay: 0});

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal('', element.val());

        editor.insertHtml('<p>Test!</p>');

        this.awaits(50, function() {
            assert.equal('<p>Test!</p>', element.val());
            editor.insertHtml('<b>Another</b>', 0);
        });

        this.awaits(100, function() {
            assert.equal('<p>Test!<strong>Another</strong></p>', element.val());
        });
    });
});

QUnit.parameterize('creme.TinyMCEditor ([disabled])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({disabled: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(state, editor.isDisabled());
        assert.equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        assert.equal(!state, editor.isDisabled());
        assert.equal(!state, element.prop('disabled'));
    });
});

QUnit.parameterize('creme.TinyMCEditor (disabled)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element, {isDisabled: state});

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(state, editor.isDisabled());
        assert.equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        assert.equal(!state, editor.isDisabled());
        assert.equal(!state, element.prop('disabled'));
    });
});

QUnit.parameterize('creme.TinyMCEditor ([readonly])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({readonly: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element);

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(state, editor.isReadOnly());
        assert.equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        assert.equal(!state, editor.isReadOnly());
        assert.equal(!state, element.prop('readonly'));
    });
});

QUnit.parameterize('creme.TinyMCEditor (readonly)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.TinyMCEditor(element, {isReadOnly: state});

    this.awaitsPromise(editor.editorSetup(), function() {
        assert.equal(state, editor.isReadOnly());
        assert.equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        assert.equal(!state, editor.isReadOnly());
        assert.equal(!state, element.prop('readonly'));
    });
});

// QUnit.parameterize('creme.TinyMCEditor (hideDisabledToolbar)', [true, false], function(state, assert) {
//    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
//    var editor = new creme.TinyMCEditor(element, {hideDisabledToolbar: state});
//
//    this.awaitsPromise(editor.editorSetup(), function() {
//        var toolbar = element.parent().find('.ck-toolbar');
//
//        assert.equal(1, toolbar.length);
//        assert.equal(false, editor.isReadOnly());
//        assert.equal(state, editor.hideDisabledToolbar());
//        assert.equal(false, toolbar.is('.ck-hide-toolbar'));
//
//        editor.isReadOnly(true);
//        assert.equal(state, toolbar.is('.ck-hide-toolbar'));
//    });
// });

}(jQuery));
