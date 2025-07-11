/* globals QUnitWidgetMixin QUnitDetailViewMixin */

(function($) {

QUnit.module("creme.detailview.hatmenubar", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitDialogMixin,
                                                           QUnitListViewMixin,
                                                           QUnitWidgetMixin,
                                                           QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        var selectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            reloadurl: 'mock/listview/reload/selection-list'
        }));

        this.setListviewReloadResponse(selectionListHtml, 'selection-list');

        this.setMockBackendGET({
            'mock/relation/selector': backend.response(200, selectionListHtml),
            'mock/show': backend.response(200, ''),
            'mock/form': backend.response(200, '<form></form>')
        });

        this.setMockBackendPOST({
            'mock/relation/add': backend.response(200, ''),
            'mock/update': backend.response(200, ''),
            'mock/delete': backend.response(200, ''),
            'mock/form': backend.response(200, '/mock/redirected')
        });

        $('body').attr('data-save-relations-url', 'mock/relation/add');
        $('body').attr('data-select-relations-objects-url', 'mock/relation/selector');
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.detailview.hatmenubar (empty)', function(assert) {
    var element = $(this.createHatMenuBarHtml()).appendTo(this.qunitFixture());

    element.on('hatmenubar-setup-actions', this.mockListener('hatmenubar-setup-actions'));

    var widget = creme.widget.create(element);
    var builder = widget.delegate._builder;

    assert.deepEqual([['hatmenubar-setup-actions', [builder]]], this.mockListenerJQueryCalls('hatmenubar-setup-actions'));
});

QUnit.test('creme.detailview.hatmenubar (no action)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: ['<a class="menu_button"/>']
    });

    this.assertActive(widget.element);
    this.assertReady(widget.element);

    assert.deepEqual([], widget.delegate._actionlinks);
});

QUnit.test('creme.detailview.hatmenubar (view)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/show',
                action: 'creme_core-hatmenubar-view'
            })
        ]
    });

    this.assertClosedDialog();

    this.assertActive(widget.element);
    this.assertReady(widget.element);

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedDialog();

    assert.deepEqual([
        ['mock/show', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.closeDialog();
    this.assertClosedDialog();
});

QUnit.test('creme.detailview.hatmenubar (confirm update)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/update',
                action: 'creme_core-hatmenubar-update',
                options: {
                    confirm: true
                },
                data: {
                    next: 'mock/next'
                }
            })
        ]
    });

    this.assertClosedDialog();

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedConfirmDialog(gettext('Are you sure?'));

    assert.deepEqual([], this.mockBackendUrlCalls());

    this.acceptConfirmDialog();

    assert.deepEqual([
        ['mock/update', 'POST', {next: 'mock/next'}]
    ], this.mockBackendUrlCalls());

    this.assertClosedDialog();
});

QUnit.test('creme.detailview.hatmenubar (form)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/form',
                action: 'creme_core-hatmenubar-form',
                options: {
                    redirectOnSuccess: false
                }
            })
        ]
    });

    this.assertClosedDialog();

    $(widget.element).find('a.menu_button').trigger('click');

    assert.deepEqual([['mock/form', 'GET', {}]], this.mockBackendUrlCalls());
    assert.deepEqual([], this.mockRedirectCalls());

    this.assertOpenedDialog();
    this.submitFormDialog();

    assert.deepEqual([
        ['mock/form', 'GET', {}],
        ['mock/form', 'POST', {}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual([], this.mockRedirectCalls());

    this.assertClosedDialog();
});

QUnit.test('creme.detailview.hatmenubar (form redirect)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/form',
                action: 'creme_core-hatmenubar-form'
            })
        ]
    });

    this.assertClosedDialog();

    $(widget.element).find('a.menu_button').trigger('click');

    assert.deepEqual([['mock/form', 'GET', {}]], this.mockBackendUrlCalls());
    assert.deepEqual([], this.mockRedirectCalls());

    this.assertOpenedDialog();
    this.submitFormDialog();

    assert.deepEqual([
        ['mock/form', 'GET', {}],
        ['mock/form', 'POST', {}]
    ], this.mockBackendUrlCalls());
    assert.deepEqual(['/mock/redirected'], this.mockRedirectCalls());

    this.assertClosedDialog();
});

QUnit.test('creme.detailview.hatmenubar (update-redirect)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/delete',
                action: 'creme_core-hatmenubar-update-redirect',
                options: {
                    confirm: 'Are you sure ?'
                },
                data: {
                    redirect: '/mock/delete/redirect'
                }
            })
        ]
    });

    this.assertActive(widget.element);
    this.assertReady(widget.element);

    assert.deepEqual(1, widget.delegate._actionlinks.length);

    var link = widget.delegate._actionlinks[0];
    assert.equal(true, link.isBound());
    assert.equal(false, link.isDisabled());

    $(widget.element).find('a.menu_button').trigger('click');

    this.assertOpenedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls('mock/delete'));
    assert.deepEqual([], this.mockRedirectCalls());

    this.acceptConfirmDialog();
    assert.deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/delete'));
    assert.deepEqual(['/mock/delete/redirect'], this.mockRedirectCalls());
});

QUnit.test('creme.detailview.hatmenubar (action registry)', function(assert) {
    var widget = this.createHatMenuBar();
    var registry = widget.delegate._builder;

    assert.ok(Object.isSubClassOf(registry, creme.component.FactoryRegistry));

    assert.ok(registry.has('creme_core-hatmenubar-view'));
    assert.ok(registry.has('creme_core-hatmenubar-update'));
    assert.ok(registry.has('creme_core-hatmenubar-form'));
    assert.ok(registry.has('creme_core-hatmenubar-update-redirect'));
});

}(jQuery));
