/* globals QUnitWidgetMixin */

(function($) {

var MOCK_CREATE_FORM = '<form action="mock/create/popup">' +
                           '<input name="value" type="text"></input>' +
                           '<input name="name" type="text"></input>' +
                           '<input type="submit" class="ui-creme-dialog-action"></input>' +
                       '</form>';

QUnit.module("creme.widget.actionlist.js", new QUnitMixin(QUnitAjaxMixin,
                                                          QUnitEventMixin,
                                                          QUnitDialogMixin,
                                                          QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({
            sync: true, name: 'creme.widget.actionlist.js'
        });
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/options': backend.responseJSON(200, [[15, 'a'], [5, 'b'], [3, 'c'], [14, 't'], [42, 'y']]),
            'mock/rtype/1/options': backend.responseJSON(200, [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]),
            'mock/rtype/5/options': backend.responseJSON(200, [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]),
            'mock/create/popup': backend.response(200, MOCK_CREATE_FORM),
            'mock/create/popup/fail': backend.response(400, 'HTTP - Error 400'),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/create/popup': function(url, data, options) {
                var name = data.name[0];
                var value = data.value ? data.value[0] : "";

                if (Object.isEmpty(name)) {
                    return backend.responseJSON(200, {});
                } else {
                    return backend.responseJSON(200, {value: value, added: [[value, name]]});
                }
            }
        });
    },

    createActionListTag: function(options) {
        options = $.extend({
            options: {},
            delegate: $('<div></div>'),
            noauto: false,
            buttons: []
        }, options || {});

        var list = $((
            '<ul class="ui-creme-widget ui-creme-actionbuttonlist ${auto}" ${attrs} widget="ui-creme-actionbuttonlist"></ul>'
        ).template({
            auto: options.noauto ? '' : 'widget-auto',
            attrs: Object.entries(options.options || {}).map(function(opt) {
                return '${0}="${1}"'.template(opt);
            }).join(' ')
        }));

        list.append($('<li class="delegate" />').append(options.delegate));

        var createActionButtonHtml = this.createActionButtonHtml.bind(this);

        options.buttons.forEach(function(button) {
            list.append('<li>${button}</li>'.template({
                button: createActionButtonHtml(button)
            }));
        });

        return list;
    },

    appendActionButton: function(element, button) {
        element.append($('<li/>').append(button));
    },

    createActionButtonHtml: function(options) {
        options = $.extend({
            attrs: {},
            disabled: false
        }, options || {});

        return (
            '<button type="button" name="${name}" title="${label}" class="ui-creme-actionbutton with-icon" ${disabled} ${attrs}>' +
                '<img width="16px"></img>' +
                '<span>${label}</span>' +
            '</button>'
        ).template({
            name: options.name,
            label: options.label || options.name,
            url: options.url || '',
            disabled: options.disabled ? 'disabled="disabled"' : '',
            attrs: this.htmlAttrs(options.attrs)
        });
    }
}));

QUnit.test('creme.widgets.actionlist.create (no delegate, no action)', function(assert) {
    var element = this.createActionListTag();
    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), '');
    assert.equal(widget.selector().length, 0);
    assert.equal(widget.actionButtons().length, 0);
    assert.deepEqual(widget.dependencies(), []);
});

QUnit.test('creme.widgets.actionlist.create (no delegate)', function(assert) {
    var element = this.createActionListTag({
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), '');
    assert.equal(widget.selector().length, 0);
    assert.equal(widget.actionButtons().length, 1);
    assert.deepEqual(widget.dependencies(), []);
});

