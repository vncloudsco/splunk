define([
	'jquery',
	'routers/Sourcetypes',
	'models/indexes/cloud/Index',
	'util/router_utils'
], function(
	$,
	SourcetypesRouter,
	IndexModel,
	router_utils
) {
	var createRouter = function(isSingleInstanceCloud) {
		var sourcetypesRouter = new SourcetypesRouter({
			isSingleInstanceCloud: isSingleInstanceCloud
	    });
	    try {
            router_utils.start_backbone_history();
        }
        // Catch malformed URLs and redirect to listing page.
        catch (e){
            window.location = './';
        }
	};

	new IndexModel().fetch().then(function() {
        createRouter(false);
    }).fail(function(error){
        createRouter(true);
    });
});
