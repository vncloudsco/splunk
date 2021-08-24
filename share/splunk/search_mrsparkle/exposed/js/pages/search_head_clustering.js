define([
        'routers/SearchHeadClustering',
        'util/router_utils'
    ],
    function(
        SearchHeadClusteringRouter,
        router_utils
    ) {
        var searchHeadClusteringRouter = new SearchHeadClusteringRouter();
        router_utils.start_backbone_history();
    }
);