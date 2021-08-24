define(['splunk_monitoring_console/routers/MonitoringConsoleLanding', 'util/router_utils'], function(MonitoringConsoleLandingRouter, router_utils) {
    var monitoringConsoleLandingRouter = new MonitoringConsoleLandingRouter();
    router_utils.start_backbone_history();
});
