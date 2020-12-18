(function($) {
"use strict";

QUnit.module("creme.component.action-feedback.js", new QUnitMixin(QUnitEventMixin,
                                                                  QUnitAjaxMixin, {
    beforeEach: function() {
        this.mockFeedbackListeners = {
            done: this.mockListener('done'),
            fail: this.mockListener('fail'),
            cancel: this.mockListener('cancel')
        };

        this.mockFeedbackRegistry = new creme.component.FactoryRegistry();
        this.mockFeedbackRegistry.registerAll({
            'redirect': function (url) {
                return new creme.component.Action(function() {
                    creme.utils.goTo(url);
                    this.done();
                });
            },
            'do-it': function(url, options, data) {
                return new creme.component.Action(function() {
                    this.done(data);
                });
            },
            'fail-it': function(url, options, data) {
                return new creme.component.Action(function() {
                    this.fail(data);
                });
            },
            'raise-it': function(url) {
                throw new Error('invalid action !');
            },
            'cancel-it': function(url, options, data) {
                return new creme.component.Action(function() {
                    this.cancel(data);
                });
            }
        });
    }
}));

QUnit.test('creme.action.FeedbackAction (no command)', function(assert) {
    var action = new creme.action.FeedbackAction();
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        done: [['done']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (single command, unknown)', function(assert) {
    var action = new creme.action.FeedbackAction({command: 'unknown'});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        fail: [['fail', {command: 'unknown'}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (single command, fail)', function(assert) {
    var action = new creme.action.FeedbackAction({command: 'fail-it'},
                                                 {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        fail: [['fail', {}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (single command, cancel)', function(assert) {
    var action = new creme.action.FeedbackAction({command: 'cancel-it'},
                                                 {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        cancel: [['cancel', {}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (single command, error)', function(assert) {
    var action = new creme.action.FeedbackAction({command: 'raise-it'},
                                                 {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        fail: [['fail', {command: 'raise-it'}, Error('invalid action !')]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (single command, ok)', function(assert) {
    var action = new creme.action.FeedbackAction({command: 'redirect', data: {url: 'mock/redirect'}},
                                                 {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        done: [['done']]
    }, this.mockListenerCalls());

    deepEqual(['mock/redirect'], this.mockRedirectCalls());
});

QUnit.test('creme.action.FeedbackAction (N commands, fail)', function(assert) {
    var action = new creme.action.FeedbackAction([
        {command: 'do-it', data: {a: 1}},
        {command: 'fail-it', data: {a: 2}},
        {command: 'do-it', data: {a: 3}}
    ], {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual([
        ['fail', {a: 2}]
    ], this.mockListenerCalls('fail').map(function(e) { return e.slice(0, 2); }));
});

QUnit.test('creme.action.FeedbackAction (N commands, unknown)', function(assert) {
    var action = new creme.action.FeedbackAction([
        {command: 'do-it', data: {a: 1}},
        {command: 'unknown', data: {a: 2}},
        {command: 'do-it', data: {a: 3}}
    ], {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        fail: [['fail', {command: 'unknown', data: {a: 2}}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.action.FeedbackAction (N commands, cancel)', function(assert) {
    var action = new creme.action.FeedbackAction([
        {command: 'do-it', data: {a: 1}},
        {command: 'cancel-it', data: {a: 2}},
        {command: 'do-it', data: {a: 3}}
    ], {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual([
        ['cancel', {a: 2}]
    ], this.mockListenerCalls('cancel').map(function(e) { return e.slice(0, 2); }));
});

QUnit.test('creme.action.FeedbackAction (N commands, ok)', function(assert) {
    var action = new creme.action.FeedbackAction([
        {command: 'do-it', data: {a: 1}},
        {command: 'do-it', data: {a: 2}},
        {command: 'do-it', data: {a: 3}}
    ], {builders: this.mockFeedbackRegistry});
    action.on(this.mockFeedbackListeners);

    action.start();

    deepEqual({
        done: [['done', {a: 3}]]
    }, this.mockListenerCalls());
});

}(jQuery));
