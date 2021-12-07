var project_config = require('../.karma.conf.js')

module.exports = function(config) {
    project_config(config);

    config.set({
        concurrency: 2,
        basePath: '../',
        browserConsoleLogOptions: {
            level: "critical",
            terminal: true
        },
        browsers: ['FirefoxHeadless', 'ChromeHeadless'],
        reporters: ['dots']
    });
};
