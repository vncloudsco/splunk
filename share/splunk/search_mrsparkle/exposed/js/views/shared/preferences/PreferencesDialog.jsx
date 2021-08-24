import React, { Component } from 'react';
import PropTypes from 'prop-types';
import _ from 'underscore';
import SimpleDialog from 'components/SimpleDialog';
import GlobalSettingsContainer from 'views/shared/preferences/global/GlobalSettingsContainer';
import SPLEditorContainer from 'views/shared/preferences/spl_editor/SPLEditorContainer';
import { createTestHook } from 'util/test_support';
import GlobalIcon from './icons/global';
import SPLEditorIcon from './icons/SPLeditor';
import Tab from './Tab';
import css from './PreferencesDialog.pcssm';

const GLOBAL_SETTING = 'global';
const SPL_EDITOR = 'SPLeditor';

class PreferencesDialog extends Component {
    constructor(props, context) {
        super(props, context);
        this.state = {
            selected: GLOBAL_SETTING,
        };
        this.model = props.model;
        this.collection = props.collection;
        this.handleTabChange = this.handleTabChange.bind(this);
    }

    getChildContext() {
        return {
            model: this.model,
            collection: this.collection,
        };
    }

    handleTabChange(value) {
        this.setState({ selected: value });
    }

    render() {
        const tabToView = {
            [GLOBAL_SETTING]: <GlobalSettingsContainer showAppSelection={this.props.showAppSelection} />,
            [SPL_EDITOR]: <SPLEditorContainer />,
        };

        const iconStyle = {
            width: '39px',
            height: '39px',
            fill: this.props.isLite ? '#f58220' : '#5CC05C',
            focusable: 'false',
        };

        const tabs = [
            {
                label: _('Global').t(),
                icon: <GlobalIcon {...iconStyle} />,
                value: GLOBAL_SETTING,
            },
            {
                label: _('SPL Editor').t(),
                icon: <SPLEditorIcon {...iconStyle} />,
                value: SPL_EDITOR,
            },
        ];
        const selected = this.state.selected;
        const tabsViews = tabs.map(tab => (
            <Tab
                key={tab.value}
                show={selected === tab.value}
                onClick={this.handleTabChange}
                value={tab.value}
                icon={tab.icon}
                label={tab.label}
                {...createTestHook(null, `tab-${tab.value}`)}
            />
        ));
        return (
            <SimpleDialog
                title={_('Preferences').t()}
                cancelLabel={_('Cancel').t()}
                okLabel={_('Apply').t()}
                onApply={this.props.onApply}
                onClose={this.props.onClose}
                width={560}
                {...createTestHook(null, 'user-pref-modal')}
            >
                <div className={css.navBar}>{tabsViews}</div>
                <div>{tabToView[selected]}</div>
            </SimpleDialog>
        );
    }
}

PreferencesDialog.propTypes = {
    onApply: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
    isLite: PropTypes.bool,
    showAppSelection: PropTypes.bool,
    model: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    collection: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};

PreferencesDialog.defaultProps = {
    isLite: false,
    showAppSelection: true,
};

PreferencesDialog.childContextTypes = {
    model: PropTypes.object.isRequired,
    collection: PropTypes.object.isRequired,
};

export default PreferencesDialog;
