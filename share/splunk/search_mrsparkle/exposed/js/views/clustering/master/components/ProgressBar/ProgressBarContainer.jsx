import React, { Component } from 'react';
import PropTypes from 'prop-types';
import ProgressBar from './ProgressBar';

class ProgressBarContainer extends Component {
    constructor(props, context) {
        super(props, context);
        this.model = this.context.model;
        this.state = {
            totalPeers: 0,
            restarted: 0,
            restartPercent: 0,
        };
    }

    componentDidMount() {
        this.model.entry.content.on('change:restart_progress', this.handleModelChange, this);
    }

    componentWillUnmount() {
        this.model.entry.content.stopListening();
    }

    handleModelChange = () => {
        const peers = this.model.entry.content.get('peers') || {};
        const totalPeers = peers ? Object.keys(peers).length : 0;
        const increment = totalPeers > 0 ? (100 / totalPeers) : 0;
        const restarted = this.model.entry.content.get('restart_progress').done ?
            this.model.entry.content.get('restart_progress').done.length : 0;
        const restartPercent = restarted * increment;
        this.setState({
            totalPeers,
            restarted,
            restartPercent,
        });
    };

    render() {
        return (
            <ProgressBar
                totalPeers={this.state.totalPeers}
                restarted={this.state.restarted}
                restartPercent={this.state.restartPercent}
            />
        );
    }
}

ProgressBarContainer.contextTypes = {
    model: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default ProgressBarContainer;