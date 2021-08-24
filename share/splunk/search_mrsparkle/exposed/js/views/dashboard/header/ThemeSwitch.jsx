import React from 'react';
import _ from 'underscore';
import Switch from '@splunk/react-ui/Switch';
import Warning from '@splunk/react-icons/Warning';
import Tooltip from '@splunk/react-ui/Tooltip';
import ReactAdapterBase from 'views/ReactAdapterBase';
import css from './ThemeSwitch.pcssm';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    className: css.switch,
    viewOptions: {
        register: false,
    },
    initialize(...args) {
        ReactAdapterBase.prototype.initialize.apply(this, args);
        this.listenTo(this.model.page, 'change:theme', this.render);
        this.listenTo(this.model.state, 'change:themeDirty', this.render);
        this.handleClick = this.handleClick.bind(this);
    },
    handleClick() {
        const theme = this.model.page.get('theme') || 'light';
        this.model.page.set('theme', theme === 'light' ? 'dark' : 'light');
    },
    getComponent() {
        const theme = this.model.page.get('theme') || 'light';
        const isThemeDirty = this.model.state.get('themeDirty') || false;
        return (
            <Switch
                key="splunk-theme-switch"
                onClick={this.handleClick}
                selected={theme === 'dark'}
                appearance="toggle"
            >
                {_('Dark Theme').t()}
                {isThemeDirty && (
                    <Tooltip content={_('To enable theme changes, save and refresh the dashboard.').t()}>
                        <Warning
                            style={{ color: '#F8BE34', marginLeft: 7 }}
                            size="15px"
                        />
                    </Tooltip>
                )}
            </Switch>
        );
    },
});
