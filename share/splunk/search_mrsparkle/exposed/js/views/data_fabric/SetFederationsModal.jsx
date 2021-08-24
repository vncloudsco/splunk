import React from 'react';
import { _ } from '@splunk/ui-utils/i18n';
import { after, difference, isEqual } from 'underscore';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import FshPasswordModel from 'models/services/admin/FshPassword';
import FederationModel from 'models/services/dfs/Federation';
import BaseModel from 'models/Base';
import Modal from '@splunk/react-ui/Modal';
import Message from '@splunk/react-ui/Message';
import Text from '@splunk/react-ui/Text';
import Dropdown from '@splunk/react-ui/Dropdown';
import Link from '@splunk/react-ui/Link';
import Button from '@splunk/react-ui/Button';
import { sprintf } from '@splunk/ui-utils/format';
import querystring from 'querystring';
import { createDocsURL, createRESTURL } from '@splunk/splunk-utils/url';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import AccumulatorControl from 'views/shared/react/groupcontrol/AccumulatorControl';
import FlashMessages from 'views/shared/react/FlashMessages';

import './DataFabric.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name SetFederationsModal
     * @extends {views.ReactAdapterBase}
     * @description A modal for creating or editing a federated provider.
     *
     * @param {Object} options
     */
    initialize(options) {
        this.store = {};
        this.deferreds = {};
        this.savedList = {
            federation: null,
            fshPassword: null,
            roles: [],
        };

        // variables
        this.modelAttribute = 'selectedItems';
        this.labelWidth = '220px';
        this.title = _('Add Federated Provider');
        this.selectedItems = [];

        // model
        this.model.federation = new FederationModel();
        this.model.fshPassword = new FshPasswordModel();
        this.model.role = new BaseModel();

        // functions
        this.handleRequestOpen = this.handleRequestOpen.bind(this);
        this.handleRequestClose = this.handleRequestClose.bind(this);
        this.handleChange = this.handleChange.bind(this);
        this.submit = this.submit.bind(this);
        this.edit = this.edit.bind(this);
        this.saveProvider = this.saveProvider.bind(this);
        this.generateForm = this.generateForm.bind(this);
        this.completeAction = this.completeAction.bind(this);

        this.listenTo(this.model.state, 'change:open', this.render);
        this.listenTo(this.model.state, 'change:type', () => {
            if (this.model.state.get('type') === 'edit') {
                this.title = _('Edit Federated Provider');
            } else {
                this.title = _('Add Federated Provider');
                this.selectedItems = [];
                this.model.state.set('fullIp', '');
            }
            this.render();
        });
        this.listenTo(this.model.state, 'change:federation', this.render);
        this.listenTo(this.model.state, 'change:err', this.render);

        ReactAdapterBase.prototype.initialize.apply(this, options);
    },

    completeAction(changedRoles) {
        if (
            this.savedList.federation &&
            this.savedList.fshPassword &&
            this.savedList.roles.length === changedRoles.length
        ) {
            this.trigger('federatedProviderSaved');
            this.handleRequestClose();
        } else {
            // if any requests fail on saving, then remove all successfully saving requests and reset success list
            if (this.savedList.federation) {
                this.savedList.federation.destroy().done(() => {
                    this.savedList.federation = null;
                });
            }
            if (this.savedList.fshPassword) {
                this.savedList.fshPassword.destroy().done(() => {
                    this.savedList.fshPassword = null;
                });
            }

            // Remove federated providers from the existing roles
            if (this.savedList.roles.length) {
                const providerName = this.model.federation.entry.content.get('name');
                this.savedList.roles.forEach((model) => {
                    const index = this.savedList.roles.indexOf(model);
                    model.removeProvider(providerName);
                    model.save({}, {
                        traditional: true,
                        success: () => {
                            this.savedList.roles.slice(index, 1);
                        },
                    });
                });
            }
        }
    },

    saveProvider(changedRoles, complete) {
        if (this.model.state.get('type') !== 'edit' && this.model.federation.id) {
            this.model.federation.unset('id');
        }

        this.model.federation.save(
            {},
            {
                success: (saved) => {
                    this.savedList.federation = saved;

                    /* After federation provider is setup,
                        then continue setting up fsh password and update role's federated provider
                    */
                    this.model.fshPassword.save({}, {
                        success: (savedFshPassword) => {
                            this.savedList.fshPassword = savedFshPassword;
                            complete();
                        },
                    })
                    .fail(complete);

                    const providerName = this.model.federation.entry.content.get('name');
                    this.collection.fshRoles.models.forEach((model) => {
                        if (changedRoles.indexOf(model.entry.get('name')) > -1) {
                            model.addProvider(providerName);
                            model.save({}, {
                                traditional: true,
                                success: (savedModel) => {
                                    this.savedList.roles.push(savedModel);
                                    complete();
                                },
                            })
                            .fail(complete);
                        }
                    });
                },
            },
        );
    },

    validateRolesChange(changedRoles) {
        return changedRoles && changedRoles.length ? null : _('Please choose at least one role');
    },

    submit() {
        // Validate inputs
        const fullIp = this.model.state.get('fullIp');
        const changedRoles = this.model.role.get(this.modelAttribute);
        const noRolesError = this.validateRolesChange(changedRoles);
        const providerExists = this.options.checkName(this.model.federation.entry.content.get('name') || '');

        if (!noRolesError && !providerExists) {
            this.model.state.set('err', '');
            // after all roles changes send out and saving password request
            const complete = after(1 + changedRoles.length, () => this.completeAction(changedRoles));
            this.model.federation.formatInputs(fullIp);
            if (!this.model.federation.entry.content.validate() && !this.model.fshPassword.entry.content.validate()) {
                this.saveProvider(changedRoles, complete);
            }
        } else {
            this.model.state.set('err', noRolesError || providerExists);
            this.$el.next().find('#set-federation-modal').animate({ scrollTop: 0 }, 'fast');
        }
    },

    updateFshPassword(url, data) {
        const mode = { output_mode: 'json' };
        return fetch(createRESTURL(`storage/fshpasswords/${url}?${querystring.encode(mode)}`), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
            .then(handleResponse(200))
            .catch(handleError());
    },

    edit() {
        const fullIp = this.model.state.get('fullIp');
        this.model.federation.formatInputs(fullIp);
        const changedRoles = this.model.role.get(this.modelAttribute);
        const noRolesError = this.validateRolesChange(changedRoles);

        // Don't validate name and username of federation because they are disabled
        if (!noRolesError && this.model.federation.entry.content.isValid(['ip', 'splunk.port'])) {
            /* To avoid override the original values,
            we validate results and then give the results to the real federation model */
            this.model.savedFederation.entry.content.set('ip', this.model.federation.entry.content.get('ip'));
            this.model.savedFederation.entry.content.set(
                'splunk.port',
                this.model.federation.entry.content.get('splunk.port'));
            this.model.savedFederation.entry.content.set(
                'splunk.app',
                this.model.federation.entry.content.get('splunk.app'));
            const removedRoles = difference(this.selectedItems, changedRoles);
            const newAddedRoles = difference(changedRoles, this.selectedItems);

            const finishUpdate = after(1 + removedRoles.length + newAddedRoles.length, () => {
                this.trigger('federatedProviderSaved');
                this.handleRequestClose();
            });

            this.model.savedFederation.save(
                {},
                {
                    success: () => {
                        const providerName = this.model.savedFederation.entry.get('name');
                        // only update roles and passwords when they have changes
                        if (!isEqual(changedRoles, this.selectedItems)) {
                            this.collection.fshRoles.models.forEach((model) => {
                                if (removedRoles.indexOf(model.entry.get('name')) > -1) {
                                    model.removeProvider(providerName);
                                    model.save({}, { traditional: true, success: finishUpdate });
                                } else if (newAddedRoles.indexOf(model.entry.get('name')) > -1) {
                                    model.addProvider(providerName);
                                    model.save({}, { traditional: true, success: finishUpdate });
                                }
                            });
                        }

                        const password = this.model.fshPassword.entry.content.get('password');
                        if (password && !this.model.fshPassword.entry.content.validate()) {
                            const username = this.model.savedFederation.entry.content.get('splunk.serviceAccount');
                            const url = encodeURIComponent(`${providerName}:${username}`);
                            this.updateFshPassword(url, { password })
                                .then(finishUpdate)
                                .catch(() => {
                                    this.model.state.set('err', _('Unable to update password. Please retry.'));
                                });
                        } else {
                            finishUpdate();
                        }
                    },
                },
            );
        } else {
            this.model.state.set('err', noRolesError || _('Invalid IP address or port number'));
            this.$el.next().find('#set-federation-modal').animate({ scrollTop: 0 }, 'fast');
        }
    },

    handleChange(e, { value, name }) {
        if (name === 'name') {
            this.model.federation.entry.content.set('name', value);
            this.model.fshPassword.entry.content.set('provider', value);
        } else if (name === 'app') {
            this.model.federation.entry.content.set('splunk.app', value);
        } else if (name === 'username') {
            this.model.federation.entry.content.set('splunk.serviceAccount', value);
            this.model.fshPassword.entry.content.set('name', value);
        } else if (name === 'password') {
            this.model.fshPassword.entry.content.set('password', value);
        } else if (name === 'ip') {
            this.model.state.set('fullIp', value);
        }
    },

    handleRequestOpen() {
        this.model.state.set('open', true);
    },

    handleRequestClose() {
        // reset everything when close the modal
        this.model.state.set('err', '');
        this.model.federation = new FederationModel();
        this.model.role = new BaseModel();
        this.model.fshPassword = new FshPasswordModel();
        this.savedList = {
            federation: null,
            fshPassword: null,
            roles: [],
        };

        this.model.state.set('open', false);
    },

    generateForm(inputs) {
        return inputs.map((item) => {
            const { label, name, help, defaultValue, editDisabled } = item;
            const ariaLabel = sprintf(_('%(label)s:%(defaultValue)s'), { label, defaultValue });
            const isEdit = this.model.state.get('type') === 'edit';

            return (
                <ControlGroup
                    labelWidth={this.labelWidth}
                    data-test={`${name}-control-group`}
                    label={label}
                    help={help}
                    key={`${name}-group`}
                >
                    { editDisabled
                        ? <span aria-label={ariaLabel} className="input-label">{defaultValue}</span>
                        : <Text
                            data-test={name}
                            autoFocus={name === 'name'}
                            name={name}
                            key={`${name}-text`}
                            onChange={this.handleChange}
                            defaultValue={isEdit ? defaultValue : ''}
                            type={name === 'password' ? 'password' : 'text'}
                            style={name === 'ip' && { maxWidth: '180px' }}
                            placeholder={isEdit && name === 'password' ? 'Optional' : ''}
                        />
                    }
                </ControlGroup>
            );
        });
    },

    renderContent() {
        const availableItems = this.collection.fshRoles.getNameItems();
        const isEdit = this.model.state.get('type') === 'edit';
        const ipHelpMsg = <span>{_('Enter IP address and port number. Example: 127.0.0.1:8189')}</span>;
        const inputs = [
            { label: _('Federated Provider Name'), name: 'name', editDisabled: isEdit },
            { label: _('IP Address'), name: 'ip', help: ipHelpMsg },
            { label: _('User Account'), name: 'username', editDisabled: isEdit },
            { label: isEdit ? _('Change Password') : _('Account Password'), name: 'password' },
        ];
        const applicationApp = isEdit ? this.model.savedFederation.entry.content.get('splunk.app') : '';
        if (isEdit) {
            inputs[0].defaultValue = this.model.savedFederation.entry.get('name');
            const ip = this.model.savedFederation.entry.content.get('ip');
            const port = this.model.savedFederation.entry.content.get('splunk.port');
            const fullIp = `${ip}:${port}`;
            this.model.state.set('fullIp', fullIp);
            inputs[1].defaultValue = fullIp;
            inputs[2].defaultValue = this.model.savedFederation.entry.content.get('splunk.serviceAccount');
            this.selectedItems = this.collection.selectedRoles.map(model => model.entry.get('name'));
        }
        const errMsg = this.model.state.get('err') ? (
            <Message data-test="error" type="error">
                {this.model.state.get('err')}
            </Message>
        ) : null;
        const dropdownLabel = <Button label={_('Remote Splunk Enterprise')} disabled isMenu />;
        const appHelpMsg = <span>{_('Leave blank for Search & Reporting application. Example: search')}</span>;
        const docUrl = createDocsURL('dfs.federatedsearch_addfederatedprovider');

        return (
            <Modal
                style={{ width: '760px' }}
                data-test="federation-modal"
                onRequestClose={this.handleRequestClose}
                open={this.model.state.get('open')}
            >
                <Modal.Header title={this.title} onRequestClose={this.handleRequestClose} />
                <Modal.Body key="set-federation-modal" id="set-federation-modal">
                    {errMsg}
                    <FlashMessages
                        model={{
                            federation: this.model.federation,
                            federationContent: this.model.federation.entry.content,
                            fshPassword: this.model.fshPassword,
                            fshPasswordContent: this.model.fshPassword.entry.content,
                        }}
                    />
                    <div className="title">{_('Federated Provider Details')}</div>
                    <div className="sub-title">
                        {_('Enter the required information to connect to your federated provider.')}
                    </div>
                    <ControlGroup
                        labelWidth={this.labelWidth}
                        data-test="type-control-group"
                        label={_('Federated Provider Type')}
                        key="type-group"
                    >
                        {isEdit
                            ? <span
                                aria-label={_('Federated Provider Type:Remote Splunk Enterprise')}
                                className="input-label"
                            >
                                {_('Remote Splunk Enterprise')}
                            </span>
                            :
                            <Dropdown style={{ maxWidth: '210px' }} toggle={dropdownLabel} open={false} />
                        }
                    </ControlGroup>
                    {this.generateForm(inputs)}
                    <ControlGroup
                        labelWidth={this.labelWidth}
                        data-test="app-control-group"
                        label={_('Application Name')}
                        key="app-group"
                        help={appHelpMsg}
                    >
                        <Text
                            data-test="application-name"
                            onChange={this.handleChange}
                            placeholder={_('Optional')}
                            name="app"
                            defaultValue={applicationApp}
                        />
                    </ControlGroup>
                    <div className="title">{_('Roles')}</div>
                    <div className="sub-title">
                        <span className="link-string-text">
                            {_('Select a user role to run federated searches.')}
                        </span>
                        <Link data-test="role-selection-learn-more-link" to={docUrl} openInNewContext>
                            {_('Learn more')}
                        </Link>
                    </div>
                    <AccumulatorControl
                        modelattribute={this.modelAttribute}
                        model={this.model.role}
                        availableitems={availableItems}
                        selecteditems={this.selectedItems}
                    />
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test="cancel-btn"
                        appearance="secondary"
                        onClick={this.handleRequestClose}
                        label={_('Cancel')}
                    />
                    <Button
                        data-test="add-btn"
                        appearance="primary"
                        onClick={isEdit ? this.edit : this.submit}
                        label={isEdit ? _('Save') : _('Add')}
                    />
                </Modal.Footer>
            </Modal>
        );
    },

    getComponent() {
        return (
            <BackboneProvider store={this.store} model={this.model}>
                {this.renderContent()}
            </BackboneProvider>
        );
    },
});
