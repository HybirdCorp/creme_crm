(function($) {
QUnit.module("creme.component.action.js", new QUnitMixin(QUnitEventMixin, {
    mockBindActionListeners: function(action) {
        var done = this.mockListener('done_cb'),
            failed = this.mockListener('fail_cb'),
            canceled = this.mockListener('cancel_cb');

        return action.onCancel(canceled)
                     .onDone(done)
                     .onFail(failed);
    },

    mockAction: function() {
        var action = new creme.component.Action();
        var run = this.mockListener('run_cb');

        return this.mockBindActionListeners(action.action(run));
    }
}));

QUnit.test('creme.component.Action (options)', function(assert) {
    var action = new creme.component.Action();
    deepEqual({}, action.options());

    deepEqual(action, action.options({a: 1, b: 12}));
    deepEqual({a: 1, b: 12}, action.options());

    equal(false, action.isRunning());
    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    equal(action.done, action.action());

    deepEqual(action, action.action(run));
    equal(run, action.action());

    deepEqual({}, this.mockListenerCalls());
    equal('done', action.status());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());

    action.start({a: 12});

    deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    equal('run', action.status());
    equal(true, action.isRunning());
});

QUnit.test('creme.component.Action (start, extra args)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    action.action(run)
          .start({a: 12}, 145, 'a');

    deepEqual({
        'run_cb': [[{a: 12}, 145, 'a']]
    }, this.mockListenerCalls());

    equal('run', action.status());
    equal(true, action.isRunning());

    equal(false, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, default)', function(assert) {
    var action = new creme.component.Action();
    var done = this.mockListener('done_cb'),
        failed = this.mockListener('fail_cb'),
        canceled = this.mockListener('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed);

    equal(action.done, action.action());

    deepEqual({}, this.mockListenerCalls());
    equal('done', action.status());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());

    action.start({a: 12});

    deepEqual({
        'done_cb': [['done', {a: 12}]]
    }, this.mockListenerCalls());

    equal('done', action.status());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, constant)', function(assert) {
    var action = new creme.component.Action();
    var done = this.mockListener('done_cb'),
        failed = this.mockListener('fail_cb'),
        canceled = this.mockListener('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed)
          .action('constant');

    equal(true, Object.isFunc(action.action()));

    deepEqual({}, this.mockListenerCalls());
    equal('done', action.status());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());

    action.start({a: 12});

    deepEqual({
        'done_cb': [['done', 'constant']]
    }, this.mockListenerCalls());

    equal('done', action.status());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, already running)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    equal(action.done, action.action());

    deepEqual(action, action.action(run));
    equal(run, action.action());

    deepEqual({}, this.mockListenerCalls());
    equal('done', action.status());
    equal(false, action.isRunning());

    action.start({a: 12});

    deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    equal('run', action.status());
    equal(true, action.isRunning());

    action.start({b: 15.8});

    deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    equal('run', action.status());
    equal(true, action.isRunning());
});

