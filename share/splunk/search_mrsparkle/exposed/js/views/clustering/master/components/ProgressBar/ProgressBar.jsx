import React from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import Progress from '@splunk/react-ui/Progress';
import { createTestHook } from 'util/test_support';

const ProgressBar = (props) => {
    const { totalPeers, restarted, restartPercent } = props;

    return (
        <div {...createTestHook(module.id)}>
            <p className="progress-bar-label">{_('Peer Restart Progress').t()}</p>
            <Progress
                data-label="progress-bar"
                percentage={restartPercent}
                tooltip={_(`${Math.round(restartPercent)}% restarted`).t()}
                {...createTestHook(null, 'progress')}
            />
            <p>{_(`Restarted ${restarted}/${totalPeers}`).t()}</p>
        </div>
    );
};

ProgressBar.propTypes = {
    totalPeers: PropTypes.number,
    restarted: PropTypes.number,
    restartPercent: PropTypes.number,
};

ProgressBar.defaultProps = {
    totalPeers: 0,
    restarted: 0,
    restartPercent: 0,
};

export default ProgressBar;