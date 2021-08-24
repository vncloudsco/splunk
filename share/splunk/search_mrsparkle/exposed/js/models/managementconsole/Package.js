define([
        'jquery',
        'underscore',
        'models/managementconsole/Configuration',
        'models/managementconsole/Task',
        'util/time',
        'util/splunkd_utils',
        'splunk.util'
    ],
    function(
        $,
        _,
        ConfigurationModel,
        TaskModel,
        timeUtil,
        splunkdUtils,
        splunkUtil
    ) {
        var STATUS = {
            'unknown': _('Unknown').t(),
            'installed': _('Installed').t(),
            'approved': _('Approved').t(),
            'vetting': _('Vetting').t(),
            'rejected': _('Rejected').t(),
            'in_manual_review': _('In manual review').t(),
            'failed': _('Failed').t()
        },

        STRINGS = {
            NO_VERSION: _('N/A').t()
        },

        DMC_ERROR_MESSAGES = {
            'AppUpload_NoPackage': _('Upload failed: No package provided.').t(),
            'AppUpload_EmptyPackage': _('Upload failed: Package is empty.').t(),
            'AppUpload_LargePackage': _('Upload failed: Package is too large, must be less than 128MB.').t(),
            'AppUpload_InspectAuthentication': _('App Inspect failed: Could not authenticate.').t(),
            'AppUpload_InspectValidation': _('App Inspect failed: Could not validate package.').t(),
            'AppUpload_InspectConnection': _('App Inspect failed: Could not connect.').t(),
            'AppUpload_InspectStatus': _('App Inspect failed: Could not get status.').t(),
            'AppUpload_InspectReport': _('App Inspect failed: Could not get report.').t(),
            'AppUpload_AccessDenied': _('You do not have permission to upload apps. ' +
                'Contact your administrator for details.').t(),
            'AppInstall_AlreadyExists': _('Install failed: App already exists.').t(),
            'AppInstall_NoPackage': _('Install failed: Package cannot be found.').t(),
            'AppInstall_BadPackage': _('Install failed: Could not extract package details.').t(),
            'AppInstall_AppIDConflict': _('Install failed: App has the same id as a public app. ' +
                'Update this private app with a unique id to remove this conflict.').t(),
            'AppInstall_AccessDenied': _('You do not have permission to install apps. ' +
                'Contact your administrator for details.').t(),
            'AppInstall_UnsupportedStaticDependencies': _(
                'Install failed: Cannot install packages that contain statically packaged dependencies. ' +
                'Only dynamically declared dependencies are supported. Remove the static packages and try again.').t(),
            'AppInstall_ServerException': _('Install failed: %s').t(),
            'AppInstall_UnsupportedDeployment': _('Install failed: App does not support %s deployments.').t(),
            'Deploy_Failed': _('Application cannot be installed because the previous deployment task has failed.').t(),
            'Deploy_Locked': _('Application cannot be installed while deployment operations are locked. ' +
                'This might happen during maintenance windows. If this situation is unexpected or goes on ' +
                'for too long, contact Splunk Support.').t(),
            'Deploy_InProgress': _('Application cannot be installed while a deployment task is still in progress.').t(),
            'ExternalAppsDiscovery_Failed':  _('Application cannot be installed because the previous external apps ' +
                'discovery task has failed.').t(),
            'AppUpdate_AlreadyUpToDate': _('Update failed: App is already up to date.').t(),
            'AppUpload_DuplicateVersion': _('App validation failed: Version already in use.').t(),
            'AppUpload_InvalidContent': _('App validation failed: Package contains invalid content. ' +
                'Only regular files and directories are permitted.').t(),
            'AppDelete_NoPackage': _('Delete failed: Package cannot be found.'),
            'AppDelete_PackageInUse': _('Delete failed: Package is in use.')
        },

        APP_UPLOAD_INCORRECT_CREDENTIALS = _('Incorrect username or password').t(),

        TIMEOUT_ERROR_MESSAGE = _('Upload failed: Connection timed out. Try again later.').t(),

        APP_VETTING_ERROR_MESSAGE = _('App validation failed to complete').t(),

        GENERIC_ERROR_MESSAGE = _('Unknown failure: Contact your administrator for details or try again later.').t(),

        // Prevent large packages from being uploaded
        LARGE_PACKAGE_ERROR_MESSAGE = _('Upload failed: Package is too large, must be less than 128MB.').t(),

        SUCCESSFUL_UPLOAD_MESSAGE = _('%s was uploaded successfully!').t(),

        DEPLOYMENT_TYPES = {
            '_search_head_clustering': _('search head cluster').t(),
            '_distributed': _('distributed').t()
        },

        // This is the status text of jQuery XHRs when the request times out.
        JQXHR_TIMEOUT = 'timeout';

        var packageModel = ConfigurationModel.extend(
            {
                maxUploadFileSize: 256 * 1024 * 1024,

                isPrivate: function() {
                    return true;
                },

                getStatus: function() {
                    return STATUS[this.entry.content.get('status')];
                },

                getSubmittedAt: function() {
                    return timeUtil.convertToLocalTime(this.entry.content.get('submittedAt'));
                },

                getApp: function() {
                    return this.entry.content.get('@app');
                },

                getUploadedFileName: function() {
                    return this.entry.content.get('uploadedFile');
                },

                getVersion: function() {
                    return this.getApp() && this.getApp().version || STRINGS.NO_VERSION;
                },

                isVetting: function() {
                    return this.getStatus() === STATUS['vetting'];
                },

                failedVetting: function() {
                    return this.getStatus() === STATUS['failed'] || this.getStatus() === STATUS['unknown'];
                },

                getVettingErrors: function() {
                    return this.entry.content.get('@errors');
                },

                getFailedVettingStatus: function() {
                    return APP_VETTING_ERROR_MESSAGE;
                },

                getDmcErrorMessage: function() {
                    var errors = this.entry.content.get('@errors');
                    if (errors && _.isString(errors[0].type) && DMC_ERROR_MESSAGES[errors[0].type]) {
                        return DMC_ERROR_MESSAGES[errors[0].type];
                    }
                    return GENERIC_ERROR_MESSAGE;
                },

                getDmcErrorPayloadMessage: function() {
                    var errors = this.entry.content.get('@errors');
                    if (errors && errors[0].payload) {
                        return errors[0].payload.message;
                    }
                    return null;
                },

                getLink: function(link) {
                    return this.entry.links.get(link);
                },

                getFullLink: function(link) {
                    return splunkdUtils.fullpath(this.getLink(link));
                },

                upload: function(file, authToken) {
                    var dfd = $.Deferred(),
                        formData = new FormData();

                    if (file.size > this.maxUploadFileSize) {
                        dfd.rejectWith(dfd, [null, LARGE_PACKAGE_ERROR_MESSAGE]);
                    } else {
                        formData.append('data', file);
                        formData.append('token', authToken);

                        this.save({}, {
                            url: splunkdUtils.fullpath("/services/dmc/packages-upload"),
                            data: formData,
                            cache: false,
                            contentType: false,
                            processData: false,
                            xhr: function(){
                                var xhr = new window.XMLHttpRequest();
                                xhr.upload.addEventListener("progress", dfd.notify);
                                return xhr;
                            }.bind(this)
                        }).done(function(response) {
                            var args = Array.prototype.slice.call(arguments);
                            args.push(response);
                            dfd.resolveWith(dfd, [args, splunkUtil.sprintf(SUCCESSFUL_UPLOAD_MESSAGE, file.name)]);
                        }).fail(function(response, statusText) {
                            var status = response.status,
                                responseJSON = response && response.responseJSON,
                                type = responseJSON && responseJSON.type,
                                message = '';

                            if (status === 400 && _.isString(type)) {
                                message = DMC_ERROR_MESSAGES[type] || '';
                            } else if (statusText === JQXHR_TIMEOUT) {
                                message = TIMEOUT_ERROR_MESSAGE;
                            }

                            dfd.rejectWith(dfd, [arguments, message]);
                        });
                    }

                    return dfd.promise();
                },

                install: function(action) {
                    var dfd = $.Deferred();

                    this.save({}, {
                        url: this.getFullLink(action.toLowerCase()),
                        data: JSON.stringify({}),
                        contentType: 'application/json',
                        parse: false
                    }).done(function(response) {
                            var args = Array.prototype.slice.call(arguments);
                            args.push(response);
                            dfd.resolveWith(dfd, [args]);
                    }).fail(function(response, statusText) {
                        var status = response.status,
                            responseJSON = response && response.responseJSON,
                            type = responseJSON && responseJSON.type,
                            message = '';

                        if (status === 400 && _.isString(type)) {
                            if (type === 'AppInstall_SlimError') {
                                message = responseJSON.payload;
                            } else if (type === 'AppInstall_ServerException') {
                                message = splunkUtil.sprintf(DMC_ERROR_MESSAGES[type], responseJSON.payload.message);
                            } else if (type === 'AppInstall_UnsupportedDeployment') {
                                message = splunkUtil.sprintf(DMC_ERROR_MESSAGES[type],
                                                             DEPLOYMENT_TYPES[responseJSON.payload.deployment]);
                            } else {
                                message = DMC_ERROR_MESSAGES[type] || '';
                            }
                        }

                        dfd.rejectWith(dfd, [arguments, message]);
                    });

                    return dfd.promise();
                },

                login: function(username, password) {
                    var dfd = $.Deferred();

                    this.save({}, {
                        url: splunkdUtils.fullpath('dmc/packages-upload:login'),
                        cache: false,
                        contentType: 'application/json',
                        data: JSON.stringify({
                            username: username,
                            password: password
                        })
                    }).done(function(response) {
                        var args = Array.prototype.slice.call(arguments);
                        args.push(response.entry[0].content);
                        dfd.resolveWith(dfd, [args]);
                    }).fail(function(response, statusText) {
                        var status = response.status,
                            responseJSON = response && response.responseJSON,
                            type = responseJSON && responseJSON.type,
                            message = '';

                        if (status === 400 && _.isString(type)) {
                            if (type === 'AppUpload_InspectAuthentication') {
                                message = APP_UPLOAD_INCORRECT_CREDENTIALS;
                            } else {
                                message = DMC_ERROR_MESSAGES[type] || '';
                            }
                        }

                        dfd.rejectWith(dfd, [arguments, message]);
                    });

                    return dfd.promise();
                },

                'delete': function(action) {
                    var dfd = $.Deferred();

                    this.destroy({
                        url: this.getFullLink(action.toLowerCase()),
                        wait: true // don't update the model until REST call is complete
                    }).done(function(response) {
                        dfd.resolve();
                    }).fail(function(response, statusText) {
                        var status = response.status,
                            responseJSON = response && response.responseJSON,
                            type = responseJSON && responseJSON.type,
                            message = '';
                        if (status === 400 && _.isString(type)) {
                            message = DMC_ERROR_MESSAGES[type] || '';
                        }
                        dfd.rejectWith(dfd, [arguments, message]);
                    });

                    return dfd.promise();
                }

            }
        );

        return packageModel;
    }
);
