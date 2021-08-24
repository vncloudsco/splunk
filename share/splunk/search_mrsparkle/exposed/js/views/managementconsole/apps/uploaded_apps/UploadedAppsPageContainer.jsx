import _ from 'underscore';
import splunkUtils from 'splunk.util';
import Package from 'models/managementconsole/Package';
import TaskModel from 'models/managementconsole/Task';
import PropTypes from 'prop-types';
import React from 'react';
import UploadedAppsPage from 'views/managementconsole/apps/uploaded_apps/UploadedAppsPage';

const DOM_EXCEPTION_IS_DEFINED = typeof DOMException !== 'undefined';
const FILE_ERROR_IS_DEFINED = typeof FileError !== 'undefined';
const DOM_ERROR_IS_DEFINED = typeof DOMError !== 'undefined';
const UPLOAD_READ_PERMISSION_ERROR = _('Upload failed: Could not read the package, enable read permissions.').t();
const ACTION_CONFIRM_MESSAGE = [
    _('Are you sure you want to %s ').t(),
    _(' (version %s)').t(),
    _('?').t(),
    _(' This app might not run on a search head cluster deployment.').t(),
    _(' %s this app might cause Splunk Cloud to restart and be unavailable for some time.').t(),
];
const ACTION_DELETE_COMPLETE_MESSAGE = _(' has been deleted successfully.').t();
const ACTION_IN_PROGRESS_MESSAGE = [
    _('Splunk Cloud is %s ').t(),
    _(' (version %s').t(),
    _('). This process might take several minutes and cause Splunk Cloud to restart. ' +
        'Do not navigate away from this page until the app %s process completes.').t(),
];
const ACTION_FAIL_MESSAGE = _(' (version %s) could not be %s because the deploy task failed.').t();
const INSTALL_FAIL_DEPENDENCY_MESSAGE = [_(' (version %s) could not be installed because it requires the following ' +
    'app dependencies to be installed:').t(),
    _('Install the required app dependencies and try again.').t(),
];
const ACTION_SUCCESS_MESSAGE = _(' (version %s) was %s successfully!').t();
const APP_VALIDATION_FAILED_TITLE = _('App Validation Failed').t();
const APP_VALIDATION_REJECTED_TITLE = _('App Rejected').t();
const APP_VALIDATION_MORE_INFO_MESSAGE = _('Fix these issues and try again, ' +
    'or contact your administrator for details.').t();
const DUPLICATE_VERSION_ERROR_MESSAGE = [
    _('App validation failed:').t(),
    _(' (version %s) has already been uploaded.').t(),
    _('Update your package with a unique version and try again.').t(),
];
const APP_VALIDATION_UNSUPPORTED_DEPLOYMENT = _('App validation failed: App does not support %s deployments.').t();

const LABELS = {
    Upload: _('Upload').t(),
    Close: _('Close').t(),
    Cancel: _('Cancel').t(),
    Continue: _('Continue').t(),
    Install: _('Install').t(),
    Update: _('Update').t(),
    Delete: _('Delete').t(),
    More_Info: _('More Info').t(),
    Action_Confirm: _(' - Confirm').t(),
    Action_Complete: _(' - Complete').t(),
    Action_Fail: _(' - Fail').t(),
    Action_In_Progress: _(' - In Progress').t(),
};
const STATES = {
    NEW: 0,
    RUNNING: 1,
    FAIL: 2,
    SUCCESS: 3,
    STARTED: 4,
};
const DEPLOYMENT_TYPES = {
    _search_head_clustering: _('search head cluster').t(),
    _distributed: _('distributed').t(),
};

class UploadedAppsPageContainer extends React.Component {
    constructor(props) {
        super(props);
        this.fileReader = new FileReader();

        this.props.packages.on('sync', this.updatePackagesTable);
        this.props.deployTask.entry.content.on('change:state', this.handleDeployTaskChange);
        this.state = this.getDefaultState();
        this.authToken = undefined;
    }

    /**
     * Return a confirmation message
     * @packageModel
     *
     * @operationLabels     An array of words describing the operation, with different tenses and capitalization.
     *                      Refer to message templates and calling examples.
     *
     */
    getConfirmationMessage(packageModel, operationLabels) {
        const manifest = packageModel.entry.content.get('@manifest');

        const showSHCWarning = this.props.isSHC && !(
            manifest &&
            manifest.supported_deployments && (
                _.contains(manifest.supported_deployments, '_search_head_clustering') ||
                _.contains(manifest.supported_deployments, '*')
            )
        );

        return [
            splunkUtils.sprintf(ACTION_CONFIRM_MESSAGE[0], operationLabels[0]),
            <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
            splunkUtils.sprintf(ACTION_CONFIRM_MESSAGE[1], this.packageModel.getApp().version),
            ACTION_CONFIRM_MESSAGE[2],
            showSHCWarning ? ACTION_CONFIRM_MESSAGE[3] : '',
            splunkUtils.sprintf(ACTION_CONFIRM_MESSAGE[4], operationLabels[1]),
        ];
    }

