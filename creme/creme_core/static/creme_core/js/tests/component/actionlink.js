QUnit.module("creme.actionlink.js", new QUnitMixin(QUnitEventMixin, {
    beforeEach: function() {
        this.resetMockActionCalls();

        var actionCalls = this._mockActionCalls;
        var self = this;

        this.mockActionA = new creme.component.Action(function(options) {
            actionCalls.push('a');
            this.done();
        });

        this.mockActionB = new creme.component.Action(function(options) {
            actionCalls.push('b');
            this.done();
        });

        this.mockActionDoIt = new creme.component.Action(function(options) {
            actionCalls.push('do-it');
            this.done();
        });

        this.mockActionRaises = new creme.component.Action(function(options) {
            throw Error('this is an error !');
        });

        this.mockActionSlow = new creme.component.TimeoutAction({delay: 200});
        this.mockActionSlow.onDone(function() {
            actionCalls.push('slow');
        });

        this.mockActionBuilder = {
            _action_a: function(options) {
                return self.mockActionA;
            },
            _action_b: function(options) {
                return self.mockActionB;
            },
            _action_do_it: function(options) {
                return self.mockActionDoIt;
            },
            _action_raises: function(options) {
                return self.mockActionRaises;
            },
            _action_slow: function(options) {
                return self.mockActionSlow;
            },
            _action_none: function(options) {
                return null;
            }
        };
    },

    resetMockActionCalls: function() {
        this._mockActionCalls = [];
    },

    mockActionCalls: function() {
        return this._mockActionCalls;
    },

    mapLinkStartEventType: function(d) {
        var uievent = d.length > 4 ? d[4] : undefined;
        var data = d.slice(0, 4);

        if (uievent) {
            data.push(uievent.type);
        }

        return data;
    }
}));

QUnit.test('creme.action.ActionLink', function(assert) {
    var action = new creme.action.ActionLink();
    equal(false, action.isRunning());
    equal(false, action.isBound());
});

QUnit.test('creme.action.ActionLink (bind, no builder)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="a"></a>');

    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(true, link.is('.is-disabled'));
    equal(true, action.isDisabled());

    link.click();
    deepEqual([], this.mockActionCalls());
    deepEqual([['action-link-start']], this.mockListenerCalls('start'));
    deepEqual([['action-link-cancel', []]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, empty action)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .on('action-link-cancel', this.mockListener('cancel'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(true, link.is('.is-disabled'));
    equal(true, action.isDisabled());

    link.click();
    deepEqual([], this.mockActionCalls());
    deepEqual([['action-link-start']], this.mockListenerCalls('start'));
    deepEqual([['action-link-cancel', []]], this.mockListenerCalls('cancel'));
    deepEqual([['action-link-cancel', []]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, href)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="/actions/" data-action="a"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['a'], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionA]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, data-action-url)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['b'], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, actiontype with -)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="/actions/" data-action="do-it"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['do-it'], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, unknown actiontype)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="unknown"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link);

    equal(true, action.isBound());
    equal(true, link.is('.is-disabled'));
    equal(true, action.isDisabled());
});

QUnit.test('creme.action.ActionLink (bind, unknown actiontype, strict)', function(assert) {
    var action = new creme.action.ActionLink({strict: true});
    var link = $('<a data-action="unknown"/>');

    action.builders(this.mockActionBuilder);

    this.assertRaises(function() {
        action.bind(link);
    }, Error, 'Error: no such action "unknown"');

    equal(false, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());
});

QUnit.test('creme.action.ActionLink (bind, function builder)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="unknown"/>');
    var self = this;

    action.builders(function(actiontype) {
        return function() {
            return self.mockActionDoIt;
        }
    });
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['do-it'], this.mockActionCalls());
    deepEqual([['action-link-start', undefined, {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, action raises)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="raises"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'))

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual([], this.mockActionCalls());
    deepEqual([['action-link-start', undefined, {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-fail', [Error('this is an error !')], this.mockActionRaises]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, action none)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="none"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'))

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual([], this.mockActionCalls());
    deepEqual([], this.mockListenerCalls('start'));
    deepEqual([], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (already bound)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="a"/>');

    action.builders(this.mockActionBuilder);
    action.bind(link);

    this.assertRaises(function() {
        action.bind(link);
    }, Error, 'Error: action link is already bound');
});

QUnit.test('creme.action.ActionLink (bind, data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"><script datatype="text/json">{"data": 23}</script></span>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['b'], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, 23, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, invalid data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"><script datatype="text/json">{"data": 23}}}</script></span>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    link.click();
    deepEqual(['b'], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (ignore click while running)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="slow"></span>');

    action.builders(this.mockActionBuilder);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    equal(true, action.isBound());
    equal(false, link.is('.is-disabled'));
    equal(false, action.isDisabled());

    equal(false, action.isRunning());

    link.click();
    equal(true, action.isRunning());
    deepEqual([], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([], this.mockListenerCalls('complete'));

    link.click();
    equal(true, action.isRunning());
    deepEqual([], this.mockActionCalls());
    deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    deepEqual([], this.mockListenerCalls('complete'));

    stop(1);

    var mockActionCalls = this.mockActionCalls.bind(this);
    var mockListenerCalls = this.mockListenerCalls.bind(this);
    var mockActionSlow = this.mockActionSlow;
    var mapLinkStartEventType = this.mapLinkStartEventType.bind(this);

    setTimeout(function() {
        equal(false, action.isRunning());
        deepEqual(['slow'], mockActionCalls());
        deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], mockListenerCalls('start').map(mapLinkStartEventType));
        deepEqual([['action-link-done', [{delay: 200}], mockActionSlow]], mockListenerCalls('complete'));
        start();
    }, 300);
});
