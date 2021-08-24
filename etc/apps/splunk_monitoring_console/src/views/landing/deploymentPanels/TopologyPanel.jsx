import {_, gettext} from '@splunk/ui-utils/i18n';
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Link from '@splunk/react-ui/Link';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import SearchJob from '@splunk/search-job';
import { createURL } from '@splunk/splunk-utils/url';
import './TopologyPanel.pcss';

class TopologyPanel extends Component {
    static propTypes = {
        appLocal: PropTypes.shape({}).isRequired,
        indexes: PropTypes.number.isRequired,
        indexerClustering: PropTypes.shape({}).isRequired,
    };

    constructor(props, context) {
        super(props, context);

        this.baseDmcAssetsSearch = SearchJob.create({
            search: '| inputlookup dmc_assets',
        }, {
            app: 'splunk_monitoring_console',
        });

        this.state = {
            indexes: this.props.appLocal.entry.content.get('configured') == '1' ? undefined : this.props.indexes,
            indexers: undefined, 
            searchHeads: undefined, 
            clusterMasters: undefined, 
            licenseMasters: undefined, 
            deploymentServers: undefined,
        };
    }

    componentDidMount() {
        if (this.props.appLocal.entry.content.get('configured') == '1') {
            this.indexesJob = SearchJob.create({
                search: 
                    '| rest splunk_server_group=dmc_group_indexer splunk_server_group="*" /services/data/indexes datatype=all' +
                    '| join title splunk_server type=outer [rest splunk_server_group=dmc_group_indexer splunk_server_group="*" /services/data/indexes-extended datatype=all]' +
                    '| `dmc_exclude_indexes`' +
                    '| eval elapsedTime = now() - strptime(minTime,"%Y-%m-%dT%H:%M:%S%z")' +
                    '| eval dataAge = ceiling(elapsedTime / 86400)' +
                    '| eval indexSizeGB = if(currentDBSizeMB >= 1 AND totalEventCount >=1, currentDBSizeMB/1024, null())' +
                    '| eval maxSizeGB = maxTotalDataSizeMB / 1024' +
                    '| eval sizeUsagePerc = indexSizeGB / maxSizeGB * 100' + 
                    '| stats dc(title) as numIndexes'
            }, {
                app: 'splunk_monitoring_console',
            });

            this.indexesJob.getResults().subscribe(results => {
                let indexes = results.results[0] ? results.results[0].numIndexes : '0';
                this.setState({
                    indexes,
                })
            });
        }

        this.indexersJob = this.baseDmcAssetsSearch.getResults && 
            this.baseDmcAssetsSearch.getResults({
                search: '| stats count(eval(search_group="dmc_group_indexer")) as num_indexers',
            }).subscribe(results => {
                let indexers = results.results[0] ? results.results[0].num_indexers : '0';
                this.setState({
                    indexers,
                });
            });
        
        this.searchHeadsJob = this.baseDmcAssetsSearch.getResults && 
            this.baseDmcAssetsSearch.getResults({
                search: '| stats count(eval(search_group="dmc_group_search_head")) as num_search_heads',
            }).subscribe(results => {
                let searchHeads = results.results[0] ? results.results[0].num_search_heads : '0';
                this.setState({
                    searchHeads,
                });
            });
        
        this.clusterMastersJob = this.baseDmcAssetsSearch.getResults && 
            this.baseDmcAssetsSearch.getResults({
                search: '| stats count(eval(search_group="dmc_group_cluster_master")) as num_cluster_masters',
            }).subscribe(results => {
                let clusterMasters = results.results[0] ? results.results[0].num_cluster_masters : '0';
                this.setState({
                    clusterMasters,
                });
            });

        this.licenseMastersJob = this.baseDmcAssetsSearch.getResults && 
            this.baseDmcAssetsSearch.getResults({
                search: '| stats count(eval(search_group="dmc_group_license_master")) as num_license_masters',
            }).subscribe(results => {
                let licenseMasters = results.results[0] ? results.results[0].num_license_masters : '0';
                this.setState({
                    licenseMasters,
                });
            });

        this.deploymentServerJob = this.baseDmcAssetsSearch.getResults && 
            this.baseDmcAssetsSearch.getResults({
                search: '| stats count(eval(search_group="dmc_group_deployment_server")) as num_deployment_servers',
            }).subscribe(results => {
                let deploymentServers = results.results[0] ? results.results[0].num_deployment_servers : '0';
                this.setState({
                    deploymentServers,
                });
            });
    }

    componentWillUnmount() {
        if(this.indexesJob) {
            this.indexesJob.unsubscribe();
        }
        if (this.indexersJob) {
            this.indexerJob.unsubscribe();
        }
        if (this.searchHeadsJob) {
            this.searchHeadsJob.unsubscribe();
        }
        if (this.clusterMastersJob) {
            this.clusterMastersJob.unsubscribe();
        }
        if (this.licenseMastersJob) {
            this.licenseMastersJob.unsubscribe();
        }
        if (this.deploymentServerJob) {
            this.deploymentServerJob.unsubscribe();
        }
    }

