import _ from 'underscore';
import Backbone from 'backbone';
import GenericResultJson from 'models/services/search/jobs/GenericResultJson';
import ResultsFetchData from 'models/shared/fetchdata/ResultsFetchData';
import SearchJobConnection from './SearchJobConnection';
import SearchManagerConnection from './SearchManagerConnection';

/**
 * @class DataSource
 */
class DataSource {
    /**
     * Creates an instance of DataSource.
     * @param {string} name
     * @param {object} [fetchParams={}] initial fetch params
     * @param {object} [searchResults={}] inital search result
     * @param {object} [options={}]
     * @memberof DataSource
     */
    constructor(name, fetchParams = {}, searchResults = {}, options = {}) {
        _.extend(this, Backbone.Events);
        this.name = name;
        this.options = options;
        this.searchResults = new GenericResultJson(searchResults);
        this.fetchParams = new ResultsFetchData(fetchParams);
        this.conn = null;
        this.listenTo(this.searchResults, 'change', this.onSearchResultsChange);
        this.listenTo(this.searchResults, 'destroy', this.onSearchResultsDestroy);
        this.listenTo(this.fetchParams, 'change', this.onFetchParamsChange);
    }
    /**
     * Dispose this DataSource
     * @memberof DataSource
     */
    dispose() {
        this.disconnect();
        this.stopListening();
    }
    /**
     *
     * Update current fetch params
     * @param {object} fetchParams new fetch params
     * @param {object} [options={}]
     *
     * @memberof DataSource
     */
    updateFetchParams(fetchParams, options = {}) {
        this.fetchParams.set(fetchParams, options);
    }
    /**
     * Return current fetch params
     * @returns {object} fetch params
     *
     * @memberof DataSource
     */
    getFetchParams() {
        return this.fetchParams.toJSON();
    }
    /**
     * Set search result
     * @param {object} searchResults
     * @param {object} [options={}]
     *
     * @memberof DataSource
     */
    setSearchResults(searchResults, options = {}) {
        this.searchResults.set(searchResults, options);
    }
    /**
     *
     * Return current search result as Object
     * @returns {object} search result
     *
     * @memberof DataSource
     */
    getSearchResults() {
        return this.searchResults.pick('fields', 'rows', 'columns', 'results', 'meta');
    }
    /**
     *
     * Check if the data source contains any search result
     * @returns {boolean}
     *
     * @memberof DataSource
     */
    hasSearchResults() {
        const data = this.getSearchResults();
        if (!_.isEmpty(data)) {
            // In the case of output_mode=json in Splunk 5 --> [{count:0}]
            if (_.isArray(data) && data.length >= 1 && data[0].count !== 0) {
                return true;
            }

            // In the case of output_mode=json in Splunk 6 --> { results: [], ... }
            if (data.results && data.results.length > 0) {
                return true;
            }

            // In the case of output_mode=json_{rows|cols} --> { fields: [], ... }
            if (data.fields && data.fields.length > 0) {
                return true;
            }
        }
        return false;
    }
    /**
     * clear current search results
     * @param {object} [options={}]
     *
     * @memberof DataSource
     */
    clearSearchResults(options = {}) {
        this.searchResults.clear(options);
    }

    /**
     * clear current fetch params
     * @param {any} [options={}]
     *
     * @memberof DataSource
     */
    clearFetchParams(options = {}) {
        this.fetchParams.clear(options);
    }
    /**
     * If the current data source ready to connect
     *
     * @returns {boolean}
     *
     * @memberof DataSource
     */
    isReadyToConnect() {
        return this.getFetchParams().output_mode != null;
    }
    /**
     *
     * Connect this data source with a existing search job
     * @param {models.search.Job} job
     * @param {object} options
     *
     * @returns {SearchJobConnection} search job connection
     *
     * @memberof DataSource
     */
    connectToSearchJob(job, options = {}) {
        this.connectToModule(SearchJobConnection, job, options);
        return this.conn;
    }
    /**
     *
     * Connect this data source with a existing search manager
     * @param {splunkjs.mvc.searchmanager} searchManager
     * @param {object} options
     *
     * @returns {SearchManagerConnection} search manager connection
     *
     * @memberof DataSource
     */
    connectToSearchManager(searchManager, options = {}) {
        this.connectToModule(SearchManagerConnection, searchManager, options);
        return this.conn;
    }
    /**
     *
     * Disconnect from job or search manager
     *
     * @memberof DataSource
     */
    disconnect() {
        if (this.conn) {
            this.conn.disconnect();
            this.conn.off();
            this.conn = null;
        }
    }
    connectToModule(ConnectionModule, instance, options = {}) {
        this.disconnect();
        this.conn = new ConnectionModule(this, instance, options);
        this.conn.on('error', this.onSearchError, this);
        if (this.isReadyToConnect()) {
            this.conn.connect();
        }
    }
    onSearchResultsDestroy() {
        this.trigger('destroy', this);
    }
    onSearchError(text, err) {
        this.trigger('searchError', this, text, err);
    }
    onSearchResultsChange() {
        this.trigger('searchResultsChange', this);
    }
    onFetchParamsChange() {
        if (this.isReadyToConnect() && this.conn && !this.conn.isConnected()) {
            this.conn.connect();
        }
        this.trigger('fetchParamsChange', this);
    }
}

export default DataSource;
