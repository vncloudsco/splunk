define(['routers/DataFabric', 'util/router_utils'], function(DataFabricRouter, router_utils) {
    var dataFabricRouter = new DataFabricRouter();
    router_utils.start_backbone_history();
});
