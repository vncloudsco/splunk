import React from 'react';
import _ from 'underscore';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import Modal from '@splunk/react-ui/Modal';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Button from '@splunk/react-ui/Button';
import Select from '@splunk/react-ui/Select';
import Text from '@splunk/react-ui/Text';
import SearchInput from 'views/shared/react/searchinput/SearchInput';
import UserModel from 'models/shared/User';
import FlashMessages from 'views/shared/react/FlashMessages';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name CreateFederatedSearchModal
     * @extends {views.ReactAdapterBase}
     * @description A modal for creating a new federated search.
     *
     * @param {Object} options
     * @param {Object} options.model The model supplied to this class
     * @param {Object} options.collection The collection supplied to this class
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.store = {};

        // default app is search
        this.model.inmem.entry.acl.set({ app: 'search' }, { silent: true });

        this.listenTo(this.model.state, 'change:open', this.render);
    },

    renderContent() {
        const SplSearchInput = (
            <SearchInput
                model={{
                    user: this.model.user,
                    content: this.model.inmem.entry.content,
                    application: this.model.application,
                    searchAttribute: 'search',
                    searchAssistant: (this.model.user.getSearchAssistant() === UserModel.SEARCH_ASSISTANT.FULL)
                        ? UserModel.SEARCH_ASSISTANT.COMPACT
                        : undefined,
                }}
                collection={{
                    searchBNFs: this.collection.searchBNFs,
                }}
            />
        );
        const open = this.model.state.get('open');
        const defaultAppName = this.model.inmem.entry.acl.get('app');
        const defaultApp = this.collection.appLocals.findByEntryName(defaultAppName);
        const appItems = this.collection.appLocals.getFilteredNameItems().map(
            app => <Select.Option key={app.value} value={app.value} label={app.label} />,
        );
        const providers = this.collection.federations.getNameItems().map(
            provider => <Select.Option key={provider.value} value={provider.value} label={provider.label} />,
        );
        return (
            <Modal
                data-test="create-federated-search-modal"
                onRequestClose={this.options.onClose}
                open={open}
                style={{ width: '600px' }}
            >
                <Modal.Header
                    title={_('Create Federated Search').t()}
                    onRequestClose={this.options.onClose}
                />
                <Modal.Body>
                    <FlashMessages
                        model={{
                            inmem: this.model.inmem,
                            content: this.model.inmem.entry.content,
                        }}
                    />
                    <ControlGroup label={_('Title').t()}>
                        <Text
                            data-test="title"
                            autoFocus
                            ref={
                                // eslint-disable-next-line no-return-assign
                                (c => (this.model.state.set('titleRef', c)))
                            }
                            onChange={this.options.onTitleChanged}
                        />
                    </ControlGroup>
                    <ControlGroup label={_('Description').t()}>
                        <Text
                            data-test="description"
                            placeholder={_('optional').t()}
                            onChange={this.options.onDescriptionChanged}
                        />
                    </ControlGroup>
                    <ControlGroup label={_('Search').t()}>
                        {SplSearchInput}
                    </ControlGroup>
                    <ControlGroup label={_('App').t()}>
                        <Select
                            data-test="application"
                            onChange={this.options.onApplicationChanged}
                            defaultValue={defaultApp.id}
                        >
                            {appItems}
                        </Select>
                    </ControlGroup>
                    <ControlGroup label={_('Federated Provider').t()}>
                        <Select
                            data-test="federated-provider"
                            onChange={this.options.onProviderChanged}
                            placeholder={_('Select provider...').t()}
                        >
                            {providers}
                        </Select>
                    </ControlGroup>
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        data-test="cancel-button"
                        appearance="secondary"
                        onClick={this.options.onClose}
                        label={_('Cancel').t()}
                    />
                    <Button
                        data-test="save-button"
                        appearance="primary"
                        onClick={this.options.onSubmit}
                        label={_('Save').t()}
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
