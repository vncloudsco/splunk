define([
        'routers/WorkloadManagement',
        'util/router_utils'
    ],
    function(
        WorkloadManagementRouter,
        router_utils
    ) {
        var workloadManagementRouter = new WorkloadManagementRouter();
        router_utils.start_backbone_history();
    }
);
