import PropTypes from 'prop-types';
import React from 'react';
import _ from 'underscore';
import Button from '@splunk/react-ui/Button';
import Dropdown from '@splunk/react-ui/Dropdown';
import Menu from '@splunk/react-ui/Menu';
import Tooltip from '@splunk/react-ui/Tooltip';

const icon = (
    <svg
        width="16"
        height="16"
        fill="currentColor"
    >
        <circle cx="8" cy="2" r="2" />
        <circle cx="8" cy="8" r="2" />
        <circle cx="8" cy="14" r="2" />
    </svg>
);

const MiscControls = ({
    onClickDrilldown,
    onClickTrellis,
    disableDrilldown,
    disableTrellis,
}) => {
    const moreActionsText = _('More actions').t();

    const buttonToggle = (
        <Button
            appearance="pill"
            style={{
                paddingTop: 6,
                paddingBottom: 6,
                paddingLeft: 0,
                paddingRight: 0,
            }}
            aria-label={moreActionsText}
        >{icon}</Button>
    );

    const tooltip = <span style={{ whiteSpace: 'nowrap' }}>{moreActionsText}</span>;

    return (
        <Tooltip content={tooltip}>
            <Dropdown
                style={{ width: 32 }}
                toggle={buttonToggle}
                focusToggleReasons={['escapeKey', 'toggleClick']}
            >
                <Menu style={{ minWidth: 100 }}>
                    <Menu.Item
                        onClick={onClickDrilldown}
                        disabled={disableDrilldown}
                    >
                        {_('Edit Drilldown').t()}
                    </Menu.Item>
                    <Menu.Item
                        icon={<i className="icon-trellis-layout" style={{ marginRight: 5 }} />}
                        onClick={onClickTrellis}
                        disabled={disableTrellis}
                    >
                        {_('Trellis').t()}
                    </Menu.Item>
                </Menu>
            </Dropdown>
        </Tooltip>
    );
};

MiscControls.propTypes = {
    onClickDrilldown: PropTypes.func.isRequired,
    onClickTrellis: PropTypes.func.isRequired,
    disableDrilldown: PropTypes.bool.isRequired,
    disableTrellis: PropTypes.bool.isRequired,
};

export default MiscControls;
