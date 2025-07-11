/* global QUnitDetailViewMixin */

(function($) {
QUnit.module("creme.billing.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitBrickMixin,
                                                           QUnitDialogMixin,
                                                           QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/billing/document/add': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/billing/saveall': backend.response(200, ''),
            'mock/billing/saveall/fail': backend.response(400, 'Unable to save lines'),
            'mock/invoice/generatenumber/12': backend.response(200, ''),
            'mock/invoice/generatenumber/12/fail': backend.response(400, 'Unable to generate invoice number'),
            'mock/quote/convert/12': backend.response(200, 'mock/quote/invoice', {'content-type': 'text/plain'}),
            'mock/quote/convert/12/fail': backend.response(400, 'Unable to convert this quote'),
            'mock/billing/document/add': backend.response(200, '')
        });

        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    },

    createBillingLineHtml: function(options, index) {
        var renderInput = function(options) {
            options = $.extend({
                validator: "Decimal"
            }, options || {});

            return (
                '<td class="bline-${name}">' +
                     '<input type="text" value="${value}" validator="${validator}"' +
                           ' name="product_line_formset-${index}-${name}" id="product_line_formset-${index}-${name}">' +
                     '</input>' +
                '</td>').template({
                    value: options.value,
                    name: options.name,
                    index: index,
                    validator: options.validator
                });
        };

        return (
           '<div class="bline-container ${classes} ${hidden}">' +
                '<div class="bline-buttons ${deletion}"></div>' +
                '<div class="bline-fields">' +
                    '<table class="linetable"><tr class="content">${inputs}</tr></table>' +
                '</div>' +
           '</div>').template({
               inputs: (options.inputs || []).map(renderInput).join(''),
               classes: (options.classes || []).join(' '),
               deletion: options.deleted ? 'bline-deletion-mark' : ''
           });
    },

    createBillingBrick: function(options) {
        options = $.extend({
            classes: ['billing-lines-brick'],
            ctype: '86'
        }, options || {});

        var header = (
            '<div class="brick-header-buttons">${buttons}</div>'
        ).template({
            buttons: (options.buttons || []).map(this.createBrickActionHtml.bind(this)).join('')
        });

        var content = (
            '<div class="bline-content">' +
                '<div class="bline-form" ct_id="${ctype}" id="form_id_${ctype}">${lines}</div>' +
            '</div>').template({
                lines: (options.lines || []).map(this.createBillingLineHtml.bind(this)).join(''),
                ctype: options.ctype
            });

        return this.createBrickWidget({
            classes: options.classes,
            content: content,
            header: header
        });
    }
}));

QUnit.test('creme.billing.brick (available actions)', function(assert) {
    var brick = this.createBillingBrick().brick();

    assert.equal(true, Object.isSubClassOf(brick.action('billing-line-addonfly'), creme.component.Action));
    assert.equal(true, Object.isSubClassOf(brick.action('billing-line-saveall'), creme.component.Action));
    assert.equal(true, Object.isSubClassOf(brick.action('billing-line-clearonfly'), creme.component.Action));
});