    getDefaultState = () => ({
        title: _('Uploaded Apps').t(),
        description: _('App Management lets you securely upload and install private apps to Splunk Cloud ' +
                       'without making them visible to the public.').t(),
        packages: this.props.packages.models,
        uploadDialogOpen: false,
        status: undefined,
        responseMessage: '',
        statusData: undefined,
        file: null,
        fileUploadPercent: undefined,
        deploymentInProgress: false,
        buttonLabel: undefined,
        onRequestUpload: this.handleRequestUpload,
        onRequestOpen: this.handleRequestOpen,
        onRequestClose: this.handleRequestClose,
        onAddFile: this.handleAddFile,
        onRemoveFile: this.handleRemoveFile,
        pollPackagesCollection: this.props.pollPackagesCollection,
        action: undefined,
        actionDialogOpen: false,
        actionDialogTitle: LABELS.INSTALL_CONFIRM,
        taskStatus: undefined,
        onInstallPackageOpen: this.handleInstallPackageOpen,
        onInstallPackage: this.handleInstallPackage,
        canEdit: this.props.canEdit,
        onUpdatePackageOpen: this.handleUpdatePackageOpen,
        onUpdatePackage: this.handleUpdatePackage,
        onDeletePackageOpen: this.handleDeletePackageOpen,
        onDeletePackage: this.handleDeletePackage,
        onMoreInfoOpen: this.handleMoreInfoOpen,
        currentAppInstallDialog: undefined,
        loginDialogOpen: false,
        consent: false,
        onLoginOpen: this.handleLoginOpen,
        onLogin: this.handleLogin,
        onConsentToggle: this.handleConsentToggle,
    })

    updatePackagesTable = () => {
        this.setState({
            packages: this.props.packages.models,
        });
    }

    uploadFile = (file, authToken) => {
        this.package = new Package();
        return this.package.upload(file, authToken);
    }

    handleDeployTaskChange = () => {
        const deploymentInProgress = this.props.deployTask.inProgress();
        this.setState({
            deploymentInProgress,
        });
    }

    handleRequestUpload = () => {
        // Since undefined and 0 are treated the same by the progress bar,
        // set the fileUploadPercent to something non-zero to indicate progress
        this.setState({
            status: undefined,
            fileUploadPercent: 1,
        });

        this.uploadFile(this.state.file, this.authToken)
        .progress((e) => {
            // Use 95% of the progress bar for showing upload action,
            // Use the remaining 5% to wait for the xhr to return
            const fileUploadPercent = (e.loaded / e.total) * 95;
            this.setState({
                fileUploadPercent,
            });
        })
        .done((xhrArgs, responseMessage) => {
            const entry = xhrArgs[3].entry[0];
            const taskId = entry.name;
            const packageId = taskId;

            this.setState({
                status: 'success',
                responseMessage,
                packageId,
                buttonLabel: LABELS.Close,
            });

            this.props.packages.fetch().done(() => {
                this.props.pollPackagesCollection();
            });
        })
        .fail((xhrArgs, responseMessage) => {
            this.setState({
                status: 'error',
                responseMessage,
            });
        })
        .always(() => {
            // Set fileUploadPercent to undefined when the xhr returns
            // This will make the progress bar disappear
            this.setState({
                fileUploadPercent: undefined,
            });
        });
    }

    handleRequestClose = () => {
        this.setState({
            actionDialogOpen: false,
            uploadDialogOpen: false,
            loginDialogOpen: false,
        });
    }

    handleRequestOpen = () => {
        this.setState({
            loginDialogOpen: false,
            uploadDialogOpen: true,
            status,
            responseMessage: '',
            file: null,
            fileUploadPercent: undefined,
            buttonLabel: LABELS.Upload,
        });
    }

