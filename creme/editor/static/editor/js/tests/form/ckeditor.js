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

    equal(false, element.is('.creme-ckeditor-hidden'));
    equal('', element.attr('id') || '');

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(true, element.is('.creme-ckeditor-hidden'));
        equal(true, element.attr('id').startsWith('creme-ckeditor__'));

        equal(element, editor.element());
        equal(editor.ckeditor(), element.data('ck-editor'));
    });
});

QUnit.test('creme.form.CKEditor (create, id)', function(assert) {
    var element = $(this.createEditorHtml({id: 'my_textarea'})).appendTo(this.qunitFixture('field'));

    equal(false, element.is('.creme-ckeditor-hidden'));

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(true, element.is('.creme-ckeditor-hidden'));
        equal('my_textarea', element.attr('id'));

        equal(element, editor.element());
        equal(editor.ckeditor(), element.data('ck-editor'));
    });
});

QUnit.test('creme.form.CKEditor (destroy)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));

    equal(false, element.is('.creme-ckeditor-hidden'));

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(true, element.is('.creme-ckeditor-hidden'));
        equal(element, editor.element());
        equal(editor.ckeditor(), element.data('ck-editor'));

        editor.destroy();

        equal(false, element.is('.creme-ckeditor-hidden'));
        equal(null, editor.ckeditor());
        equal(null, editor.ckeditorSetup());
        equal(true, Object.isNone(element.data('ck-editor')));
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
        equal(enabled, element.parent().find('.ck-file-dialog-button input[type="file"]').length > 0);
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
        equal(enabled, element.parent().find('.ck-placeholder-dropdown').length > 0);
    });
});

QUnit.parameterize('creme.form.CKEditor (maxWidth)', [
    ['200px', 200],
    ['fit-input', 300]
], function(maxWidth, expected, assert) {
    var element = $(this.createEditorHtml({maxWidth: maxWidth})).css('width', '300px').appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(expected, element.parent().find('.ck.ck-editor').width());
    });
});

QUnit.parameterize('creme.form.CKEditor (maxHeight)', [
    ['200px', '200px'],
    ['fit-input', '300px'],
    ['fit-rows', '13em']
], function(minHeight, expected, assert) {
    var element = $(this.createEditorHtml({minHeight: minHeight}));
    element.css('height', '300px')
           .attr('rows', 13)
           .appendTo(this.qunitFixture('field'));

    equal(element.data('ckeditorHeight'), minHeight);

    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(expected, element.parent().find('.ck.ck-editor').height());
    });
});

QUnit.test('creme.form.CKEditor (updateSourceDelay, no delay)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 0});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal('', element.val());
        editor.insertHtml('<p>Test!</p>');

        setTimeout(function() {
            equal('<p>Test!</p>', element.val());
            start();
        });

        stop(1);
    });
});

QUnit.test('creme.form.CKEditor (updateSourceDelay)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 300});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal('', element.val());
        editor.insertHtml('<p>Test!</p>');

        setTimeout(function() {
            equal('', element.val());
            start();
        }, 100);

        setTimeout(function() {
            equal('<p>Test!</p>', element.val());
            start();
        }, 350);

        stop(2);
    });
});

QUnit.test('creme.form.CKEditor (insertHtml)', function(assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {updateSourceDelay: 0});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal('', element.val());

        editor.insertHtml('<p>Test!</p>');

        this.awaits(50, function() {
            equal('<p>Test!</p>', element.val());
            editor.insertHtml('<b>Another</b>', 0);
        });

        this.awaits(100, function() {
            equal('<p>Test!<strong>Another</strong></p>', element.val());
        });
    });
});

QUnit.parameterize('creme.form.CKEditor ([disabled])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({disabled: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(state, editor.isDisabled());
        equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        equal(!state, editor.isDisabled());
        equal(!state, element.prop('disabled'));
    });
});


QUnit.parameterize('creme.form.CKEditor (disabled)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {isDisabled: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(state, editor.isDisabled());
        equal(state, element.prop('disabled'));

        editor.isDisabled(!state);

        equal(!state, editor.isDisabled());
        equal(!state, element.prop('disabled'));
    });
});


QUnit.parameterize('creme.form.CKEditor ([readonly])', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml({readonly: state})).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(state, editor.isReadOnly());
        equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        equal(!state, editor.isReadOnly());
        equal(!state, element.prop('readonly'));
    });
});


QUnit.parameterize('creme.form.CKEditor (readonly)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {isReadOnly: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(state, editor.isReadOnly());
        equal(state, element.prop('readonly'));

        editor.isReadOnly(!state);

        equal(!state, editor.isReadOnly());
        equal(!state, element.prop('readonly'));
    });
});

QUnit.parameterize('creme.form.CKEditor (hideDisabledToolbar)', [true, false], function(state, assert) {
    var element = $(this.createEditorHtml()).appendTo(this.qunitFixture('field'));
    var editor = new creme.form.CKEditor(element, {hideDisabledToolbar: state});

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        var toolbar = element.parent().find('.ck-toolbar');

        equal(1, toolbar.length);
        equal(false, editor.isReadOnly());
        equal(state, editor.hideDisabledToolbar());
        equal(false, toolbar.is('.ck-hide-toolbar'));

        editor.isReadOnly(true);
        equal(state, toolbar.is('.ck-hide-toolbar'));
    });
});

}(jQuery));
