import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { values } from 'lodash';
import { _ } from '@splunk/ui-utils/i18n';
import Error from '@splunk/react-icons/Error';
import InfoCircle from '@splunk/react-icons/InfoCircle';
import Success from '@splunk/react-icons/Success';
import Warning from '@splunk/react-icons/Warning';
import Link from '@splunk/react-ui/Link';
import List from '@splunk/react-ui/List';
import Message from '@splunk/react-ui/Message';
import Table from '@splunk/react-ui/Table';
import { createURL } from '@splunk/splunk-utils/url';
import './Anomalies.pcss';

export const icons = {
    green: {
        type: 'success',
        icon: <Success size={1.6} data-test-name='success-icon' className='successIcon' />,
    },
    red: {
        type: 'error',
        icon: <Error size={1.6} data-test-name='error-icon' className='errorIcon' />
    },
    yellow: {
        type: 'warning',
        icon: <Warning size={1.6} data-test-name='warning-icon' className='warningIcon' />
    },
    info: {
       type: 'info',
       icon: <InfoCircle size={1.6} data-test-name='info-icon' className='infoIcon' />
    },
};

class Anomalies extends Component {
    static propTypes = {
        anomalies: PropTypes.arrayOf(PropTypes.shape({})),
    }

    createInvestigateURL = (anomaly) => {
        let tags = [];
        // health.conf feature stanza name is used as tag name
        if (anomaly.reasons) {
            values(values(anomaly.reasons)[0]).forEach(function(reasonObj) {
                tags.push(reasonObj.due_to_stanza.split(':').pop());
            });
        }
        return createURL('app/splunk_monitoring_console/monitoringconsole_check', {tag: tags});
    }

    renderDescriptions = (anomaly) => {
        let children = [];
        if (anomaly.reasons) {
            values(values(anomaly.reasons)[0]).forEach(function(reasonObj, index) {
                children.push(
                    <List.Item 
                        key={`${reasonObj.due_to_stanza}-${index}`}
                    >
                        { reasonObj.reason }
                    </List.Item>
                );
            });
        } else {
            children.push(
                <List.Item>
                    { _('Description is not available.') }
                </List.Item>
            );
        }
        return (
            <List className='anomaly-description'>{ children }</List>
        );
    }

    renderNoAnomalies = () => (
        <div data-test-name='no-anomalies-section' className='no-anomalies-section'>
            <Message type={icons['green'].type}>
                { _('No anomalies found in your deployment.') }
            </Message>
        </div>
    )
    
    render() {
        const { anomalies } = this.props;
        return anomalies.length > 0 ? (
            <div>
                <Table 
                    stripeRows
                    tableStyle={{ backgroundColor: 'white' }}
                    data-test-name='anomalies-table'
                >
                    <Table.Head data-test-name='anomalies-table-head'>
                        <Table.HeadCell
                            data-test-name='anomalies-table-head-cell-status'
                        >
                            {_('Status')}
                        </Table.HeadCell>
                        <Table.HeadCell
                            data-test-name='anomalies-table-head-cell-description'
                        >
                            {_('Description')}
                        </Table.HeadCell>
                        <Table.HeadCell
                            data-test-name='anomalies-table-head-cell-feature'
                            width={300}
                        >
                            {_('Feature')}
                        </Table.HeadCell>
                        <Table.HeadCell
                            data-test-name='anomalies-table-head-cell-actions'
                            width={150}
                        >
                            {_('Actions')}
                        </Table.HeadCell>
                    </Table.Head>
                    <Table.Body data-test-name='anomalies-table-body'>
                        {anomalies.map(anomaly => {

                            const anomalyName = anomaly.name[anomaly.name.length - 1];
                            return (
                                <Table.Row
                                    key={`anomalies-table-row-${anomalyName}`}
                                    data-test-name={`anomalies-table-row-${anomalyName}`}
                                >
                                    <Table.Cell
                                        className='status-cell'
                                        data-test-name={`${anomalyName}-cell-status`}
                                    >
                                        { icons[`${anomaly.health}`].icon }
                                    </Table.Cell>
                                    <Table.Cell
                                        data-test-name={`${anomalyName}-cell-description`}
                                    >
                                        {this.renderDescriptions(anomaly)}
                                    </Table.Cell>
                                    <Table.Cell
                                        data-test-name={`${anomalyName}-cell-feature`}
                                    >
                                        {anomaly.name.join(' | ')}
                                    </Table.Cell>
                                    <Table.Cell
                                        data-test-name={`${anomalyName}-cell-action`}
                                    >
                                        <Link 
                                            to={this.createInvestigateURL(anomaly)}
                                            openInNewContext
                                        >
                                            {_('Investigate')}
                                        </Link>
                                    </Table.Cell>
                                </Table.Row>
                            );
                        })}
                    </Table.Body>
                </Table>
            </div>
        ) : this.renderNoAnomalies();
    }
}

export default Anomalies;