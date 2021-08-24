import PropTypes from 'prop-types';
import React from 'react';
import Heading from '@splunk/react-ui/Heading';

const HeaderSection = (props) => {
    const { title, description, children } = props;

    return (
        <div data-test="UploadedApps-HeaderSection">
            <div className="section-header section-padded">
                {children}
                <Heading className="section-title">{title}</Heading>
                <p>{description}</p>
            </div>
        </div>
    );
};

HeaderSection.propTypes = {
    title: PropTypes.string,
    description: PropTypes.string,
    children: PropTypes.node,
};

HeaderSection.defaultProps = {
    title: '',
    description: '',
    children: undefined,
};

export default HeaderSection;