    handleAddFile = (file) => {
        if (this.fileReader.readyState === 1) {
            this.fileReader.abort();
        }

        this.fileReader.onload = () => {
            this.setState({
                file,
                fileUploadPercent: undefined,
                status: undefined,
            });
        };

        this.fileReader.onerror = (fileReaderErrorEvent) => {
            // See https://developer.mozilla.org/en-US/docs/Web/API/DOMException
            // and https://developer.mozilla.org/en-US/docs/Web/API/DOMError
            // and https://developer.mozilla.org/en-US/docs/Web/API/FileError
            if (fileReaderErrorEvent.target && fileReaderErrorEvent.target.error) {
                const fileReaderError = fileReaderErrorEvent.target.error;
                if ((DOM_EXCEPTION_IS_DEFINED && fileReaderError instanceof DOMException &&
                    fileReaderError.name === 'NotReadableError') ||
                    (DOM_ERROR_IS_DEFINED && fileReaderError instanceof DOMError &&
                    fileReaderError.name === 'NotReadableError') ||
                    (FILE_ERROR_IS_DEFINED && fileReaderError instanceof FileError &&
                    fileReaderError.code === FileError.NOT_READABLE_ERR)) {
                    this.setState({
                        status: 'error',
                        responseMessage: UPLOAD_READ_PERMISSION_ERROR,
                    });
                    this.fileReader.abort();
                }
            }
        };

        this.fileReader.readAsArrayBuffer(file);
    }

    handleRemoveFile = () => {
        if (this.fileReader.readyState === 1) {
            this.fileReader.abort();
        }

        this.setState({
            file: null,
            status: undefined,
        });
    }

    handleMoreInfoOpen = (packageModel) => {
        this.packageModel = packageModel;
        let title;
        let message;

        const errors = this.packageModel.getVettingErrors();
        if (errors && _.isString(errors[0].type)) {
            if (errors[0].type === 'AppUpload_DuplicateVersion') {
                title = splunkUtils.sprintf('%s - %s', APP_VALIDATION_REJECTED_TITLE, LABELS.More_Info);
                message = [
                    DUPLICATE_VERSION_ERROR_MESSAGE[0],
                    <ul key={this.packageModel.id}>
                        <li key={this.packageModel.id}><b>{errors[0].payload.app_label}</b>
                            {splunkUtils.sprintf(DUPLICATE_VERSION_ERROR_MESSAGE[1], errors[0].payload.app_version)}
                        </li>
                    </ul>,
                    DUPLICATE_VERSION_ERROR_MESSAGE[2],
                ];
            } else if (errors[0].type === 'AppInstall_UnsupportedDeployment') {
                title = splunkUtils.sprintf('%s - %s', APP_VALIDATION_FAILED_TITLE, LABELS.More_Info);
                message = [splunkUtils.sprintf(APP_VALIDATION_UNSUPPORTED_DEPLOYMENT,
                                               DEPLOYMENT_TYPES[errors[0].payload.deployment])];
            } else {
                title = splunkUtils.sprintf('%s - %s', APP_VALIDATION_FAILED_TITLE, LABELS.More_Info);
                message = [this.packageModel.getDmcErrorMessage()];
                if (message.length === 0) {
                    message = this.packageModel.getFailedVettingStatus();
                }
            }
            const payloadMessage = this.packageModel.getDmcErrorPayloadMessage();
            if (payloadMessage) {
                message.push(<ul key={this.packageModel.id}><li key={this.packageModel.id}>{payloadMessage}</li></ul>);
                message.push(APP_VALIDATION_MORE_INFO_MESSAGE);
            }
        } else {
            // default error message
            title = splunkUtils.sprintf('%s - %s', APP_VALIDATION_FAILED_TITLE, LABELS.More_Info);
            message = [this.packageModel.getDmcErrorMessage()];
        }

        this.setState({
            action: LABELS.More_Info,
            actionDialogOpen: true,
            actionDialogTitle: title || LABELS.More_Info,
            buttonLabel: LABELS.Close,
            status: 'error',
            taskStatus: STATES.FAIL,
            responseMessage: message,
        });
    }

    handleInstallPackageOpen = (packageModel) => {
        this.packageModel = packageModel;
        this.setState({
            action: LABELS.Install,
            actionDialogOpen: true,
            actionDialogTitle: LABELS.Install + LABELS.Action_Confirm,
            buttonLabel: LABELS.Cancel,
            status: 'info',
            taskStatus: STATES.NEW,
            responseMessage: this.getConfirmationMessage(packageModel,
                [_('install').t(), _('Installing').t()],
            ),
        });
    }

    handleInstallPackage = () => {
        this.setState({
            taskStatus: STATES.STARTED,
        });
        this.packageModel.install(this.state.action)
        .done((xhrArgs) => {
            const entry = xhrArgs[3].entry[0];
            const taskId = entry.name;

            this.installTask = new TaskModel();
            this.installTask.entry.set('name', taskId);

            this.setState({
                status: 'info',
                actionDialogTitle: LABELS.Install + LABELS.Action_In_Progress,
                taskStatus: STATES.RUNNING,
                responseMessage: [
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[0], _('installing').t()),
                    <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[1], this.packageModel.getApp().version),
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[2], _('install').t()),
                ],
            });

