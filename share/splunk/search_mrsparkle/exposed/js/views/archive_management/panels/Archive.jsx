import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import { _ } from '@splunk/ui-utils/i18n';
import { getFormattedValue, emptyArchiveTemplate, constructHistoryData }
    from 'views/shared/indexes/cloud/DynamicDataArchiveUtils';

const columns = [
    { sortKey: 'IndexName', label: _('IndexName') },
    { sortKey: 'earliest', label: _('Earliest') },
    { sortKey: 'latest', label: _('Latest') },
];

class Archive extends Component {

    static propTypes = {
        onFetchArchive: PropTypes.func.isRequired,
    };

    constructor(...args) {
        super(...args);
        this.state = {
            items: [],
        };
    }

    componentDidMount = () => {
        const data = constructHistoryData();
        data.action = 'time_ranges';
        this.props.onFetchArchive(data)
            .then((response) => {
                if (response.status === 'success') {
                    this.setState({ items: response.time_ranges });
                }
            });
    }

    render() {
        const archiveHeaders = ['IndexName', 'earliest', 'latest'];
        return (
            <div>
                { this.state.items.length > 0 ?
                    <Table stripeRows>
                        <Table.Head>
                            {columns.map(headData => (
                                <Table.HeadCell
                                    data-test={headData.sortKey}
                                    key={headData.sortKey}
                                >
                                    {headData.label}
                                </Table.HeadCell>
                            ))}
                        </Table.Head>
                        <Table.Body>
                            {this.state.items
                                .map((row, index) => {
                                    const rowKey = `row-${index}`;
                                    return (
                                        <Table.Row key={rowKey} data-test={rowKey}>
                                            {
                                                archiveHeaders.map(key => (
                                                    <Table.Cell
                                                        key={key}
                                                        data-test={`${rowKey}-${key}`}
                                                    >
                                                        { getFormattedValue(key, row[key]) }
                                                    </Table.Cell>
                                                ))
                                            }
                                        </Table.Row>
                                    );
                                })}
                        </Table.Body>
                    </Table>
                    : emptyArchiveTemplate }
            </div>
        );
    }
}

export default Archive;