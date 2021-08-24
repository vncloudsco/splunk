import SearchJob from '@splunk/search-job';

// Defaults search job attributes for getting the index field values
const defaults = {
    indexList: [],
    count: 250,
    valueFilter: '',
    fieldFilter: '',
    type: '',
    earliest_time: '-60s@s',
    latest_time: 'now',
    isDefault: false,
    cache: true,
    cacheLimit: 600,
};

/**
 * This class to create search jobs that gets the values of default index
 * fields (host, source, sourcetype) or custom index fields defined by user.
 */
export default class IndexFieldValues {
    constructor(options) {
        this.options = Object.assign({}, defaults, options);
        this.valueSearchStr = '';
        this.fieldSearchStr = '';
        this.errorMsg = '';
    }
    /**
     * Function to validate the model.
     * To have a valid search string index name and field name are required fields.
     * @returns {boolean}
     */
    isValid() {
        if (!this.options.indexList.length || !this.options.type) {
            this.errorMsg = 'Index name(s) and index field name are required fields.';
            return false;
        }
        return true;
    }
    /**
     * Call this function to unsubscribe from the searchJob and reset
     * instance values to the defaults.
     */
    clear() {
        this.options = Object.assign({}, defaults);
        this.valueSearchStr = '';
        this.errorMsg = '';
        if (this.searchJob) {
            this.searchJob.cancel();
        }
    }
    /**
     * Call the SearchJob component to create the search job.
     * @returns {instance of SearchJob}
     */
    createSearchJob(search) {
        return SearchJob.create({
            search,
            earliest_time: this.options.earliest_time,
            latest_time: this.options.latest_time,
        }, { cache: this.options.cache, cacheLimit: this.options.cacheLimit });
    }
    createIndexListStr(type) {
        const indList = [...this.options.indexList];
        let indexStr = indList.length ? `index=${indList.shift()}` : '';
        indList.forEach((ind) => {
            indexStr += (type === 'value') ? ` OR index=${ind}` : ` index=${ind}`;
        });
        return indexStr;
    }
    /**
     * Returns a search job to get the top 100 index field names for a list of indices.
     * Uses the walklex command introduced in Pinkipie to return the list of field names.
     * @returns {instance of SearchJob}
     */
    getFields() {
        if (this.isValid()) {
            this.fieldSearchStr = `| walklex ${this.createIndexListStr('field')} type=field`;
            this.fieldSearchStr += this.options.fieldFilter ?
                ` pattern=${this.options.fieldFilter}*` : '';
            this.fieldSearchStr += ' | where substr(field,0,1) != " " | stats count by field ' +
             `| sort ${this.options.count} -count`;
        }
        this.searchJob = this.createSearchJob(this.fieldSearchStr);
        return this.searchJob;
    }
    /**
     * Returns a search job to get the values of a particular default index field.
     * Uses the '| tstats' search command. Optionally filters results based on a search string.
     * Limits the results to options.count.
     * @returns {instance of SearchJob}
     */
    getValues() {
        if (this.isValid()) {
            this.valueSearchStr = `| tstats count where ${this.createIndexListStr('value')} by ${this.options.type}`;
            this.valueSearchStr += this.options.valueFilter ?
                ` | where match(${this.options.type}, "${this.options.valueFilter}")` : '';
            this.valueSearchStr += ` | sort ${this.options.count} -count | sort +${this.options.type}`;
        }
        this.searchJob = this.createSearchJob(this.valueSearchStr);
        return this.searchJob;
    }
}