            const pollInstallTask = () => {
                this.installTask.beginPolling()
                .done(() => {
                    this.setState({
                        status: 'success',
                        responseMessage: [
                            <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                            splunkUtils.sprintf(ACTION_SUCCESS_MESSAGE, this.packageModel.getApp().version,
                                                _('installed').t()),
                        ],
                        actionDialogTitle: LABELS.Install + LABELS.Action_Complete,
                        buttonLabel: LABELS.Close,
                        taskStatus: STATES.SUCCESS,
                    });
                    this.props.packages.fetch();
                })
                .fail(() => {
                    this.setState({
                        status: 'error',
                        responseMessage: [
                            <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                            splunkUtils.sprintf(ACTION_FAIL_MESSAGE, this.packageModel.getApp().version,
                                                _('installed').t()),
                        ],
                        actionDialogTitle: LABELS.Install_Fail,
                        buttonLabel: LABELS.Close,
                        taskStatus: STATES.FAIL,
                    });
                });
            };

            pollInstallTask();
            this.installTask.on('serverValidated', (success, context, messages) => {
                const netErrorMsg = _.find(messages, msg =>
                    msg.type === 'network_error' || msg.text === 'Server error',
                );
                if (netErrorMsg) {
                    pollInstallTask();
                }
            }, this);
        })
        .fail((xhrArgs, responseMessage) => {
            let message;
            if (responseMessage && responseMessage.missing_dependencies) {
                message = [
                    <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                    splunkUtils.sprintf(INSTALL_FAIL_DEPENDENCY_MESSAGE[0], this.packageModel.getApp().version),
                    <p key={`${this.packageModel.id}_empty-text`} />,
                ];
                const listApps = responseMessage.missing_dependencies.map(app =>
                    <li key={app.app_id}>{ app.app_title }</li>,
                );
                message.push(<ul key={`${this.packageModel.id}_dependencies`} >{listApps}</ul>);
                message.push(INSTALL_FAIL_DEPENDENCY_MESSAGE[1]);
            } else {
                message = [responseMessage];
            }

            this.setState({
                status: 'error',
                responseMessage: message,
                actionDialogTitle: LABELS.Install + LABELS.Action_Fail,
                buttonLabel: LABELS.Close,
                taskStatus: STATES.FAIL,
            });
        });
    }

    handleUpdatePackageOpen = (packageModel) => {
        this.packageModel = packageModel;
        this.setState({
            action: LABELS.Update,
            actionDialogOpen: true,
            actionDialogTitle: LABELS.Update + LABELS.Action_Confirm,
            buttonLabel: LABELS.Cancel,
            status: 'info',
            taskStatus: STATES.NEW,
            responseMessage: this.getConfirmationMessage(packageModel,
                [_('update').t(), _('Updating').t()],
            ),
        });
    }

    handleUpdatePackage = () => {
        this.setState({
            taskStatus: STATES.STARTED,
        });
        this.packageModel.install(this.state.action)
        .done((xhrArgs) => {
            const entry = xhrArgs[3].entry[0];
            const taskId = entry.name;

            this.installTask = new TaskModel();
            this.installTask.entry.set('name', taskId);

            this.setState({
                status: 'info',
                actionDialogTitle: LABELS.Update + LABELS.Action_In_Progress,
                taskStatus: STATES.RUNNING,
                responseMessage: [
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[0], _('updating').t()),
                    <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[1], this.packageModel.getApp().version),
                    splunkUtils.sprintf(ACTION_IN_PROGRESS_MESSAGE[2], _('update').t()),
                ],
            });

            const pollInstallTask = () => {
                this.installTask.beginPolling()
                .done(() => {
                    this.setState({
                        status: 'success',
                        responseMessage: [
                            <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                            splunkUtils.sprintf(ACTION_SUCCESS_MESSAGE, this.packageModel.getApp().version,
                                                _('updated').t()),
                        ],
                        actionDialogTitle: LABELS.Update + LABELS.Action_Complete,
                        buttonLabel: LABELS.Close,
                        taskStatus: STATES.SUCCESS,
                    });
                    this.props.packages.fetch();
                })
                .fail(() => {
                    this.setState({
                        status: 'error',
                        responseMessage: [
                            <b key={this.packageModel.id}>{ this.packageModel.getApp().label }</b>,
                            splunkUtils.sprintf(ACTION_FAIL_MESSAGE, this.packageModel.getApp().version,
                                                _('updated').t()),
                        ],
                        actionDialogTitle: LABELS.Update + LABELS.Action_Fail,
                        buttonLabel: LABELS.Close,
                        taskStatus: STATES.FAIL,
                    });
                });
            };

            pollInstallTask();
            this.installTask.on('serverValidated', (success, context, messages) => {
                const netErrorMsg = _.find(messages, msg =>
                    msg.type === 'network_error' || msg.text === 'Server error',
                );
                if (netErrorMsg) {
                    pollInstallTask();
                }
            }, this);
        })
        .fail((xhrArgs, responseMessage) => {
            this.setState({
                status: 'error',
                responseMessage,
                actionDialogTitle: LABELS.Update + LABELS.Action_Fail,
                buttonLabel: LABELS.Close,
                taskStatus: STATES.FAIL,
            });
        });
    }

    handleConsentToggle = () => {
        this.setState({
            consent: !this.state.consent,
        });
    }

    handleLoginOpen = () => {
        this.setState({
            loginDialogOpen: true,
            consent: false,
            status: undefined,
        });
    }

    handleLogin = (username, password) => {
        this.setState({
            status: undefined,
        });
        this.package = new Package();
        const promise = this.package.login(username, password);
        promise
            .done((xhrArgs) => {
                this.authToken = xhrArgs[3];
                this.handleRequestOpen();
            })
            .fail((xhrArgs, responseMessage) => {
                this.setState({
                    status: 'error',
                    responseMessage,
                });
            });
        return promise;
    }


    handleDeletePackageOpen = (packageModel) => {
        this.packageModel = packageModel;

        const app = this.packageModel.getApp();
        const responseMessage = [splunkUtils.sprintf(ACTION_CONFIRM_MESSAGE[0], _('delete').t())];

        if (app) {
            responseMessage.push(
                <b key={this.packageModel.id}>{ app.label }</b>,
                splunkUtils.sprintf(ACTION_CONFIRM_MESSAGE[1], app.version),
            );
        } else {
            responseMessage.push(<b key={this.packageModel.id}>{ this.packageModel.getUploadedFileName() }</b>);
        }
        responseMessage.push(ACTION_CONFIRM_MESSAGE[2]);
        this.setState({
            action: LABELS.Delete,
            actionDialogOpen: true,
            actionDialogTitle: LABELS.Delete + LABELS.Action_Confirm,
            buttonLabel: LABELS.Cancel,
            status: 'info',
            taskStatus: STATES.NEW,
            responseMessage,
        });
    }

    handleDeletePackage = () => {
        this.setState({
            taskStatus: STATES.STARTED,
        });
        this.packageModel.delete(this.state.action)
        .done(() => {
            const app = this.packageModel.getApp();
            const appId = app ? app.label : this.packageModel.getUploadedFileName();
            const responseMessage = [
                <b key={this.packageModel.id}>{appId}</b>,
                ACTION_DELETE_COMPLETE_MESSAGE,
            ];
            this.setState({
                status: 'success',
                actionDialogTitle: LABELS.Delete + LABELS.Action_Complete,
                responseMessage,
                buttonLabel: LABELS.Close,
                taskStatus: STATES.SUCCESS,
            });
        })
        .fail((xhrArgs, responseMessage) => {
            this.setState({
                status: 'error',
                actionDialogTitle: LABELS.Delete + LABELS.Action_Fail,
                responseMessage: responseMessage.t(),
                buttonLabel: LABELS.Cancel,
                taskStatus: STATES.FAIL,
            });
        });
    }

    render() {
        return <UploadedAppsPage {...this.state} />;
    }
}

UploadedAppsPageContainer.propTypes = {
    packages: PropTypes.shape({
        models: PropTypes.arrayOf(PropTypes.shape({})),
        on: PropTypes.func,
        fetch: PropTypes.func,
    }),
    pollPackagesCollection: PropTypes.func,
    deployTask: PropTypes.shape({
        entry: PropTypes.shape({
            content: PropTypes.shape({
                on: PropTypes.func,
            }),
        }),
        inProgress: PropTypes.func,
    }),
    canEdit: PropTypes.bool,
    isSHC: PropTypes.bool,
};

UploadedAppsPageContainer.defaultProps = {
    packages: undefined,
    pollPackagesCollection: undefined,
    deployTask: undefined,
    canEdit: false,
    isSHC: false,
};

export default UploadedAppsPageContainer;
