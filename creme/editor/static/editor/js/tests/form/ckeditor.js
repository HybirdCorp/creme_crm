(function($) {

QUnit.module("creme.form.CKEditor", new QUnitMixin(QUnitAjaxMixin,
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
        $('.creme-ckeditor-hidden').each(function() {
            var editor = $(this).data('ck-editor');
            if (editor) {
                editor.destroy();
            }
        });
    },

    createEditorHtml: function(options) {
        options = options || {};

        return '<textarea ${id} ${uploadURL} ${maxWidth} ${minHeight} ${disabled} ${readonly}></textarea>'.template({
            id: options.id ? 'id="${id}"'.template(options) : '',
            uploadURL: options.uploadURL ? 'data-ckeditor-upload="${uploadURL}"'.template(options) : '',
            maxWidth: options.maxWidth ? 'data-ckeditor-max-width="${maxWidth}"'.template(options) : '',
            minHeight: options.minHeight ? 'data-ckeditor-height="${minHeight}"'.template(options) : '',
            disabled: options.disabled ? 'disabled' : '',
            readonly: options.readonly ? 'readonly' : ''
        });
    }
}));

QUnit.test('creme.form.CKEditor (create, no id)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-ckeditor-hidden'));
    assert.equal('', element.attr('id') || '');

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(true, element.is('.creme-ckeditor-hidden'));
        assert.equal(true, element.attr('id').startsWith('creme-ckeditor__'));

        assert.equal(element, editor.element());
        assert.equal(editor.ckeditor(), element.data('ck-editor'));
    });
});

QUnit.test('creme.form.CKEditor (create, id)', function(assert) {
    var element = $(this.createEditorHtml({id: 'my_textarea'})).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-ckeditor-hidden'));

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(true, element.is('.creme-ckeditor-hidden'));
        assert.equal('my_textarea', element.attr('id'));

        assert.equal(element, editor.element());
        assert.equal(editor.ckeditor(), element.data('ck-editor'));
    });
});

QUnit.test('creme.form.CKEditor (destroy)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    assert.equal(false, element.is('.creme-ckeditor-hidden'));

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(true, element.is('.creme-ckeditor-hidden'));
        assert.equal(element, editor.element());
        assert.equal(editor.ckeditor(), element.data('ck-editor'));

        editor.destroy();

        assert.equal(false, element.is('.creme-ckeditor-hidden'));
        assert.equal(null, editor.ckeditor());
        assert.equal(null, editor.ckeditorSetup());
        assert.equal(true, Object.isNone(element.data('ck-editor')));
    });
});

QUnit.test('creme.form.CKEditor (already bound)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        this.assertRaises(function() {
            return new creme.form.CKEditor(element);
        }, Error, 'Error: CkEditor instance is already active');
    });
});

QUnit.test('creme.form.CKEditor (invalid toolbar)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    this.assertRaises(function() {
        return new creme.form.CKEditor(element, {toolbar: 'unknown'});
    }, Error, 'Error: CkEditor toolbar "unknown" does not exist');
});

QUnit.test('creme.form.CKEditor (empty toolbar)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {toolbar: []});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        var toolbar = element.parent().find('.ck-toolbar');

        assert.equal(1, toolbar.length);
        assert.equal(false, editor.isReadOnly());
        assert.equal(false, editor.hideDisabledToolbar());
        assert.equal(true, toolbar.is('.ck-hide-toolbar'));  // Hidden anyway to prevent rendering glitch
    });
});

QUnit.parameterize('creme.form.CKEditor (upload)', [
    ['', false],
    ['mock/upload', true]
], function(url, enabled, assert) {
    var element = $(this.createEditorHtml({uploadURL: url})).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {
        toolbarExtra: ['imageupload']
    });

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(enabled, element.parent().find('.ck-file-dialog-button input[type="file"]').length > 0);
    });
});

QUnit.parameterize('creme.form.CKEditor (placeholder)', [
    [[], false],
    [[{name: 'id', label: 'Identifier', help: 'An identifier tag'}], true]
], function(placeholders, enabled, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {
        toolbar: 'template',
        placeholders: placeholders
    });

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(enabled, element.parent().find('.ck-placeholder-dropdown').length > 0);
    });
});

QUnit.parameterize('creme.form.CKEditor (maxWidth)', [
    ['200px', 200],
    ['fit-input', 300]
], function(maxWidth, expected, assert) {
    var element = $(this.createEditorHtml({maxWidth: maxWidth})).css('width', '300px').appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(expected, element.parent().find('.ck.ck-editor').width());
    });
});

QUnit.parameterize('creme.form.CKEditor (minHeight)', [
    ['200px', '200px'],
    ['fit-input', '300px'],
    ['fit-rows', '13em']
], function(minHeight, expected, assert) {
    var element = $(this.createEditorHtml({minHeight: minHeight}));
    element.css('height', '300px')
           .attr('rows', 13)
           .appendTo(this.qunitFixture('field'));

    assert.equal(element.data('ckeditorHeight'), minHeight);

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(
            'min-height:${height};'.template({height: expected}),
            element.parent().find('.ck.ck-editor .ck-content').attr('style')
        );
    });
});

QUnit.test('creme.form.CKEditor (updateSourceDelay, no delay)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 0});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal('', element.val());
        editor.insertHtml('<p>Test!</p>');

        var done = assert.async();

        setTimeout(function() {
            assert.equal('<p>Test!</p>', element.val());
            done();
        });
    });
});

QUnit.test('creme.form.CKEditor (updateSourceDelay)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 300});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal('', element.val());
        editor.insertHtml('<p>Test!</p>');

        var done = assert.async(2);

        setTimeout(function() {
            assert.equal('', element.val());
            done();
        }, 100);

        setTimeout(function() {
            assert.equal('<p>Test!</p>', element.val());
            done();
        }, 350);
    });
});

QUnit.test('creme.form.CKEditor (insertHtml)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 0});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
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

QUnit.parameterize('creme.form.CKEditor ([disabled])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({disabled: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(state, editor.isDisabled());
        assert.equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        assert.equal(!state, editor.isDisabled());
        assert.equal(!state, element.prop('disabled'));
    });
});


QUnit.parameterize('creme.form.CKEditor (disabled)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {isDisabled: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(state, editor.isDisabled());
        assert.equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        assert.equal(!state, editor.isDisabled());
        assert.equal(!state, element.prop('disabled'));
    });
});


QUnit.parameterize('creme.form.CKEditor ([readonly])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({readonly: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(state, editor.isReadOnly());
        assert.equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        assert.equal(!state, editor.isReadOnly());
        assert.equal(!state, element.prop('readonly'));
    });
});


QUnit.parameterize('creme.form.CKEditor (readonly)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {isReadOnly: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        assert.equal(state, editor.isReadOnly());
        assert.equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        assert.equal(!state, editor.isReadOnly());
        assert.equal(!state, element.prop('readonly'));
    });
});

QUnit.parameterize('creme.form.CKEditor (hideDisabledToolbar)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {hideDisabledToolbar: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        var toolbar = element.parent().find('.ck-toolbar');

        assert.equal(1, toolbar.length);
        assert.equal(false, editor.isReadOnly());
        assert.equal(state, editor.hideDisabledToolbar());
        assert.equal(false, toolbar.is('.ck-hide-toolbar'));

        editor.isReadOnly(true);
        assert.equal(state, toolbar.is('.ck-hide-toolbar'));
    });
});

}(jQuery));
