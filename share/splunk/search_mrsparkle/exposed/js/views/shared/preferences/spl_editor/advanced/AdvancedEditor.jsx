import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import TabLayout from '@splunk/react-ui/TabLayout';
import { createTestHook } from 'util/test_support';
import GeneralSettings from './GeneralSettings';
import ThemesAdapter from './ThemesAdapter';

class AdvancedEditor extends Component {
    constructor(props) {
        super(props);
        this.state = { activePanelId: 'general' };
        this.handleTabChange = this.handleTabChange.bind(this);
    }

    handleTabChange(e, { activePanelId }) {
        this.setState({ activePanelId });
    }

    render() {
        const panelStyle = { marginTop: '20px' };
        return (
            <TabLayout
                activePanelId={this.state.activePanelId}
                onChange={this.handleTabChange}
                {...createTestHook(module.id)}
                style={{ marginTop: '0px' }}
            >
                <TabLayout.Panel
                    label={_('General')}
                    panelId="general"
                    style={panelStyle}
                >
                    <GeneralSettings
                        content={this.props.content}
                        onAttributeChange={this.props.onAttributeChange}
                    />
                </TabLayout.Panel>
                <TabLayout.Panel
                    label={_('Themes')}
                    panelId="themes"
                    style={panelStyle}
                >
                    <ThemesAdapter />
                </TabLayout.Panel>
            </TabLayout>
        );
    }
}

AdvancedEditor.propTypes = {
    content: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    onAttributeChange: PropTypes.func.isRequired,
};

export default AdvancedEditor;