QUnit.parametrize('creme.widgets.actionlist.create (initial state)', [
    [{}, {disabled: true, label: gettext('Add')}],
    [{popupTitle: 'Create It !'}, {disabled: true, label: 'Create It !'}],
    [{popupUrl: 'mock/create/popup'}, {disabled: false, label: gettext('Add')}],
    [{popupUrl: 'mock/create/popup', popupTitle: 'Create It !'}, {disabled: false, label: 'Create It !'}]
], function(buttonAttrs, expected, assert) {
    var delegate = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', label: 'Create', attrs: buttonAttrs}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.selector().length, 1);
    assert.equal(widget.actionButtons().length, 1);

    assert.equal(widget.val(), 1);
    assert.deepEqual(widget.dependencies(), []);

    assert.equal(delegate.hasClass('widget-active'), true);
    assert.equal(delegate.hasClass('widget-ready'), true);

    assert.equal(delegate.creme().widget().val(), 1);
    assert.deepEqual(delegate.creme().widget().dependencies(), []);

    assert.equal(widget.actionButton('create').find('img').length, 1);
    assert.equal(widget.actionButton('create').is('[disabled]'), false);
    assert.equal(widget.actionButton('create').find('span').text(), 'Create');

    widget.reload();

    assert.equal(widget.actionButton('create').find('img').length, 1);
    assert.equal(widget.actionButton('create').is('[disabled]'), expected.disabled);
    assert.equal(widget.actionButton('create').find('span').text(), expected.label);
});

QUnit.test('creme.widgets.actionlist.create (disabled actionlist, html)', function(assert) {
    var delegate = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        options: {
            disabled: true
        },
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}}
        ]
    });

    assert.equal(element.is('[disabled]'), true);
    assert.equal(delegate.is('[disabled]'), false);

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.selector().length, 1);

    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);
    assert.equal(widget.selector().is('[disabled]'), true);

    assert.equal(2, widget.actionButtons().length);
    assert.equal(widget.actionButton('create').is('[disabled]'), true);
    assert.equal(widget.actionButton('create').find('img').length, 1);
    assert.equal(widget.actionButton('create').find('span').text(), 'create');

    assert.equal(widget.actionButton('reset').is('[disabled]'), true);
    assert.equal(widget.actionButton('reset').find('img').length, 1);
});

QUnit.test('creme.widgets.actionlist.create (disabled actionlist, option)', function(assert) {
    var delegate = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}}
        ]
    });

    assert.equal(element.is('[disabled]'), false);
    assert.equal(delegate.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true, backend: this.backend});

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.selector().length, 1);

    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);
    assert.equal(widget.selector().is('[disabled]'), true);

    assert.equal(2, widget.actionButtons().length);
    assert.equal(widget.actionButton('create').is('[disabled]'), true);
    assert.equal(widget.actionButton('reset').is('[disabled]'), true);
});

QUnit.test('creme.widgets.actionlist.create (disabled action)', function(assert) {
    var delegate = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}, disabled: true}
        ]
    });

    assert.equal(element.is('[disabled]'), false);
    assert.equal(delegate.is('[disabled]'), false);

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.selector().length, 1);
    assert.equal(widget.actionButtons().length, 2);

    assert.equal(element.is('[disabled]'), false);
    assert.equal(widget.delegate._enabled, true);
    assert.equal(widget.selector().is('[disabled]'), false);

    assert.equal(widget.actionButton('create').is('[disabled]'), false);
    assert.equal(widget.actionButton('reset').is('[disabled]'), true);
});

QUnit.test('creme.widgets.actionlist.dependencies (url delegate)', function(assert) {
    var delegate = $(this.createSelectHtml({
        url: 'mock/${ctype}/options'
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.deepEqual(delegate.creme().widget().dependencies(), ['ctype']);
    assert.deepEqual(widget.dependencies(), ['ctype']);
});

// TODO : add dependency support for actions
/*
QUnit.test('creme.widgets.actionlist.dependencies (url actions)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        url: 'mock/${ctype}/options'
    }));
    this.appendOptionTag(delegate, 'a', 1);
    this.appendOptionTag(delegate, 'b', 5);
    this.appendOptionTag(delegate, 'c', 3);

    var element = this.createActionListTag()
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/${rtype}/popup', enabled: true});

    var widget = creme.widget.create(element, {backend: this.backend});
    assert.deepEqual(delegate.creme().widget().dependencies(), ['ctype']);
    assert.deepEqual(widget.dependencies(), ['ctype', 'rtype']);
});
*/

QUnit.test('creme.widgets.actionlist.value', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(delegate.val(), 1);
    assert.equal(widget.val(), 1);

    widget.val(5);
    assert.equal(delegate.val(), 5);
    assert.equal(widget.val(), 5);

    widget.val(15);
    assert.equal(delegate.val(), 1);
    assert.equal(widget.val(), 1);
});

QUnit.test('creme.widgets.actionlist.url', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        url: 'mock/${ctype}/options',
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});
    var delegateWidget = delegate.creme().widget();

    assert.deepEqual(delegateWidget.dependencies(), ['ctype']);
    assert.deepEqual(widget.dependencies(), ['ctype']);

    assert.equal(null, delegateWidget.url());
    assert.equal(null, widget.url());

    delegateWidget.reload({ctype: 'ctype.1'});

    assert.equal('mock/ctype.1/options', delegateWidget.url());
    assert.equal('mock/ctype.1/options', widget.url());

    widget.url('mock/${rtype}/other/${ctype}/options');

    assert.deepEqual(delegateWidget.dependencies(), ['rtype', 'ctype']);
    assert.deepEqual(widget.dependencies(), ['rtype', 'ctype']);

    assert.equal(null, delegateWidget.url());
    assert.equal(null, widget.url());

    delegateWidget.reload({ctype: 'ctype.1', rtype: 'rtype.74'});

    assert.equal('mock/rtype.74/other/ctype.1/options', delegateWidget.url());
    assert.equal('mock/rtype.74/other/ctype.1/options', widget.url());
});