    render() {
        const { 
            appLocal,
            indexerClustering,
        } = this.props;

        const {
            indexes, 
            indexers, 
            searchHeads,
            clusterMasters,
            licenseMasters,
            deploymentServers,
        } = this.state;

        const renderWaitSpiner = () => {
            if (
                typeof indexes === 'undefined' ||
                typeof indexers === 'undefined' || 
                typeof searchHeads === 'undefined' ||
                typeof clusterMasters === 'undefined' ||
                typeof licenseMasters === 'undefined' ||
                typeof deploymentServers === 'undefined'
            ) {
                return (
                    <div className='topologyMiniCard'>
                        <WaitSpinner size='medium' />
                    </div>
                );
            }
        }

        const getIndexesURL = () => {
            return appLocal.entry.content.get('configured') == '1' ? 
                createURL(
                    'app/splunk_monitoring_console/indexes_and_volumes_deployment', 
                    {
                        'form.datatype': 'datatype=all',
                        'form.group': '*',
                    }
                ) : 
                createURL('manager/splunk_monitoring_console/data/indexes');
        }

        return (
            <div
                data-test-name='deployment-topology-card'
                className='topologyCard'
            >
                <div
                    className='topologyCardHeader'
                />
                <div className='topologyCardBody'>
                    <div className='topologyDetails'>

                        {renderWaitSpiner()}
                        
                        {
                            indexers > 0 && appLocal.entry.content.get('configured') == '1' ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={createURL(
                                            'app/splunk_monitoring_console/monitoringconsole_instances', 
                                            {group: 'dmc_group_indexer'}
                                        )}
                                    >
                                        {indexers}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { indexers > 1 ? gettext('Indexers') : gettext('Indexer') }
                                    </div>
                                </div>
                            ) : null 
                        }

                        {
                            searchHeads > 0 && appLocal.entry.content.get('configured') == '1' ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={createURL(
                                            'app/splunk_monitoring_console/monitoringconsole_instances', 
                                            {group: 'dmc_group_search_head'}
                                        )}
                                    >
                                        {searchHeads}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { searchHeads > 1 ? gettext('Search Heads') : gettext('Search Head') }
                                    </div>
                                </div>
                            ) : null 
                        }

                        {
                            clusterMasters > 0 && appLocal.entry.content.get('configured') == '1' ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={createURL(
                                            'app/splunk_monitoring_console/monitoringconsole_instances', 
                                            {group: 'dmc_group_cluster_master'}
                                        )}
                                    >
                                        {clusterMasters}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { clusterMasters > 1 ? gettext('Cluster Masters') : gettext('Cluster Master') }
                                    </div>
                                </div>
                            ) : null 
                        }

                        {
                            licenseMasters > 0 && appLocal.entry.content.get('configured') == '1' ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={createURL(
                                            'app/splunk_monitoring_console/monitoringconsole_instances', 
                                            {group: 'dmc_group_license_master'}
                                        )}
                                    >
                                        {licenseMasters}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { licenseMasters > 1 ? gettext('License Masters') : gettext('License Master') }
                                    </div>
                                </div>
                            ) : null 
                        }
                        
                        {
                            deploymentServers > 0 && appLocal.entry.content.get('configured') == '1' ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={createURL(
                                            'app/splunk_monitoring_console/monitoringconsole_instances', 
                                            {group: 'dmc_group_deployment_server'}
                                        )}
                                    >
                                        {deploymentServers}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { deploymentServers > 1 ? gettext('Deployment Servers') : gettext('Deployment Server') }
                                    </div>
                                </div>
                            ) : null 
                        }

                        {
                            indexes > 0 ? 
                            (
                                <div className='topologyMiniCard'>
                                    <Link 
                                        className='topologyMiniCardNum'
                                        to={getIndexesURL()}
                                    >
                                        {indexes}
                                    </Link>
                                    <br />
                                    <div className='topologyLabel'>
                                        { indexes > 1 ? gettext('Indexes') : gettext('Index') }
                                    </div>
                                </div>
                            ) : null 
                        }
                    </div>

                    <div className='topologyRow'>
                        <div className='topologyLabel'>{gettext('Indexer Clustering')}</div>
                        <div className='topologyLabel topologyResult'>
                            {
                                indexerClustering.entry.content.changed.disabled ? 
                                    gettext('Disable') : gettext('Enable') 
                            }
                        </div>
                    </div>
                    
                    {
                        indexerClustering.entry.content.changed.disabled ? null : 
                        (
                            <div className='topologyRow'>
                                <div className='topologyLabel'>{gettext('Replication Factor')}</div>
                                <div className='topologyMiniCardNum'>
                                    {indexerClustering.entry.content.changed.replication_factor}
                                </div>
                            </div>
                        )
                    }

                    {
                        indexerClustering.entry.content.changed.disabled ? null : 
                        (
                            <div className='topologyRow'>
                                <div className='topologyLabel'>{gettext('Search Factor')}</div>
                                <div className='topologyMiniCardNum'>
                                    {indexerClustering.entry.content.changed.search_factor}
                                </div>
                            </div>
                        )
                    }
                </div>
            </div>
        );
    }
}

export default TopologyPanel;