QUnit.test('creme.billing.brick (billing-line-saveall, invalid input)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    assert.ok(creme.billing.formsHaveErrors());

    brick.action('billing-line-saveall', 'mock/billing/saveall').on(this.brickActionListeners).start();

    this.assertOpenedAlertDialog(gettext('There are some errors in your lines.'));
    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/billing/saveall'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-saveall, invalid response)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    brick.element().find('#product_line_formset-0-quantity').val('5').trigger('change');
    brick.element().find('#product_line_formset-0-product').val('Product #1').trigger('change');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, creme.billing.modifiedBLineForms().length);

    brick.action('billing-line-saveall', 'mock/billing/saveall/fail').on(this.brickActionListeners).start();

    assert.deepEqual([
        ['POST', {
            '86': JSON.stringify({'product_line_formset-0-quantity': '5', 'product_line_formset-0-product': 'Product #1'})
         }]
    ], this.mockBackendUrlCalls('mock/billing/saveall/fail'));

    this.assertOpenedAlertDialog('Unable to save lines');
    this.closeDialog();

    assert.deepEqual([['fail', 'Unable to save lines']], this.mockListenerCalls('action-fail'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-saveall, no changes)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]}
        ]
    }).brick();

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(0, creme.billing.modifiedBLineForms().length);

    brick.action('billing-line-saveall', 'mock/billing/saveall').on(this.brickActionListeners).start();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/billing/saveall'));

    this.assertClosedDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-saveall, ok)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    brick.element().find('#product_line_formset-0-quantity').val('5').trigger('change');
    brick.element().find('#product_line_formset-0-product').val('Product #1').trigger('change');

    assert.equal(false, creme.billing.formsHaveErrors());

    brick.action('billing-line-saveall', 'mock/billing/saveall').on(this.brickActionListeners).start();

    assert.deepEqual([
        ['POST', {
            '86': JSON.stringify({'product_line_formset-0-quantity': '5', 'product_line_formset-0-product': 'Product #1'})
         }]
    ], this.mockBackendUrlCalls('mock/billing/saveall'));

    this.assertClosedDialog();

    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));
    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-addonfly)', function(assert) {
    var brick = this.createBillingBrick({
        buttons: [{
                classes: ['brick-header-button action-type-add'],
                action: 'billing-line-addonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }],
        lines: [{
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]
            }, {
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}],
                classes: ['hidden-form empty_form_${ctype} empty_form_inputs_${ctype}'.template({ctype: 86})]
            }]
    }).brick();

    var addonflyLink = brick.element().find('[data-action="billing-line-addonfly"]');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, brick.element().find('.hidden-form').length);
    assert.equal(false, addonflyLink.is('.forbidden'));

    addonflyLink.trigger('click');

    assert.equal(true, creme.billing.formsHaveErrors());
    assert.equal(0, brick.element().find('.hidden-form').length);
    assert.equal(true, addonflyLink.is('.forbidden'));
});

QUnit.test('creme.billing.brick (billing-line-addonfly, forbidden)', function(assert) {
    var brick = this.createBillingBrick({
        buttons: [{
                classes: ['brick-header-button action-type-add forbidden'],
                action: 'billing-line-addonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }],
        lines: [{
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]
            }, {
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}],
                classes: ['hidden-form empty_form_${ctype} empty_form_inputs_${ctype}'.template({ctype: 86})]
            }]
    }).brick();

    var addonflyLink = brick.element().find('[data-action="billing-line-addonfly"]');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, brick.element().find('.hidden-form').length);
    assert.equal(true, addonflyLink.is('.forbidden'));

    addonflyLink.trigger('click');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, brick.element().find('.hidden-form').length);
    assert.equal(true, addonflyLink.is('.forbidden'));
});

QUnit.test('creme.billing.brick (billing-line-clearonfly)', function(assert) {
    var brick = this.createBillingBrick({
        buttons: [{
                classes: ['brick-header-button action-type-add'],
                action: 'billing-line-addonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }, {
                classes: ['brick-header-button action-type-delete'],
                action: 'billing-line-clearonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }],
        lines: [{
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]
            }, {
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}],
                classes: ['hidden-form empty_form_${ctype} empty_form_inputs_${ctype}'.template({ctype: 86})]
            }]
    }).brick();

    var addonflyLink = brick.element().find('[data-action="billing-line-addonfly"]');
    var clearonflyLink = brick.element().find('[data-action="billing-line-clearonfly"]');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, brick.element().find('.hidden-form').length);
    assert.equal(false, addonflyLink.is('.forbidden'));

    addonflyLink.trigger('click');

    assert.equal(true, creme.billing.formsHaveErrors());
    assert.equal(0, brick.element().find('.hidden-form').length);
    assert.equal(true, addonflyLink.is('.forbidden'));

    clearonflyLink.trigger('click');

    assert.equal(false, creme.billing.formsHaveErrors());
    assert.equal(1, brick.element().find('.hidden-form').length);
    assert.equal(false, addonflyLink.is('.forbidden'));
});

