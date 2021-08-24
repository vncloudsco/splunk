(function(global) {

Splunk.namespace("Splunk.Logger");
/**
 * The getLogger factory provides a standard interface for implementing a logger program mode. Dependency on utils.js
 *
 * var logger = Splunk.Logger.getLogger("logger.js");
 * logger.info("This is a log message at ", new Date(), "showing a log!");
 *
 *
 * @param {String} fileName The name of the source file to log.
 * @param {Function} mode (Optional) The logging programming interface you wish to implement, defaults to Splunk.Logger.mode.Default if not defined.
 */
Splunk.Logger.getLogger = function(fileName, mode){
    var self;
    mode = mode || Splunk.Logger.mode.Default;
    try {
        self = new (mode)(fileName);
    }catch(err){
        self = this;
        throw(new Error("Splunk.Logger mode is undefined, not callable or thrown an exception. mode=" + mode + " and fileName=" + fileName + ". Check to make sure the mode you are defining exist (see: web.conf js_logger_mode) and is a proper closure. Stack trace:" + err));
    }
    return self;
};

/**
 * Exposes if a browser has a window console object.
 *
 * @method hasConsole
 * @return Boolean
 */
Splunk.Logger.hasConsole = function(){
    return (typeof(console)!="undefined")?true:false;
};
/**
 * Object to store logger program mode.
 */
Splunk.Logger.mode = {};
/**
 * A mode logger program that does nothing.
 */
Splunk.Logger.mode.None = function(){
    var self = this;
    self.info = self.log = self.debug = self.warn = self.error = self.trace = function(){};
};

/**
 * Leave an object key reference to Firebug.
 * Otherwise clients who have supplied
 *   this as a value in their conf will be thrown an error.
 *
 * Jira: https://jira.splunk.com/browse/SPL-133007
 */
Splunk.Logger.mode.Firebug = Splunk.Logger.mode.None;

/**
 * A mode logger program that implements logging to a server/splunk. Dependency on contrib/swfobject.js
 */
Splunk.Logger.mode.Server = function(fileName){
    var self = this,
        buffer = Splunk.Logger.mode.Server.Buffer.getInstance();
    /**
     * Formats a console call and pushes it to buffer.
     *
     * @method bufferPush
     * @param {arguments} args The arguments object from the original closure handler.
     * @param {String} level The console level called.
     */
    var bufferPush = function(args, level){
        args = args || [];
        for(var i = 0; i < args.length; i++) {
            if(typeof args[i] === 'object') {
                try {
                    args[i] = JSON.stringify(args[i]);
                }
                catch(e) { }
            }
        }
        var message = Array.apply(null, args).join(" ");
        var data = {level: level, 'class': fileName, message: message};
        buffer.push(data);
    };
    /**
     * The handlers for (new Splunk.Logger(fileName, [mode]))[level](arguments) calls.
     */
    self.info = function(){
        bufferPush(arguments, "info");
    };
    self.log = function(){
        bufferPush(arguments, "log");
    };
    self.debug = function(){
        bufferPush(arguments, "debug");
    };
    self.warn = function(){
        bufferPush(arguments, "warn");
    };
    self.error = function(){
        bufferPush(arguments, "error");
    };
    self.trace = function(){
        // try to generate a stack trace that can be sent to the server with log-level DEBUG
        // this will not actually give any meaningful information in IE, in which case this is a no-op
        var trace = '';
        try {
            var err = new Error();
            trace = err.stack.replace(/^Error/, '');
        }
        catch(e) { }
        if(trace) {
            bufferPush([trace], "debug");
        }
    };
};
/**
 * A buffer class to take care of purging and posting of logged messages.
 */
Splunk.Logger.mode.Server.Buffer = function(){
    var self = this,
        thread,
        buffer = [];
    /**
     * Posts buffer asynchronously to Splunk.Logger.Mode.Server.END_POINT,
     *
     * @method serverPost
     */
    var serverPost = function(){
        var data = JSON.stringify(buffer);
        $.post(Splunk.Logger.mode.Server.END_POINT, {"data":data});
    };
    /**
     * Posts and purges the existing buffer.
     *
     * @method purge
     */
    var purge = function(){
        serverPost();
        buffer = [];
    };
    /**
     * Checks the buffer, posts and purges if necessary.
     *
     * @method check
     */
    var check = function(){
        if(buffer.length>Splunk.Logger.mode.Server.MAX_BUFFER){
            purge();
        }
    };
    self.push = function(str){
        buffer.push(str);
        check();
    };
    /**
     * Checks the buffer at set interval and posts and purges if data exists.
     *
     * @method poller
     */
    self.poller = function(){
        if(buffer.length>0){
            purge();
        }
    };
    self.size = function(){
        return buffer.length;
    };
    self.Buffer = function(){
        thread = setInterval(self.poller, Splunk.Logger.mode.Server.POLL_BUFFER);
    }();
};
Splunk.Logger.mode.Server.Buffer.instance = null;
/**
 * Singleton reference to a shared buffer.
 *
 * @method getInstance
 */
Splunk.Logger.mode.Server.Buffer.getInstance = function(){
    if(Splunk.Logger.mode.Server.Buffer.instance==null){
        Splunk.Logger.mode.Server.Buffer.instance = new Splunk.Logger.mode.Server.Buffer();
    }
    return Splunk.Logger.mode.Server.Buffer.instance;
};
Splunk.Logger.mode.Server.END_POINT = Splunk.util.make_url(Splunk.util.getConfigValue("JS_LOGGER_MODE_SERVER_END_POINT", "util/log/js"));
Splunk.Logger.mode.Server.POLL_BUFFER = Splunk.util.getConfigValue("JS_LOGGER_MODE_SERVER_POLL_BUFFER", 1000);
Splunk.Logger.mode.Server.MAX_BUFFER = Splunk.util.getConfigValue("JS_LOGGER_MODE_SERVER_MAX_BUFFER", 100);
/**
 * The default system mode logger program, see web.conf js_logger_mode.
 */
Splunk.Logger.mode.Default = Splunk.Logger.mode[Splunk.util.getConfigValue("JS_LOGGER_MODE", "None")];
/**
 * Legacy Splunk.log compatibility
 */
Splunk.log = function(msg, category, src){
    Splunk.Logger.getLogger("logger.js").warn("WARNING! Splunk.log is now deprecated. See Splunk.Logger class for more details.", "Original Message:", msg, " Original Category:", category, "Original Source:", src);
};
/**
 * Legacy Backwards compatibility with 3.X
 */
var D = global.D = {};
D.logger = Splunk.Logger.getLogger("logger.js");
D.wrapper = function(str, level){
    D.logger.warn("WARNING! D.", level, "is now deprecated. See Splunk.Logger class for more details.", str);
};
D.debug = function(str){D.wrapper(str, "debug");};
D.error = function(str){D.wrapper(str, "error");};
D.warn = function(str){D.wrapper(str, "warn");};
/**
 * Augment util.logger to standard logger.
 */
Splunk.util.logger = Splunk.Logger.getLogger("util.js");

})(this);

