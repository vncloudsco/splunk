import React, { Component } from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import Link from '@splunk/react-ui/Link';
import { _ } from '@splunk/ui-utils/i18n';
import { createTestHook } from 'util/test_support';
import * as DDAUtils from 'views/shared/indexes/cloud/DynamicDataArchiveUtils';
import Confirmation from './Confirmation';

class RestoreHistory extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            sortKey: 'IndexName',
            sortDir: 'asc',
            items: props.history,
            requestId: '',
        };
    }

    componentWillReceiveProps = (nextProps) => {
        this.setState({ items: nextProps.history });
    }

    handleSort = (e, { sortKey }) => {
        const nextSortDir = DDAUtils.getNextSortDir(this.state.sortKey, this.state.sortDir, sortKey);
        this.setState({
            sortKey,
            sortDir: nextSortDir,
        });
        this.props.onSort(sortKey, nextSortDir);
    }

    handleConfirmOpen = (start, end, name, desc) => {
        this.setState({
            requestId: {
                IndexName: name,
                StartTime: start,
                EndTime: end,
                Description: desc,
            },
        });
        this.props.onConfirmToggle();
    }

    handleFlush = () => {
        this.props.onFlushConfirm(this.state.requestId);
    }

    render() {
        const { sortKey, sortDir } = this.state;
        const msg = _('Are you sure you want to clear restored data? ' +
            'Clearing this restored data does not delete data from your archive.');
        const columns = DDAUtils.getRestoreHistoryColumns(this.state.items);
        return (
            <div>
                {this.state.items.length > 0 ?
                    <Table
                        stripeRows headType="fixed"
                        innerStyle={{ maxHeight: 200 }}
                        {...createTestHook(null, 'ArchiveRestoreHistoryTable')}
                    >
                        <Table.Head>
                            {columns.map(headData => (
                                <Table.HeadCell
                                    key={headData.sortKey}
                                    onSort={headData.sortKey !== 'Description' ? this.handleSort : undefined}
                                    sortKey={headData.sortKey}
                                    sortDir={headData.sortKey === sortKey ? sortDir : 'none'}
                                >
                                    {headData.label}
                                </Table.HeadCell>
                            ))}
                            <Table.HeadCell>
                                {_('Actions')}
                            </Table.HeadCell>
                        </Table.Head>
                        <Table.Body>
                            {this.state.items
                                .map((row, index) => {
                                    const rowKey = `row-${index}`;
                                    return (
                                        <Table.Row key={rowKey}>
                                            { DDAUtils.headers.map(key => (
                                                <Table.Cell key={key}>
                                                    { key === 'State' && DDAUtils.getStateIcon(row[key]) }
                                                    { DDAUtils.getFormattedValue(key, row[key]) }
                                                </Table.Cell>
                                            )) }
                                            <Table.Cell key="action">
                                                {
                                                    row.State === 'Success' &&
                                                        <Link
                                                            onClick={() => this.handleConfirmOpen(row.StartTime,
                                                            row.EndTime, row.IndexName, row.Description)}
                                                            disabled={this.props.disableContents}
                                                        >
                                                            {_('Clear')}
                                                        </Link>
                                                }
                                            </Table.Cell>
                                        </Table.Row>
                                    );
                                })}
                        </Table.Body>
                    </Table>
                    : DDAUtils.emptyTemplate }
                <Confirmation
                    open={this.props.flushConfirm}
                    confirmMsg={msg}
                    confirmButtonLabel={_('Clear')}
                    onConfirmCancel={this.props.onConfirmToggle}
                    processing={this.props.processing}
                    onConfirm={this.handleFlush}
                />
            </div>
        );
    }
}

RestoreHistory.propTypes = {
    history: PropTypes.arrayOf(
        PropTypes.shape({
            StartTime: PropTypes.number,
            EndTime: PropTypes.number,
            RequestTime: PropTypes.number,
            Description: PropTypes.string,
            State: PropTypes.string,
            DataVolumeInGB: PropTypes.number,
        })),
    onSort: PropTypes.func.isRequired,
    onConfirmToggle: PropTypes.func.isRequired,
    onFlushConfirm: PropTypes.func.isRequired,
    flushConfirm: PropTypes.bool,
    processing: PropTypes.bool,
    disableContents: PropTypes.bool,
};

RestoreHistory.defaultProps = {
    history: [],
    flushConfirm: false,
    processing: false,
    disableContents: false,
};

export default RestoreHistory;