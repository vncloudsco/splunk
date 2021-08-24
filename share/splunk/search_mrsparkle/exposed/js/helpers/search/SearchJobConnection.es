import _ from 'underscore';
import Backbone from 'backbone';
import Job from 'models/search/Job';
import GenericResultJson from 'models/services/search/jobs/GenericResultJson';

/**
 *
 *
 * @class SearchJobConnection
 */
class SearchJobConnection {
    /**
     * Creates an instance of SearchJobConnection.
     * @param {helpers.search.DataSource} dataSource data source instance
     * @param {models.search.Job} searchJob search job instance
     * @param {object} [options={}]
     *
     * @memberof SearchJobConnection
     */
    constructor(dataSource, searchJob, options = {}) {
        _.extend(this, Backbone.Events);
        this.dataSource = dataSource;
        this.searchJob = searchJob;
        this.options = options;
    }
    connect() {
        this.disconnect();
        this.result = new GenericResultJson(); // save data into a temp model as we need to mixin meta later.
        this.onFetchParamsChange();
        Job.registerArtifactModel(this.result, this.searchJob, Job.RESULTS_PREVIEW);
        this.listenTo(this.result, 'change', this.onDataChange);
        this.listenTo(this.dataSource, 'fetchParamsChange', this.onFetchParamsChange);
    }
    disconnect() {
        if (this.result) {
            Job.unregisterArtifactModel(this.result, this.searchJob);
            this.result = null;
        }
        this.stopListening();
    }
    isConnected() {
        return this.result != null;
    }
    /**
     * Move data from temp model into data source
     * @memberof SearchJobConnection
     */
    onDataChange() {
        const data = Object.assign({}, this.result.toJSON(), {
            meta: {
                done: this.searchJob.isDone(),
            },
        });
        this.dataSource.setSearchResults(data);
    }
    onFetchParamsChange() {
        if (this.result) {
            this.result.fetchData.set(this.dataSource.getFetchParams());
        }
    }
}

export default SearchJobConnection;