QUnit.test('creme.component.Action (done)', function(assert) {
    var action = this.mockAction();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());

    action.start({a: 12});

    deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    equal(true, action.isRunning());

    action.done();

    deepEqual({
        'run_cb': [[{a: 12}]],
        'done_cb': [['done']]
    }, this.mockListenerCalls());

    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (done, parameter)', function(assert) {
    var action = this.mockAction();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());

    action.start({a: 12});

    deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    equal(true, action.isRunning());

    action.done({b: 153});

    deepEqual({
        'run_cb': [[{a: 12}]],
        'done_cb': [['done', {b: 153}]]
    }, this.mockListenerCalls());

    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (done, not running)', function(assert) {
    var action = this.mockAction();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());

    action.done();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (fail)', function(assert) {
    var action = this.mockAction();

    action.start();

    deepEqual({
        'run_cb': [[]]
    }, this.mockListenerCalls());

    equal(true, action.isRunning());

    action.fail();

    deepEqual({
        'run_cb': [[]],
        'fail_cb': [['fail']]
    }, this.mockListenerCalls());

    equal('fail', action.status());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (fail, not running)', function(assert) {
    var action = this.mockAction();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());

    action.fail();

    deepEqual({}, this.mockListenerCalls());
    equal(false, action.isRunning());

    equal(true, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (fail, run exception)', function(assert) {
    var action = this.mockAction();
    var error = new Error('fail test !');

    action.action(function() {
                      throw error;
                  })
          .start();

    deepEqual({
        'fail_cb': [['fail', error]]
    }, this.mockListenerCalls());

    equal('fail', action.status());
    equal(false, action.isRunning());

    equal(false, action.isStatusDone());
    equal(true, action.isStatusFail());
    equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (fail from action)', function(assert) {
    var action = this.mockAction();

    action.action(function() {
                      this.fail('fail test', 145);
                  })
          .start();

    deepEqual({
        'fail_cb': [['fail', 'fail test', 145]]
    }, this.mockListenerCalls());

    equal('fail', action.status());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (cancel)', function(assert) {
    var action = this.mockAction();

    action.start();

    deepEqual({
        'run_cb': [[]]
    }, this.mockListenerCalls());

    equal(true, action.isRunning());

    action.cancel();

    deepEqual({
        'run_cb': [[]],
        'cancel_cb': [['cancel']]
    }, this.mockListenerCalls());

    equal('cancel', action.status());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (cancel from action)', function(assert) {
    var action = this.mockAction();

    action.action(function() {
                      this.cancel('cancel test', 8);
                  })
          .start();

    deepEqual({
        'cancel_cb': [['cancel', 'cancel test', 8]]
    }, this.mockListenerCalls());

    equal('cancel', action.status());
    equal(false, action.isRunning());

    equal(false, action.isStatusDone());
    equal(false, action.isStatusFail());
    equal(true, action.isStatusCancel());
});

QUnit.test('creme.component.Action (onStart)', function(assert) {
    var action = this.mockAction();

    action.onStart(this.mockListener('start_cb'))
          .action(function() {
                      this.done('ok');
                  })
          .start('start test', 4);

    deepEqual({
        'start_cb': [['start', 'start test', 4]],
        'done_cb': [['done', 'ok']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.component.Action (trigger)', function(assert) {
    var action = this.mockAction();

    action.on('event1', this.mockListener('1'));
    action.action(function() {
                      this.trigger('event1', 2);
                      this.done();
                  })
          .start();

    deepEqual({
        '1': [['event1', 2]],
        'done_cb': [['done']]
    }, this.mockListenerCalls());

    equal('done', action.status());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (off event)', function(assert) {
    var action = this.mockAction();

    action.off('done');
    action.on('event1', this.mockListener('1'));
    action.action(function() {
                      this.trigger('event1', 2);
                      this.done();
                  })
          .start();

    deepEqual({
        '1': [['event1', 2]]
    }, this.mockListenerCalls());

    equal('done', action.status());
    equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (delegate)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    equal(false, delegate.isRunning());
    equal(false, action.isRunning());

    deepEqual({}, this.mockListenerCalls());

    delegate.action(12).start();

    deepEqual({
        'done_cb': [['done', 12], ['done', 12]]
    }, this.mockListenerCalls());

    equal('done', delegate.status());
    equal('done', action.status());
});

QUnit.test('creme.component.Action (delegate, cancel)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    equal(false, delegate.isRunning());
    equal(false, action.isRunning());

    deepEqual({}, this.mockListenerCalls());

    delegate.action(function() {
        this.cancel('canceled !');
    }).start();

    deepEqual({
        'cancel_cb': [['cancel', 'canceled !'], ['cancel', 'canceled !']]
    }, this.mockListenerCalls());

    equal('cancel', delegate.status());
    equal('cancel', action.status());
});

QUnit.test('creme.component.Action (delegate, fail)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    equal(false, delegate.isRunning());
    equal(false, action.isRunning());

    deepEqual({}, this.mockListenerCalls());

    delegate.action(function() {
        this.fail('failed !');
    }).start();

    deepEqual({
        'fail_cb': [['fail', 'failed !'], ['fail', 'failed !']]
    }, this.mockListenerCalls());

    equal('fail', delegate.status());
    equal('fail', action.status());
});

QUnit.test('creme.component.Action (after)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first)
          .action(function(value) {
                      this.result = value * 10;
                      this.done(this.result);
                  });

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.action(12).start();
    deepEqual({
        'done_cb': [['done', 12], ['done', NaN]]
    }, this.mockListenerCalls());

    equal(true, isNaN(second.result));
    equal('done', first.status());
    equal('done', second.status());
});