QUnit.test('creme.billing.AddDocumentAction', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var action = new creme.billing.AddDocumentAction({
        url: 'mock/billing/document/add'
    }).on({
        'cancel': this.mockListener('action-cancel'),
        'done': this.mockListener('action-done')
    });

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['GET', {}],
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.AddDocumentAction (deps)', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    this.createBrickWidget({
        id: 'brick-for-test-A',
        deps: ['A', 'B']
    }).brick();

    this.createBrickWidget({
        id: 'brick-for-test-B',
        deps: ['C']
    }).brick();

    var action = new creme.billing.AddDocumentAction({
        url: 'mock/billing/document/add',
        deps: ['creme_core.relation', 'C']
    }).on({
        'cancel': this.mockListener('action-cancel'),
        'done': this.mockListener('action-done')
    });

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();
    assert.deepEqual([['done']], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['GET', {}],
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test", "brick-for-test-B"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.AddDocumentAction (cancel)', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    var action = new creme.billing.AddDocumentAction({
        url: 'mock/billing/document/add'
    }).on({
        'cancel': this.mockListener('action-cancel'),
        'done': this.mockListener('action-done')
    });

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-cancel'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.closeDialog();
    this.assertClosedDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.hatmenubar.billing-hatmenubar-add-document', function(assert) {
    this.createBrickWidget({
        deps: ['creme_core.relation']
    }).brick();

    this.createBrickWidget({
        id: 'creme_core-test1',
        deps: ['A', 'B']
    }).brick();

    this.createBrickWidget({
        id: 'my_app-test2',
        deps: ['creme_core.relation.rtype-C', 'my_app-modelA']
    }).brick();

    this.createBrickWidget({
        id: 'my_app-related_modelA',
        deps: ['my_app-modelA']
    }).brick();

    var widget = this.createButtonsBrick({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/billing/document/add',
                action: 'billing-hatmenubar-add-document',
                data: {
                    rtype_id: ['rtype-C'],
                    model_id: ['my_app-modelA']
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    this.submitFormDialog();

    this.assertClosedDialog();

    assert.deepEqual([
        ['GET', {}],
        ['POST', {}]
    ], this.mockBackendUrlCalls('mock/billing/document/add'));

    assert.deepEqual([
        ['GET', {"brick_id": ["creme_core-test", "my_app-test2", "my_app-related_modelA"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.hatmenubar.billing-hatmenubar-add-document (with redirection)', function(assert) {
    var creationURL = 'mock/billing/document/add';
    var quoteURL = 'mock/quote/12';

    var POSTBackends = {};  // TODO:  {[creationURL]: ...}  when IE is dead
    POSTBackends[creationURL] = this.backend.response(200, quoteURL);
    this.setMockBackendPOST(POSTBackends);

    var widget = this.createButtonsBrick({
        buttons: [
            this.createHatMenuActionButton({
                url: creationURL + '?redirection=true',
                action: 'billing-hatmenubar-add-document',
                data: {
                    rtype_id: ['rtype-C'],
                    model_id: ['model-A']
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').trigger('click');


    assert.deepEqual([
        ['GET', {"redirection": "true"}]
    ], this.mockBackendUrlCalls(creationURL));

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockListenerCalls('action-done'));

    this.submitFormDialog();
    this.assertClosedDialog();

    assert.deepEqual([
        ['GET', {"redirection": "true"}],
        ['POST', {
            "URI-SEARCH": {"redirection": "true"}
        }]
    ], this.mockBackendUrlCalls(creationURL));
    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
    assert.deepEqual([quoteURL], this.mockRedirectCalls());
});

}(jQuery));
