var path = require('path');

var BUILD_TOOLS = path.join(process.env.SPLUNK_SOURCE, 'web', 'build_tools');
var mergeConfigs = require(path.join(BUILD_TOOLS, 'util', 'mergeConfigs'));
var appPageConfig = require(path.join(BUILD_TOOLS, 'profiles', 'common', 'namespacedAppPages.config'));
var createBabelLoader = require(path.join(BUILD_TOOLS, 'util', 'createBabelLoader'));
var appDir = path.join(__dirname, '..');
var appName = path.basename(appDir);

module.exports = function(options) {
    options = { loadTheme: 'lite', ...options };
    return mergeConfigs(appPageConfig(appDir, appName, options), {
        output:{
            path: path.join(appDir, 'appserver', 'static', 'build', 'pages', 'lite')
        },
        module: {
            rules: [
            createBabelLoader({
                test: /\.es$/,
                include: /splunk_monitoring_console/,
                presets: ['babel-preset-es2015'],
            }),
            createBabelLoader({
                test: /\.jsx$/,
                include: /splunk_monitoring_console/,
                presets: ['babel-preset-es2015', 'babel-preset-react'],
            }),
            ]
        }
    });
}