QUnit.test('creme.component.Action (after, passArgs)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first, {passArgs: true})
          .action(function(value) {
                      this.result = value * 10;
                      this.done(this.result);
                  });

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.action(12).start();
    deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    equal(12 * 10, second.result);
    equal('done', first.status());
    equal('done', second.status());
});

QUnit.test('creme.component.Action (after, invalid)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    this.assertRaises(function() {
        second.after({});
    }, Error, 'Error: This is not an action instance');

    deepEqual([], second.stack());
    deepEqual([], first.stack());

    second.after(first);

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    this.assertRaises(function() {
        second.after(first);
    }, Error, 'Error: Action is already after');

    deepEqual([first], second.stack());
    deepEqual([], first.stack());
});

QUnit.test('creme.component.Action (after, second fail)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first, {passArgs: true})
          .action(function(value) {
                      this.fail(value);
                  });

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.action(115).start();

    deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    equal(undefined, second.result);
    equal('done', first.status());
    equal('fail', second.status());
});

QUnit.test('creme.component.Action (after, first fail)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    first.action(function(value) {
        this.fail(value);
    });

    second.after(first, {passArgs: true});

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.start(115);

    deepEqual({
        'fail_cb': [['fail', 115], ['fail', 115]]
    }, this.mockListenerCalls());

    equal('fail', first.status());
    equal('fail', second.status());
});

QUnit.test('creme.component.Action (after, first cancel)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    first.action(function(value) {
        this.cancel(value);
    });

    second.after(first, {passArgs: true});

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.start(115);

    deepEqual({
        'cancel_cb': [['cancel', 115], ['cancel', 115]]
    }, this.mockListenerCalls());

    equal('cancel', first.status());
    equal('cancel', second.status());
});

QUnit.test('creme.component.Action (listen, after alias)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.listen(first, {passArgs: true})
          .action(function(value) {
                      if (value < 100) {
                          this.result = value * 10;
                          this.done(this.result);
                      } else {
                          this.fail(value);
                      }
                  });

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.action(12).start();

    deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    equal(12 * 10, second.result);
    equal('done', first.status());
    equal('done', second.status());

    second.result = undefined;
    this.resetMockListenerCalls();

    first.action(115).start();

    deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    equal(undefined, second.result);
    equal('done', first.status());
    equal('fail', second.status());
});

QUnit.test('creme.component.Action (before)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.action(function(value) {
                      if (value < 100) {
                          this.result = value * 10;
                          this.done(this.result);
                      } else {
                          this.fail(value);
                      }
                  });

    first.before(second, {passArgs: true});

    deepEqual([first], second.stack());
    deepEqual([], first.stack());

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual({}, this.mockListenerCalls());

    first.action(12).start();

    deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    equal(12 * 10, second.result);
    equal('done', first.status());
    equal('done', second.status());

    second.result = undefined;
    this.resetMockListenerCalls();

    first.action(115).start();

    deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    equal(undefined, second.result);
    equal('done', first.status());
    equal('fail', second.status());
});

QUnit.test('creme.component.TimeoutAction (zero delay)', function(assert) {
    var action = this.mockBindActionListeners(new creme.component.TimeoutAction({delay: 0}));
    action.start();

    // stops immediately
    equal(false, action.isRunning());
    equal('done', action.status());

    deepEqual({
        'done_cb': [['done', {delay: 0}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.component.TimeoutAction (200ms delay)', function(assert) {
    var timeout = this.mockBindActionListeners(new creme.component.TimeoutAction({delay: 200}));
    var action = this.mockBindActionListeners(new creme.component.Action());
    var mockListenerCalls = this.mockListenerCalls.bind(this);

    timeout.before(action).start();

    equal(true, timeout.isRunning());
    equal(false, action.isRunning());
    deepEqual({}, this.mockListenerCalls());

    stop(1);

    setTimeout(function() {
        equal(false, timeout.isRunning());
        equal(false, action.isRunning());

        deepEqual({
            'done_cb': [['done', {delay: 200}], ['done']]
        }, mockListenerCalls());

        start();
    }, 300);
});

}(jQuery));
