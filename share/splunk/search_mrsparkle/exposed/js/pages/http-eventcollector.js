define([
    'jquery',
    'models/indexes/cloud/Index',
    'routers/HttpInput',
    'util/router_utils'
], function(
    $,
    CloudClusterIndexModel,
    HttpInputRouter,
    router_utils
) {
    var createRouter = function(isCloudCluster) {
        new HttpInputRouter({
            isCloudCluster: isCloudCluster
        });
        router_utils.start_backbone_history();
    };
    new CloudClusterIndexModel().fetch().then(function() {
        createRouter(true);
    }).fail(function(error){
        createRouter(false);
    });
});