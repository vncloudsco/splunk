import _ from 'underscore';

const DataSourceMixin = {
    getAllDataSources() {
        return this.dataSources || [];
    },
    getDataSource(dataSourceName) {
        return _(this.getAllDataSources()).find(ds => (
            ds.name === dataSourceName
        ));
    },
    getPrimaryDataSource() {
        return this.getDataSource('primary');
    },
};

export default DataSourceMixin;
