var path = require('path');

var BUILD_TOOLS = path.join(process.env.SPLUNK_SOURCE, 'web', 'build_tools');
var mergeConfigs = require(path.join(BUILD_TOOLS, 'util', 'mergeConfigs'));
var bootstrapCssConfig = require(path.join(BUILD_TOOLS, 'profiles', 'css_bootstrap.config'));

module.exports = bootstrapCssConfig.map(config => mergeConfigs(config, {
    output: {
        path: path.join(__dirname, '..', 'appserver', 'static', 'build', 'css')
    }
}));
