import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import { icons } from 'splunk_monitoring_console/views/landing//Anomalies';
import './ComponentsPanel.pcss';

class DeploymentComponentsPanel extends Component {
    static propTypes = {
        features: PropTypes.arrayOf(PropTypes.shape({})),
    }
    
    render() {
        const { features } = this.props;
        return (
            <div 
                data-test-name='components-card'
                className='componentsCard'
            >
                <div className='componentsCardHeader'/>
                <div className='componentsCardBody'>
                    {features.map(feature => {
                        return (
                            <div 
                                className='componentItem'
                                data-test-name='component-item'
                                key={feature.name}
                            >
                                <div className='componentItemLabel'>{feature.name}</div>
                                {icons[feature.health].icon}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }
}

export default DeploymentComponentsPanel;