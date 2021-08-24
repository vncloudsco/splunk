import _ from 'underscore';
import { createTestHook } from 'util/test_support';
import React from 'react';
import PropTypes from 'prop-types';
import Success from '@splunk/react-icons/Success';
import Error from '@splunk/react-icons/Error';
import Button from '@splunk/react-ui/Button';
import Heading from '@splunk/react-ui/Heading';
import Menu from '@splunk/react-ui/Menu';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import css from './WorkloadManagement.pcssm';

const PreflightChecks = (props) => {
    const {
        enableSettingsViewBtn,
        handleReRunPreflightCheck,
        handleShowSettingsView,
        isPreflightCheckLoading,
        checks,
    } = props;

    return (
        <div {...createTestHook(module.id)} className={css.table}>
            <Heading className={`${css.preFlightCheckHeading}`}>
                {_('Preflight Checks').t()}
            </Heading>
            <Menu>
                {checks.map(row => (
                    <Menu.Item
                        className={`${row.id} ${css.preFlightCheckMenuBtn}`}
                        description={row.preflight_check_status ? '' : _(row.mitigation).t()}
                        key={row.id}
                    >
                        {row.preflight_check_status ?
                            <div className={css.successIcon}>
                                <Success size="21px" />
                                &nbsp;{_(row.title).t()}
                            </div>
                            :
                            <div className={css.errorIcon}>
                                <Error size="21px" />
                                &nbsp;{_(row.title).t()}
                            </div>
                        }
                    </Menu.Item>
                ))}
            </Menu>
            <Button
                style={{ marginTop: '5px' }}
                label={_('Rerun preflight checks').t()}
                onClick={handleReRunPreflightCheck}
            />
            <Button
                style={{ marginTop: '5px' }}
                disabled={!enableSettingsViewBtn}
                label={_('Settings View').t()}
                onClick={handleShowSettingsView}
                appearance="primary"
            />
            {isPreflightCheckLoading ?
                <WaitSpinner size="medium" style={{ padding: '6px' }} /> :
                null
            }
        </div>
    );
};


PreflightChecks.propTypes = {
    enableSettingsViewBtn: PropTypes.bool.isRequired,
    handleReRunPreflightCheck: PropTypes.func.isRequired,
    handleShowSettingsView: PropTypes.func.isRequired,
    isPreflightCheckLoading: PropTypes.bool.isRequired,
    checks: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
};

export default PreflightChecks;
