import PropTypes from 'prop-types';
import React, { Component } from 'react';
import Link from '@splunk/react-ui/Link';
import splunkUtils from 'splunk.util';
import './ActionLink.pcss';

class ActionLink extends Component {
    handleActionLinkClick = (e) => {
        e.preventDefault();
        this.props.onActionDialogOpen(this.props.package);
    }

    render() {
        return (
            <div className="action-link">
                <Link
                    onClick={this.handleActionLinkClick}
                    disabled={this.props.disabledDuringDeployment && this.props.deploymentInProgress}
                    data-test={splunkUtils.sprintf('UploadedApps-ActionLink-%s', this.props.action)}
                >
                    { this.props.action }
                </Link>
            </div>
        );
    }
}

ActionLink.propTypes = {
    action: PropTypes.string.isRequired,
    package: PropTypes.shape({}),
    deploymentInProgress: PropTypes.bool,
    disabledDuringDeployment: PropTypes.bool,
    onActionDialogOpen: PropTypes.func.isRequired,
};

ActionLink.defaultProps = {
    package: undefined,
    deploymentInProgress: false,
    disabledDuringDeployment: false,
};

export default ActionLink;