QUnit.test('creme.widgets.actionlist.reset', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 12, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    assert.equal(delegate.val(), 5);
    assert.equal(widget.val(), 5);

    // reset with widget instance
    widget.reset();
    assert.equal(delegate.val(), 12);
    assert.equal(widget.val(), 12);
});

QUnit.test('creme.widgets.actionlist.reset (button click)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 12, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    widget.val(5);
    assert.equal(delegate.val(), 5);
    assert.equal(widget.val(), 5);

    // reset with button
    widget.actionButton('reset').trigger('click');
    assert.equal(delegate.val(), 12);
    assert.equal(widget.val(), 12);
});

QUnit.test('creme.widgets.actionlist.reload', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.val(), 1);
    assert.deepEqual(widget.dependencies(), []);

    element.creme().widget().url('mock/options');
    this.assertDSelect(delegate, '15', [], 'mock/options', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);

    assert.equal(widget.val(), 15);
    assert.deepEqual(widget.dependencies(), []);

    element.creme().widget().url('mock/rtype/${ctype}/options');
    element.creme().widget().reload({ctype: 5});

    this.assertDSelect(delegate, 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    assert.equal(widget.val(), 'rtype.7');
    assert.deepEqual(widget.dependencies(), ['ctype']);
});

QUnit.test('creme.widgets.actionlist.action (popup, canceled)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('create').trigger('click');

    this.assertOpenedDialog();
    this.closeDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([
        ['actionListCanceled']
    ], this.mockListenerJQueryCalls('actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (popup, fail)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup/fail'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('create').trigger('click');

    this.assertOpenedDialog();
    this.closeDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([
        ['actionListCanceled']
    ], this.mockListenerJQueryCalls('actionlist-cancel'));
});


QUnit.test('creme.widgets.actionlist.action (popup, empty url)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: ''}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('create').trigger('click');

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([
        ['actionListCanceled']
    ], this.mockListenerJQueryCalls('actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (popup, success)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('create').trigger('click');

    this.assertOpenedDialog();
    this.submitFormDialog({
        value: 42,
        name: 'other'
    });

    this.assertClosedDialog();

    assert.equal(4, delegate.find('option').length);
    assert.equal('42', delegate.val());
    assert.deepEqual([
        ['actionListSuccess', [{value: '42', added: [['42', 'other']]}]]
    ], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (unknow action)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'unknown', attrs: {action: 'unknown'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('unknown').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('unknown').trigger('click');

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([
        ['actionListCanceled']
    ], this.mockListenerJQueryCalls('actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (disabled action)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup', disabled: true}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), true);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.actionButton('create').trigger('click');

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (doAction, button)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}},
            {name: 'reset', attrs: {action: 'reset'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 2, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.equal('1', delegate.val());

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.doAction('create', {
        done: this.mockListener('one-actionlist-success'),
        cancel: this.mockListener('one-actionlist-cancel')
    });

    this.assertOpenedDialog();
    this.submitFormDialog({
        value: 42,
        name: 'other'
    });

    this.assertClosedDialog();

    assert.equal(4, delegate.find('option').length);
    assert.equal('42', delegate.val());

    assert.deepEqual([
        ['actionListSuccess', [{value: '42', added: [['42', 'other']]}]]
    ], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    assert.deepEqual([
        ['done', {value: '42', added: [['42', 'other']]}]
    ], this.mockListenerCalls('one-actionlist-success'));
    assert.deepEqual([], this.mockListenerCalls('one-actionlist-cancel'));

    widget.doAction('reset');
    assert.equal(4, delegate.find('option').length);
    assert.equal('1', delegate.val());

    assert.deepEqual([
        ['actionListSuccess', [{value: '42', added: [['42', 'other']]}]],
        ['actionListSuccess', [{value: ''}]]
    ], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    assert.deepEqual([
        ['done', {value: '42', added: [['42', 'other']]}]
    ], this.mockListenerCalls('one-actionlist-success'));
    assert.deepEqual([], this.mockListenerCalls('one-actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (doAction, disabled buttons)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup', disabled: true}},
            {name: 'reset', attrs: {action: 'reset', disabled: true}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 2, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), true);
    assert.equal(widget.actionButton('reset').is('[disabled]'), true);

    this.assertClosedDialog();

    assert.equal(3, delegate.find('option').length);
    assert.equal('1', delegate.val());

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    widget.doAction('create', {
        done: this.mockListener('one-actionlist-success'),
        cancel: this.mockListener('one-actionlist-cancel')
    });

    this.assertOpenedDialog();
    this.submitFormDialog({
        value: 42,
        name: 'other'
    });

    this.assertClosedDialog();

    assert.equal(4, delegate.find('option').length);
    assert.equal('42', delegate.val());

    assert.deepEqual([
        ['actionListSuccess', [{value: '42', added: [['42', 'other']]}]]
    ], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    assert.deepEqual([
        ['done', {value: '42', added: [['42', 'other']]}]
    ], this.mockListenerCalls('one-actionlist-success'));
    assert.deepEqual([], this.mockListenerCalls('one-actionlist-cancel'));

    widget.doAction('reset');
    assert.equal(4, delegate.find('option').length);
    assert.equal('1', delegate.val());

    assert.deepEqual([
        ['actionListSuccess', [{value: '42', added: [['42', 'other']]}]],
        ['actionListSuccess', [{value: ''}]]
    ], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));

    assert.deepEqual([
        ['done', {value: '42', added: [['42', 'other']]}]
    ], this.mockListenerCalls('one-actionlist-success'));
    assert.deepEqual([], this.mockListenerCalls('one-actionlist-cancel'));
});

QUnit.test('creme.widgets.actionlist.action (doAction, delegate)', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    delegate.on('action', this.mockListener('action'));

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
    assert.deepEqual([], this.mockListenerCalls('action'));

    widget.doAction('delegate-action');

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
    assert.deepEqual([
        ['action', ['delegate-action', {}]]
    ], this.mockListenerJQueryCalls('action'));
});


QUnit.test('creme.widgets.actionlist.action (trigger delegate "action")', function(assert) {
    var delegate = $(this.createSelectHtml({
        auto: false,
        noEmpty: true,
        choices: [
            {value: 1, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var element = this.createActionListTag({
        delegate: delegate,
        buttons: [
            {name: 'create', attrs: {popupUrl: 'mock/create/popup'}}
        ]
    }).on({
        actionListSuccess: this.mockListener('actionlist-success'),
        actionListCanceled: this.mockListener('actionlist-cancel')
    });

    delegate.on('action', this.mockListener('action'));

    var widget = creme.widget.create(element, {backend: this.backend});

    assert.equal(widget.actionButtons().length, 1, 'action count');
    assert.equal(widget.actionButton('create').is('[disabled]'), false);

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
    assert.deepEqual([], this.mockListenerCalls('action'));

    element.trigger('action', ['delegate-action']);

    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-success'));
    assert.deepEqual([], this.mockListenerJQueryCalls('actionlist-cancel'));
    assert.deepEqual([
        ['action', ['delegate-action', {}]]
    ], this.mockListenerJQueryCalls('action'));
});


}(jQuery));
