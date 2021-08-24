import { _ } from '@splunk/ui-utils/i18n';
import Link from '@splunk/react-ui/Link';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { createDocsURL } from '@splunk/splunk-utils/url';
import React from 'react';
import PropTypes from 'prop-types';
import DFSPageHeader from './DFSPageHeader';

import './DataFabric.pcss';

const LicensePage = ({ status }) => {
    let content;
    if (status === 'loading') {
        content = [
            <h2 key="title" className="grey-text">{_('Checking distributed environment health')}</h2>,
            <WaitSpinner key="license-spinner" data-test="checking-license-spinner" size="medium" />,
        ];
    } else {
        const docUrl = createDocsURL('dfs.enabledfs_editconfigfile');
        content = [
            <p key="license-description" className="grey-text license-desc">
                <span className="link-string-text">
                    {_(`Enable Data Fabric Search (DFS) by changing the “disabled” field to “false” 
                    in the [dfs] stanza of the server.conf configuration file.`)}
                </span>
                <Link to={docUrl} openInNewContext data-test="license-learn-more-link">
                    {_('Learn more')}
                </Link>
            </p>,
        ];
    }
    return (
        <div>
            <DFSPageHeader />
            <div className="content license-content">{content}</div>
        </div>
    );
};

LicensePage.propTypes = {
    status: PropTypes.oneOf(['loading', 'success']).isRequired,
};

export default LicensePage;
