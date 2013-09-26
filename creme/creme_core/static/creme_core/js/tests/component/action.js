module("creme.component.action.js", {
    setup: function() {
        this.resetMockCalls();
    },

    teardown: function() {},

    resetMockCalls: function() {
        this._eventListenerCalls = [];
    },

    mockCallback: function(name)
    {
        var self = this;
        return (function(name) {return function() {
            self._eventListenerCalls.push([name, this].concat(Array.copy(arguments)));
        }})(name);
    },

    mockBindActionCallbacks: function(action)
    {
        var done = this.mockCallback('done_cb'),
            failed = this.mockCallback('fail_cb'),
            canceled = this.mockCallback('cancel_cb');

        return action.onCancel(canceled)
                     .onDone(done)
                     .onFail(failed);
    },

    mockAction: function()
    {
        var action = new creme.component.Action();
        var run = this.mockCallback('run_cb');

        return this.mockBindActionCallbacks(action.action(run));
    }
});

test('creme.component.Action (options)', function() {
    var action = new creme.component.Action();
    deepEqual({}, action.options());

    deepEqual(action, action.options({a:1, b:12}));
    deepEqual({a:1, b:12}, action.options());
});

test('creme.component.Action (start)', function() {
    var action = new creme.component.Action();
    var run = this.mockCallback('run_cb');

    equal(action.done, action.action());

    deepEqual(action, action.action(run));
    equal(run, action.action());

    deepEqual([], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['run_cb', action, {a:12}]], this._eventListenerCalls);
    equal('run', action.status());
    equal(true, action.isRunning());
});

test('creme.component.Action (start, extra args)', function() {
    var action = new creme.component.Action();
    var run = this.mockCallback('run_cb');

    action.action(run)
          .start({a:12}, 145, 'a');

    deepEqual([['run_cb', action, {a:12}, 145, 'a']], this._eventListenerCalls);
    equal('run', action.status());
    equal(true, action.isRunning());
});

test('creme.component.Action (start, default)', function() {
    var action = new creme.component.Action();
    var run = this.mockCallback('run_cb'),
        done = this.mockCallback('done_cb'),
        failed = this.mockCallback('fail_cb'),
        canceled = this.mockCallback('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed);

    equal(action.done, action.action());

    deepEqual([], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['done_cb', action, 'done', {a:12}]], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (start, constant)', function() {
    var action = new creme.component.Action();
    var run = this.mockCallback('run_cb'),
        done = this.mockCallback('done_cb'),
        failed = this.mockCallback('fail_cb'),
        canceled = this.mockCallback('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed)
          .action('constant');

    equal(true, Object.isFunc(action.action()));

    deepEqual([], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['done_cb', action, 'done', 'constant']], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (start, already running)', function() {
    var action = new creme.component.Action();
    var run = this.mockCallback('run_cb');

    equal(action.done, action.action());

    deepEqual(action, action.action(run));
    equal(run, action.action());

    deepEqual([], this._eventListenerCalls);
    equal('done', action.status());
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['run_cb', action, {a:12}]], this._eventListenerCalls);
    equal('run', action.status());
    equal(true, action.isRunning());

    action.start({b:15.8});

    deepEqual([['run_cb', action, {a:12}]], this._eventListenerCalls);
    equal('run', action.status());
    equal(true, action.isRunning());
});

test('creme.component.Action (done)', function() {
    var action = this.mockAction();

    deepEqual([], this._eventListenerCalls);
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['run_cb', action, {a:12}]], this._eventListenerCalls);
    equal(true, action.isRunning());

    action.done();

    deepEqual([['run_cb', action, {a:12}], ['done_cb', action, 'done']], this._eventListenerCalls);
    equal(false, action.isRunning());
});

test('creme.component.Action (done, parameter)', function() {
    var action = this.mockAction();

    deepEqual([], this._eventListenerCalls);
    equal(false, action.isRunning());

    action.start({a:12});

    deepEqual([['run_cb', action, {a:12}]], this._eventListenerCalls);
    equal(true, action.isRunning());

    action.done({b:153});

    deepEqual([['run_cb', action, {a:12}], ['done_cb', action, 'done', {b:153}]], this._eventListenerCalls);
    equal(false, action.isRunning());
});

test('creme.component.Action (done, not running)', function() {
    var action = this.mockAction();

    deepEqual([], this._eventListenerCalls);
    equal(false, action.isRunning());

    action.done();

    deepEqual([], this._eventListenerCalls);
    equal(false, action.isRunning());
});

test('creme.component.Action (fail)', function() {
    var action = this.mockAction();

    action.start();

    deepEqual([['run_cb', action]], this._eventListenerCalls);
    equal(true, action.isRunning());

    action.fail();

    deepEqual([['run_cb', action], ['fail_cb', action, 'fail']], this._eventListenerCalls);
    equal('fail', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (fail, run exception)', function() {
    var action = this.mockAction();
    var error = new Error('fail test !');

    action.action(function() {
                      throw error;
                  })
          .start();

    deepEqual([['fail_cb', action, 'fail', error]], this._eventListenerCalls);
    equal('fail', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (fail from action)', function() {
    var action = this.mockAction();

    action.action(function() {
                      this.fail('fail test', 145);
                  })
          .start();

    deepEqual([['fail_cb', action, 'fail', 'fail test', 145]], this._eventListenerCalls);
    equal('fail', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (cancel)', function() {
    var action = this.mockAction();

    action.start();

    deepEqual([['run_cb', action]], this._eventListenerCalls);
    equal(true, action.isRunning());

    action.cancel();

    deepEqual([['run_cb', action], ['cancel_cb', action, 'cancel']], this._eventListenerCalls);
    equal('cancel', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (cancel from action)', function() {
    var action = this.mockAction();

    action.action(function() {
                      this.cancel('cancel test', 8);
                  })
          .start();

    deepEqual([['cancel_cb', action, 'cancel', 'cancel test', 8]], this._eventListenerCalls);
    equal('cancel', action.status());
    equal(false, action.isRunning());
});

test('creme.component.Action (after)', function() {
    var first = this.mockBindActionCallbacks(new creme.component.Action());
    var second = this.mockBindActionCallbacks(new creme.component.Action());

    second.after(first)
          .action(function(value) {
                      if (value < 100) {
                          this.result = value * 10;
                          this.done(this.result);
                      } else {
                          this.fail(value);
                      }
                  });

    equal(undefined, second.result);
    equal(false, first.isRunning());
    equal(false, second.isRunning());

    deepEqual([], this._eventListenerCalls);

    first.action(12).start();

    deepEqual([['done_cb', first, 'done', 12], ['done_cb', second, 'done', 12 * 10]], this._eventListenerCalls);

    equal(12 * 10, second.result);
    equal('done', first.status());
    equal('done', second.status());

    second.result = undefined;
    this.resetMockCalls();

    first.action(115).start();

    deepEqual([['done_cb', first, 'done', 115], ['fail_cb', second, 'fail', 115]], this._eventListenerCalls);

    equal(undefined, second.result);
    equal('done', first.status());
    equal('fail', second.status());
});
