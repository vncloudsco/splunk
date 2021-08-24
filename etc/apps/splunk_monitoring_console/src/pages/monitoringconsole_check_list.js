define(['routers/MonitoringConsoleCheckList', 'util/router_utils'], function(MonitoringConsoleCheckListRouter, router_utils) {
    var monitoringConsoleCheckListRouter = new MonitoringConsoleCheckListRouter();
    router_utils.start_backbone_history();
});