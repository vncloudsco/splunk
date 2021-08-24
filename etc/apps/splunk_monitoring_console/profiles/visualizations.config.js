var path = require('path');

var BUILD_TOOLS = path.join(process.env.SPLUNK_SOURCE, 'web', 'build_tools');
var mergeConfigs = require(path.join(BUILD_TOOLS, 'util', 'mergeConfigs'));
var sharedConfig = require(path.join(BUILD_TOOLS, 'profiles', 'common', 'shared.config'));

var appDir = path.join(__dirname, '..');
var CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = mergeConfigs(sharedConfig, {
    plugins: [
        new CopyWebpackPlugin([{
            from: path.join(appDir, 'src', 'visualizations', 'KpiTrafficLight'),
            to: path.join(appDir, 'appserver', 'static', 'visualizations', 'KpiTrafficLight'),
            ignore: ['README']
        }]),
        new CopyWebpackPlugin([{
            from: path.join(appDir, 'src', 'visualizations', 'heatmap'),
            to: path.join(appDir, 'appserver', 'static', 'visualizations', 'heatmap'),
            ignore: ['README', 'src/**', 'node_modules/**']
        }])
    ],
    entry: 'heatmap',
    resolve: {
        modules: [ path.join(appDir, 'src', 'visualizations', 'heatmap', 'src'), ]
    },
    output: {
        path: path.join(appDir, 'appserver', 'static', 'visualizations', 'heatmap'),
        filename: 'visualization.js',
        libraryTarget: 'amd'
    },
    externals: [
        'vizapi/SplunkVisualizationBase',
        'vizapi/SplunkVisualizationUtils'
    ]
});
