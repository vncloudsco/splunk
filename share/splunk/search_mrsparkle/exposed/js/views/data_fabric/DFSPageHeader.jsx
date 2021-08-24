import React from 'react';
import PropTypes from 'prop-types';
import { createDocsURL } from '@splunk/splunk-utils/url';
import { _ } from '@splunk/ui-utils/i18n';
import Link from '@splunk/react-ui/Link';
import Button from '@splunk/react-ui/Button';

import './DataFabric.pcss';

const docUrl = createDocsURL('dfs.federatedsearch_noconnection');

const DFSPageHeader = ({ openModal }) => {
    const handleClick = () => {
        openModal();
    };

    return (
        <div data-test="data-fabric-container">
            <div>
                {openModal && <div style={{ float: 'right', marginTop: '1em', marginRight: '1em' }}>
                    <Button
                        data-test="add-provider-btn"
                        label={_('Add federated provider')}
                        appearance="primary"
                        style={{ flexGrow: '0' }}
                        onClick={handleClick}
                    />
                </div>}
                <div>
                    <h1 className="header">{_('Data Fabric Search (DFS)')}</h1>
                    <div className="description desc-text">
                        <span className="link-string-text">
                            {_('Conducts searches and joins across multiple federated providers.')}
                        </span>
                        <Link data-test="dfs-learn-more-link" to={docUrl} openInNewContext>
                            {_('Learn more')}
                        </Link>
                    </div>
                </div>
            </div>
            <div className="divider" />
        </div>
    );
};

DFSPageHeader.defaultProps = {
    openModal: null,
};

DFSPageHeader.propTypes = {
    openModal: PropTypes.func,
};

export default DFSPageHeader;
