define([
            'jquery',
            'underscore',
            'util/console_dev',
            'splunk.logger',
            'splunk.util'
        ],
        function(
            $,
            _,
            devConsole,
            SplunkLogger,
            splunkUtils
        ) {

    return SplunkLogger.getLogger(splunkUtils.getConfigValue('USERNAME', '') + ':::' + window.location.href);

});
