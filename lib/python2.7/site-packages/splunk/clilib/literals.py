#   Version 4.0
# All help strings for clilib.
# Help string declarations, and help string calls (addHelp's...)


#Use this command to test for ASCII weirdness
#sed -e "s/[-0-9A-Za-z\"',()#%\^\*_+=\[\/\.:;\t |<>{}\$\!\&\?,@]*//g" -e "s/\]//g" literals.py | grep -v '^\w*$

# this stuff is not to be messed with
helpStrs = {}
def addHelp(cmd, hShort, hLong):
    global helpStrs
    helpStrs[cmd] = {"helpShort" : hShort, "helpLong" : hLong}

###################################################################
######################   Begin Help String Declarations  ###################

###################################################################
# Command definitions

ANONYMIZE_LONG="""
     Use anonymize to replace identifying data (usernames, IP addresses, domain
     names, etc.) with fictional values that maintain the same word length and
     event type. Anonymizing data lets Splunk users share log data without
     revealing  confidential or personal information from their networks.

     You can specify custom rules for Splunk's anonymizer by using the
     parameters to specify your own word lists.

     Syntax:

        anonymize file -source [-parameter <value>]...

     Objects:

        source           relative or full path to file to anonymize

     Parameters:

        public-terms     file containing a list of locally-used words to NOT anonymize
                         (default= $SPLUNK_HOME/etc/anonymizer/public-terms.txt)

        private-terms    file containing a list of words to anonymize
                         (default= $SPLUNK_HOME/etc/anonymizer/private-terms.txt)

        name-terms       file containing a list of common English personal
                         names that Splunk uses to anonymize names with
                         (default= $SPLUNK_HOME/etc/anonymizer/names.txt)

        dictionary       file containing a global list of commonly-used
                         words to NOT anonymize - unless they are in the
                         private-terms file
                         (default= $SPLUNK_HOME/etc/anonymizer/dictionary.txt)

        timestamp-config  file that determines how timestamps are parsed
                          (default= $SPLUNK_HOME/etc/anonymizer/
                          anonymizer-time.ini)

     Examples:

        ./splunk anonymize file -source /tmp/messages

        ./splunk anonymize file -source /tmp/messages -name_terms $SPLUNK_HOME/bin/Mynames.txt

        ./splunk anonymize file -source ../README-splunk.txt -name_terms ./etc/anonymizer/names.txt


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

CLEAN_LONG="""
    The clean command deletes event data, global data, and user account data
    from your Splunk installation.

    Permanently remove event data from an index by typing, "./splunk clean
    eventdata". Set the index parameter to delete event data from a specific
    index. If you don't set an index, Splunk deletes all event data from all
    indexes.

    Remove global data (tags and source type aliases for events you indexed)
    from Splunk by typing, "./splunk clean globaldata".

    Remove user data (user accounts you've created) from Splunk by typing,
    "./splunk clean userdata".

    ** Caution: **
    Removing data is irreversible. Use caution when choosing what data to
    remove from your Splunk installation. If you want to get your data back,
    you must re-index the applicable data sources.

    ** Note: **
    Add the -f parameter to force clean to skip its confirmation prompts.


     Syntax:

        clean  eventdata [-f] [-index <name>] [--remote=<bool>]

        clean  (globaldata|userdata|locks|all|deployment-artifacts) [-f]

        clean  all [--remote=<bool>]

        clean  inputdata [<scheme>]

        clean  kvstore [-f] (-local|-all|-app <appname>|-app <appname> -collection <collection name>|-cluster)

        clean  raft [-f]

     Objects:

          eventdata    exported events indexed as raw log files

          globaldata   host tags, source type aliases

          userdata     user accounts

          inputdata    modular inputs checkpoint data

          locks        internal lockfiles (only on advice of Splunk Support)

          kvstore      application key/value-store database

          raft         search head cluster raft configuration

          all          everything above; *not* deployment-artifacts

          deployment-artifacts        files created by instance having acted as
                                      Deployment Server or Deployment Client
                                      (only on advice of Splunk Support)
     Required Parameters:

         eventdata     if no index specified, the default is to clean all
                       indexes

         inputdata     if no modular input scheme specified, the default is
                       to clean data for all registered modular inputs

         kvstore       no default mode is assumed, a valid mode must be given

     Optional Parameters:

         eventdata     index        name of index whose eventdata should be cleaned
                       f            forces clean to skip its confirmation prompt
                                    (Cleaning cannot be undone. Use carefully!)
                       --remote=    <true/ false> to override default configuration and clean/ skip the remote index

         globaldata    f            forces clean to skip its confirmation prompt
                                    (Cleaning cannot be undone. Use carefully!)

         userdata      f            forces clean to skip its confirmation prompt
                                    (Cleaning cannot be undone. Use carefully!)

         kvstore       local        drop local key value store database
                       all          delete data from all app collections
                       app          delete data from specific app collections
                       collection   delete data from specific collection
                                    (can be used only with app parameter)
                       cluster      drop current kvstore cluster configuration
                                    (use when you want to move current instance
                                    out of SHC/SHP and keep data)
                       f            forces clean to skip its confirmation prompt
                                    (Cleaning cannot be undone. Use carefully!)

         raft          f            forces clean to skip its confirmation prompt
                                    (Cleaning cannot be undone. Use carefully!)

         all           --remote=    <true/ false> to override default configuration and clean/ skip the remote index

     Examples:

          ./splunk clean eventdata

          ./splunk clean globaldata

          ./splunk clean eventdata -index main -f

          ./splunk clean eventdata --remote=true

          ./splunk clean inputdata s3


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation
"""

CREATE_LONG="""

     Builds a new app from a template.

     It provides a scaffolding for development of new apps.

     Syntax:

        create app appname [-parameter <value>]

     Parameters:

        appname     name of the new app

        template    if no template specified, default template will be used

     Examples:

        ./splunk create app myNewApp -template sample_app

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

CLUSTER_LONG="""

        Clustering helps you setup cloned indexer configuration, to make computing, storage and networking resources more
        robust to single node failure. A cluster would typically have a single master server and several peer servers. When one
        of the peers goes down, the data on that node is available for searching on backup nodes(i.e. the other peers). Some of
        the basic parameters that can be used to setup one such cluser are:

        Parameters:

                 mode                    Controls the mode of the current instance in the cluster
                                         Acceptable values for which include [master|slave|searchhead|disabled]
                 cxn_timeout             Low level timeout, in seconds, for establishing connection between cluster nodes
                                          (can be configured only at splunk instances configured as the master)
                 send_timeout            Low level timeout, in seconds, for sending data between cluster nodes
                                          (can be configured only at splunk instances configured as the master)
                 rcv_timeout             Low level timeout, in seconds, for receiving data between cluster nodes
                                          (can be configured only at splunk instances configured as the master)
                 rep_send_timeout        Low level timeout, in seconds, for sending replication data between cluster nodes
                                          (can be configured only at splunk instances configured as the master)
                 rep_rcv_timeout         Configures timeout for receiving replicated bucket
                                          (can be configured only at splunk instances configured as the master)
                 replication_factor      Controls the number of copies of each bucket maintained in the cluster
                                          (can be configured only at the master)
                 search_factor           Configures search factor ie number of searchable copies of each bucket
                                          (can be configured only at splunk instances configured as the master)
                 heartbeat_timeout       Controls the hearbeat for the cluster
                                          (can be configured only at splunk instances configured as the master)
                 restart_timeout         Controls the amount of time the master waits for the peer to readd itself after a restart
                                          (can be configured at the master)
                 replication_port        Controls the port dedicated for replication data, at the peers.
                                          (must be configured at the peer)
                 master_uri              Controls the URI of the cluster master to which this slave/peer node connects
                                          (can be used only at splunk instances configured as the peer)
                 max_peer_build_load     Controls the max number of concurrent jobs to make bucket searchable
                 max_peer_rep_load       Controls the max number of concurrent replications that peer can take
                                           part in as target
                 secret                  Controls the secret key between the master and the peer. Needed if the secret key
                                          is configured at the master. Appears in the server.conf as pass4SymmKey
                 use_batch_mask_changes  Controls how bucket mask changes are processed (In batch or individually) in a cluster.
                                          (can be configured only at the master)

        Syntax:

        Commands that can be used on the cluster master to view and edit various clustering configurations:

                  [list|edit] cluster-config

                  list [master-info|cluster-generation|cluster-peers|cluster-buckets]

                  [list|remove] excess-buckets

                  [remove] cluster-peers

                  [apply|validate|rollback] cluster-bundle

                  [show] [cluster-bundle-status|maintenance-mode|primaries-backup-status]

                  rebalance cluster-data

                  [rolling-restart] cluster-peers

                  [enable|disable|show] maintenance-mode

                  [set] indexing-ready

          [upgrade-init] cluster-peers

          [upgrade-finalize] cluster-peers

         Commands that can be used on the cluster slave/peer to view and edit various clustering configurations:

                  [list|edit] cluster-config

                  list [peer-info|peer-buckets]

                  offline [--enforce-counts]

        Required Parameters:

                  See help for individual commands. For listing various configuration parameters, use "help list". Alternatively,
                 use "help [object|topic]" to get help on particular objects.

        Optional Parameters:

                  See help for individual commands by using "help [object|topic]"

        Examples:

          (For Cluster master)
                    ./splunk list cluster-config
                    ./splunk edit cluster-config : To get a complete list of all the editable configurations, see 'splunk help edit'
                    ./splunk list master-info
                    ./splunk list cluster-generation
                    ./splunk list cluster-peers
                    ./splunk list cluster-buckets
                    ./splunk list excess-buckets
                    ./splunk rebalance cluster-data -action start|stop|status
                    ./splunk remove excess-buckets
                    ./splunk remove cluster-peers
                    ./splunk apply cluster-bundle
                    ./splunk validate cluster-bundle
                    ./splunk rollback cluster-bundle
                    ./splunk show cluster-bundle-status
                    ./splunk show cluster-bundle-status --verbose
                    ./splunk show cluster-status
                    ./splunk show cluster-status --verbose
                    ./splunk show maintenance-mode
                    ./splunk show primaries-backup-status
                    ./splunk rolling-restart cluster-peers
                    ./splunk enable maintenance-mode
                    ./splunk disable maintenance-mode
            ./splunk upgrade-init cluster-peers
            ./splunk upgrade-finalize cluster-peers

          (For Cluster Slave/Peer)
                    ./splunk list cluster-config
                    ./splunk edit cluster-config
                    ./splunk list peer-info
                    ./splunk list peer-buckets
                    ./splunk offline [--enforce-counts]

          (For Cluster searchhead)
                    ./splunk add cluster-master
                    ./splunk edit cluster-master
                    ./splunk list cluster-master
                    ./splunk remove cluster-master

        For additional help on a particular command, view help for the particular object using "./splunk help [command]".

        Complete documentation is available online at: "https://docs.splunk.com/Documentation"

"""

OFFLINE_PEER="""

          Used to shutdown the peer in a way that doesn't affect existing searches. The master rearranges the primary peers for buckets, and actually
        fixes up the cluster state as much as possible in case the enforce-counts flag is set. ie trying to maintain the replication and search factor
        for the cluster.

     Syntax:

        offline [--flag]

     Required Parameters:

          auth       <username>:<password>

     Optional Parameters:

          NONE

     Flags:

        enforce-counts  If this flag is used, the cluster is completely fixed up before this peer is taken down.
                        ie the Replication factor and search factor for the cluster are honored to the maximum possible extent.

                        Without this flag, the master will simple rearrange the primaries and timeout after 5 minutes(by default),
                        The amount of time the master waits for the peer is configurable using the "restart_timeout" parameter using
                        the "./splunk edit cluster-config" command.

     Examples:

          ./splunk offline -auth admin:changeme

          ./splunk offline --enforce-counts

          ./splunk offline


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

SHPOOL_LONG="""

        A search head cluster consists of a group of search heads that act in unison to increase the search/compute capability
        of your system. It makes your enterprise more robust to node failures. In a search head cluster, one member is dynamically
        elected the captain. Dynamic election provides high availability and auto-failover. The cluster keeps configurations in sync
        across all cluster members. This allows you to use any search head to modify search-related configurations.

         Some of the parameters that can be used to set up a cluster are:

        Parameters:

                 cxn_timeout           Low level timeout, in seconds, for establishing connection between cluster members
                                                  (can be configured only at the captain)
                 send_timeout          Low level timeout, in seconds, for sending data between cluster members
                                                  (can be configured only at the captain)
                 rcv_timeout           Low level timeout, in seconds, for receiving data between cluster members
                                                  (can be configured only at the captain)
                 rep_send_timeout      Low level timeout, in seconds, for sending replication data between cluster members
                                                  (can be configured only at the captain)
                 rep_rcv_timeout       Configures timeout for receiving replicated search artifacts
                                                  (can be configured only at the captain)
                 replication_factor    Controls the number of copies of each search artifact maintained in the cluster
                                                  (can be configured only at the captain)
                 heartbeat_timeout     Controls the heartbeat for the cluster
                                                  (can be configured only at the captain)
                 restart_timeout        Controls the amount of time the captain waits for a member to re-add itself after a restart
                                                  (can be configured only at the captain)
                 replication_port       Controls the port dedicated for replication data.
                 captain_uri            Controls the URI of the cluster captain to which this member connects
                 max_peer_rep_load      Controls the max number of concurrent replications that member can take part in as target
                 secret                 Controls the secret key used by the cluster members. Appears in server.conf as pass4SymmKey.

        Syntax:

         Commands that can be used on any cluster member to setup, view and edit various configurations:

                  [init|edit|list] shcluster-config

                  show shcluster-status

                  list shcluster-captain-info

                  list shcluster-members

                  list [shcluster-member-info|shcluster-member-artifacts]

                  add shcluster-member

                  resync shcluster-replicated-config

                  clean raft

                  edit shcluster-config -manual_detention on

                  upgrade-init shcluster-members

                  upgrade-finalize shcluster-members

        Commands that can only be used on the cluster captain:

                  bootstrap shcluster-captain

                  transfer shcluster-captain

                  list [shcluster-artifacts|shcluster-scheduler-jobs]

                  list shcluster-configuration-set

                  rolling-restart shcluster-members

          rotate shcluster-splunk-secret

        Commands that can only be used on the cluster deployer:

                  apply shcluster-bundle

        Required Parameters:

                 See help for individual commands. For listing various configuration parameters, use "help list". Alternatively,
                 use "help [object|topic]" to get help on particular objects.

        Optional Parameters:

                  See help for individual commands by using "help [object|topic]"

        Examples:

                    ./splunk list shcluster-config
                    ./splunk edit shcluster-config : To get a complete list of all the editable configurations, see 'splunk help edit'
                    ./splunk edit shcluster-config -manual_detention on
                    ./splunk list shcluster-captain-info
                    ./splunk list shcluster-members
                    ./splunk list shcluster-artifacts
                    ./splunk list shcluster-configuration-set
                    ./splunk rolling-restart shcluster-members
                    ./splunk list shcluster-member-info
                    ./splunk list shcluster-member-artifacts
                    ./splunk show shcluster-status
                    ./splunk apply shcluster-bundle -target https://server:1234
                    ./splunk transfer shcluster-captain -mgmt_uri https://server.example.com:8089
                    ./splunk bootstrap shcluster-captain -servers_list "https://server1.example.com:8089, https://server2.example.com:8089, https://server3.example.com:8089"
                    ./splunk resync shcluster-replicated-config
                    ./splunk upgrade-init shcluster-members
                    ./splunk upgrade-finalize shcluster-members
            ./splunk rotate shcluster-splunk-secret

        For additional help on a particular command, view help for the particular object using "./splunk help [command]".

        Complete documentation is available online at: "https://docs.splunk.com/Documentation"

"""

DIAG="""
     Collects basic info about your Splunk server, including Splunk's
     configuration details.

     ** Important ** It does not include any event data or private
     information.

     Syntax:

        diag

     Objects:

        NONE

     Parameters:

        NONE

     Examples:

        ./splunk diag

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

DISPATCH_LONG="""
     Searching with dispatch lets you run long-running reports via the CLI.
     Use dispatch to search a large number (or unlimited) number of results to
     process a report. Searches run using dispatch are only limited by the
     parameters you set (maxout or maxtime). You can set when to end a
     dispatched search by setting a maximum time (maxtime) or a maximum number
     of results to output (maxout).

     ** Note: **
     dispatch uses the same syntax as the search command.


     Syntax:

       dispatch "search string" [-parameter]


     Objects:

       search string     String to search and report on.


     Required Parameters:

       NONE


     Optional Parameters:

       maxout     Set the maximum number of results to return from the search
                  string (default=100)
       maxtime    Set the maximum number of seconds to run the search
                  (default=0 or no limit)


     Examples:

       ./splunk dispatch "source=*hot* | stats count" -maxtime 3

       ./splunk dispatch "sourcetype=access* bytes>1000" -maxout 200


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""


EXPORTIMPORT_LONG="""
     Import or export Splunk global data, user data, or event data into or out
     of your Splunk server.

     Use import and export to migrate data from one Splunk installation to
     another.

     Syntax:

        export [object] [-parameter <value>] ...

        import [object] [-parameter <value>] ...

     Objects:

        (For both)
          userdata       user accounts

        (For export only)
          eventdata      exported events indexed as raw log files

     Required Parameters:

          userdata     dir    specify which directory to import data from

          eventdata    index  (default) specify which Splunk index to export events from
                       dir    specify which directory to export data to


     Optional Parameters:

          userdata     NONE

          eventdata    host         export events for the specified host
                       source       export events for the specified source
                       sourcetype   export events for the specified sourcetype
                       terms        export events containing the given terms


     Examples:

          ./splunk import userdata -dir /tmp/export.dat

          ./splunk export eventdata -index my_apache_data -dir /tmp/apache_raw_404_logs -host localhost -terms "404 html"

          ./splunk export eventdata -index main -dir /tmp/events -host www -sourcetype syslog -terms "dhcp OR bind"


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

FIND_LONG="""
     The "find logs" command is no longer supported, and is not available in Splunk.

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

HELP_LONG="""
     Display the default help page, or any specific topic or command help page.

     Syntax:

          help [command|parameter|object|topic]

     Required (default) parameter:

          NONE     if no topic is specified, display the default help page


     Optional parameters:

          help                                displays the main help page
          [command|object|parameter|topic]    links to a help page relating to
                                              the specified topic


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation




"""


LOGINLOGOUT_LONG="""

     Authenticate a session to a Splunk server with an Enterprise license
    (login). Or, end an authenticated session (logout).

     Login stores authentication information in the .splunk subdirectory of
     SPLUNK_OS_USER's home directory (so, on UNIX, ~/.splunk/)

     Syntax:

        login     prompts you for a Splunk username and password

        logout    ends an authenticated session

     Parameters:

          NONE

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

CREATESSL_LONG="""

Creates Secure Sockets Layer (SSL) certificates for secure connections to Splunk Web and between instances of Splunk.

Syntax:
    ./splunk createssl [[audit-keys] [-d <destination_dir>] [-p <privatekey_path>] [-k <publickey_path>] [-l <bit_length>]] [[server-cert [-d <rootca_dir>] [-n <certificate_name>] [-c <cert_CommonName>] [-l <RSA_keylength>] [-p]] [[web-cert [-n <cert_CommonName>] [-l <RSA_keylength>]]

    You must supply one of the following arguments and its associated flags for the command to be valid:

    audit-keys

    server-cert

    web-cert

    Supported flags and arguments:

    audit-keys: Generates a public and private authentication key.

          Supported flags:
                 -d <destination_directory>         # defaults to etc/auth/audit
                 -p <path to write the private key> # defaults to <dest_dir>/private.pem
                 -k <path to write the public key>  # defaults to <dest-dir>/public.pem
                 -l <key length in bits>            # defaults to 1024

                Note: To specify the -d flag, you must also set the -p and -k flags to include the same flags.
               Otherwise, Splunk will place the public and private key files in the default directory.

              server-cert: Generates root CA and other server certificates.

             Supported flags:
                  -d:     Directory where root CA and other certs are stored.
                   (required)
                   -n:     The name of the cert.
                  (required)
                 -c:     The CommonName for the cert.  This should match the DNS name.
                         If DNS is not available then the IP will suffice.
                  -l:     Length of the RSA key to generate (default 1024).
                                                                                                                                                          -p:     Prompt for optional arguments (shown below).
                                                                                                                                                          Note: The -d flag points to the location where input CAs are located, and also create the server cert.  You cannot select an empty directory.
                                                                                                                                                                                                                                                                                          Optional arguments are:
                   - key password/passphrase
                   - company info (name, locaiton, org unit)
                   - key owner info (name, email)

              web-cert: Generates an SSL certificate for Splunk Web.

             Supported flags:
               -n:     The CommonName of the cert.  This shuld match the DNS name.
                       If DNS is not available then the IP will suffice.
               -l:     Length of the RSA key to generate (default 1024).

"""

PACKAGE_LONG="""

     Create tar package of an app.

     The package can be distributed via SplunkBase or deployed locally.

     Syntax:

        package app     packages the app and returns its uri

     Parameters:

        appname         name of the app that needs packaging

     Examples:

       ./splunk package app stubby

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""



REFRESH="""
"""


RTSEARCH_LONG="""

  Search events before they are indexed and preview reports as the events stream in.
  Use the rtsearch command exactly as you use the traditional search command.
  For more information, type "help search".

  For a complete reference on Splunk search, search syntax, and all of the search commands
  see our online user documentation, starting with:
  http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/AboutCLIsearches

  Syntax:

      rtsearch [object][-parameter <value>]

  Note: Parameters that take Boolean values support {0, false, f, no} as
  negatives and {1, true, t, yes} positives.

  Objects:

     Search objects are enclosed in single quotes (' ') and can be keywords,
     expressions, or a series of search commands.

  Required Parameters:

    lastest_time  time-modifier   relative time modifier for the end time of the
                                  search

  Optional Parameters:

    app          appname          specify an app context to run the search

    batch        true             indicates how to handle updates in preview mode.
                                  Defaults to false.

    detach       true             triggers an asynchronous search and displays
                                  the job id and ttl for the search.

    earliest_time  time-modifier  relative time modifier for the start time
                                  of the search

    header       false            indicates whether to display a header in the table
                                  output mode.

    id           rt_<job id>      search job ID number.

    max_time     number           the length of time in seconds that a search job
                                  runs before it is finalized. Defaults to 0, which
                                  means no time limit.

    maxout       number           the maximum number of events to return or send to
                                  stdout (when exporting events). The max allowable
                                  value is 10k. Defaults to 0, which means it will
                                  output an unlimited number of events.

    output       value            indicates how to display the job. Choices are:
                                  rawdata, table, csv, raw, and auto. If not specified,
                                  defaults to rawdata for non-transforming searches
                                  and table for transforming searches.

    preview      false            indicates that reporting searches should be
                                  previewed. Defaults to true.

    timeout      number           the length of time in seconds that a search job
                                  is allowed to live after running. Defaults to 0,
                                  which means the job is cancelled immediately after
                                  it is run.

    wrap         false            indicates whether to line wrap for individual lines
                                  that are longer than the terminal width. Defaults
                                  to true.

   workload_pool value            the name of the workload-pool for the search to run in.

  See what search language is available for use in the CLI by using these
  help commands:

      search-fields          a full list of search fields
      search-modifiers       a full list of search modifiers
      search-commands        a full list of usable search commands

  For more information about how to specify time-modifiers, search the online
  documentation for "search time modifier".

  Examples:

      ./splunk rtsearch 'error' -wrap false

      ./splunk rtsearch 'eventtype=webaccess error | top clientip'

      ./splunk rtsearch 'eventtype=webaccess error' -output csv

      ./splunk rtsearch -id rt_1293485632.11


  Type "help [object|topic]" to view help on a specific object or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

SEARCH_LONG="""

  Splunk searches can retrieve events or generate statistical reports.  Complex searches
  are constructed by stringing commands together with a pipe "|" operator.

  For a complete reference on Splunk search, search syntax, and all of the search commands
  see our online user documentation, starting with:
  http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/AboutCLIsearches

  Syntax:

    search [object][-parameter <value>]

  Note: Parameters that take Boolean values support {0, false, f, no} as
  negatives and {1, true, t, yes} positives.

  Objects:

    Search objects are enclosed in single quotes (' ') and can be keywords,
    expressions, or a series of search commands.

  Optional Parameters:

    app            appname        specify an app context to run the search

    batch          true           indicates how to handle updates in preview
                                  mode. Defaults to false.

    detach         true           triggers an asynchronous search and displays
                                  the job id and ttl for the search.

    earliest_time  time-modifier  epoch or relative specifier for the start time
                                  of the search

    header         false          indicates whether to display a header in the
                                  table output mode.

    id             job id         search job ID number.

    index_earliest time-modifier  REST API option for start time of search, use epoch or
                                  relative specifier format.

    index_latest   time-modifier   REST API option for end time of search, use epoch or
                                  relative specifier format.

    lastest_time   time-modifier  epoch or relative specifier for the end time of the
                                  search

    max_time       number         the length of time in seconds that a search job
                                  runs before it is finalized. Defaults to 0,
                                  which means no time limit.

    maxout         number         the maximum number of events to return or send
                                  to stdout (when exporting events). Setting this
                                  to 0 means it will output an unlimited number
                                  of events. The max allowable value is 10k.
                                  Defaults to 100.

    output         value          indicates how to display the job. Choices are:
                                  rawdata, table, csv, raw, and auto. If not
                                  specified, defaults to rawdata for non-transforming
                                  searches and table for transforming searches.

    preview        false          indicates that reporting searches should be
                                  previewed. Defaults to true.

    timeout        number         the length of time in seconds that a search
                                  job is allowed to live after running. Defaults
                                  to 0, which means the job is cancelled immediately
                                  after it is run.

    wrap           false          indicates whether to line wrap for individual
                                  lines that are longer than the terminal width.
                                  Defaults to true.

    workload_pool  value          the name of the workload-pool for the search to run in.

  See what search language is available for use in the CLI by using these
  help commands:

        search-fields        a full list of search fields
        search-modifiers     a full list of search modifiers
        search-commands      a full list of usable search commands

  For more information about how to specify time-modifiers, search the online
  documentation for "search time modifier".

  Examples:

        ./splunk search '*' -detach true

        ./splunk search 'eventtype=webaccess error' -wrap false

        ./splunk search 'eventtype=webaccess error' -detach true

        ./splunk search '* | stats count' -earliest_time -1h@h -latest_time @h

        ./splunk search -id 1293485632.11

        ./splunk search 'index=_internal' -index_earliest -1d@d -index_latest @d


    Type "help [object|topic]" to view help on a specific object or topic.

    Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

SPOOL_LONG="""

     Add a file to Splunk by reading the input source once.

     Syntax:

        spool <source>

     Objects:

          NONE

     Required Parameters:

          {NULL}    no action

          source    path or file to be indexed

     Optional Parameters:

          NONE

     Examples:

          ./splunk spool /tmp/logs.tgz


     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation




"""

STARTSTOPRESTART_LONG="""
     Start, stop, or restart your Splunk server.

     Syntax:

        [start|stop|restart] object

     Objects:

        NONE        (default) starts/stops/restarts the Splunk daemon

        splunkweb   Can be used to just restart the web interface without
                    affecting the rest of the Splunk daemon

     Parameters:

        NONE

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation



"""

STATUS_LONG="""

     Show the status of Splunk's processes.

     Syntax:

        status

     Objects:

        NONE

     Parameters:

        NONE

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""


VALIDATE_LONG="""
     Use validate index to verify index paths specified in indexes.conf.

     Use validate files to verify splunk-installed files are still intact.

     Syntax:

        validate index [indexname]
        validate files [-manifest <filename>] [-type <value>]

     Objects:

        index      index to validate

     Required Parameters:

        NONE

     Optional Parameters:

        manifest  filename        Validate files against specific manifest file

        type      file-category   Only validate selected type of file.
                                  (Only "conf" is supported,
                                   to validate all default conf files.)

     Examples:

        ./splunk validate index main

        ./splunk validate files

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation




"""

VERSION_LONG="""
     Display Splunk's version and build number.

     Syntax:

        version

     Objects:

        NONE

     Parameters:

        NONE

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""


###################################################################
# Object and Parameter Definitions

AUTH_LONG="""
    The authentication parameter for all commands on a Splunk server with an
    Enterprise license.

    Add the parameter "-auth username:password" to authenticate in line with
    execution of any command.

    Note: You can't use "-auth" with the "login" command.

    Note: Once you are logged in, your credentials are cached; you do not need to supply
        the '-auth' parameter again, until you invoke 'splunk logout', or the period given in
        server.conf/[general]/sessionTimeout has elapsed.
   
    Note: Alternatively, you can use the "-token" parameter for commands that require authentication
        without caching your credentials. Run "splunk help token" for more information.

    Note: In offline mode (i.e. you are giving CLI commands from console of the host where Splunk is
        installed, *and* splunkd is not running), you do not need to supply the '-auth' parameter.

    Syntax:

       [command] [object] -auth username:password

    Objects:

        username:password      login name and password pair

    Examples:

        This example authenticates as user "admin" to change the password for
        user "newbie":

            ./splunk edit user newbie -password f8h2.$R -auth admin:d3cidr

        This example makes the same change the longer, but less confusing way:

            login
            edit user newbie -password f8h2.$R
            logout

     Type "help [object|topic]" to view help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

TOKEN_LONG="""
    Lets you use a token for authentication when you run commands on a Splunk Enterprise instance.

    Add the parameter "-token <token>" to authenticate in-line with execution of any command. You must 
    supply a full, valid, non-expired authentication token, and the instance you want to log into
    must have token authentication enabled.

    You cannot use the "-token" argument combined with the "login" command.

    Note: The instance does not cache successful logins that are made with tokens. You must provide either a 
    valid token with the "-token" argument, or standard credentials with the "-auth" argument, for every 
    command that requires authentication.

    If you provide both a token and standard credentials using both arguments, the CLI tries to log 
    in with the standard credentials. If those credentials are not valid, the command fails, even if the 
    token you supply is valid. If the credentials are valid, the command succeeds, even if the token you 
    supply is not valid.

    Syntax:

       [command] [object] -token <token>

    Objects:

       <token>    A string that represents a full JavaScript Object Notation-style Web authentication token (JWT)

    Example: 

       This example lets the user create an app called "myNewApp" from template "sample_app" using 
       a token for authentication:

       ./splunk create app myNewApp -template sample_app -token eyJraWQiOi...

"""

BOOTSTART_LONG="""

     An object used by the enable and disable commands to set Splunk to run
     when the operating system boots.

     Syntax:

        [enable|disable] boot-start [parameters]

     Required Parameters:

        NONE

     Optional Parameters:

        user   specifies which OS user to run splunkd service as, at boot time
               (default=root); SPLUNK_OS_USER in splunk-launch.conf is also set
               to the specified value.


     Type "help [command]" to get help with parameters for a specific command on boot-start.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""


DEPLOYCLIENT_LONG="""
     An object used to tell commands to operate on deployment clients that report to the deployment server.

     Syntax:

      [list] deploy-clients
      [disable|enable] deploy-client

     Required Parameters:

        NONE

     Type "help [command]" to get help with parameters for a specific command on deploy-client.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

DEPLOYPOLL_LONG="""
     An object used to enable or set which deployment server to poll.

     Syntax:

        [set|show] deploy-poll [-uri ip:port]

     Optional Parameters:

        uri     deployment server ip:port to poll for deployment class updates

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6


      Type "help [command]" to get help with parameters for a specific command on deploy-poll.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

DEPLOYSERVER_LONG="""

     An object used to control distributed deployment server capability.


     Syntax:

        [disable|display|enable|reload] deploy-server

     Parameters:

        NONE

      Type "help [command]" to get help with parameters for a specific command on deploy-server.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

DISTSEARCH_LONG="""
     An object used to control a Splunk server's distributed search capability.

     Syntax:

        [disable|enable|display] dist-search

     Parameters:

        NONE


      Type "help [command]" to get help with parameters for a specific command on dist-search.

     Complete documentation is available online at: http://docs.splunk.com/Documentation




"""

EVENTDATA_LONG="""
     An object used to identify data of events that are indexed by Splunk.

     Syntax:

        [import|export|clean] eventdata -dir -index [-parameter <value>]

     Required Parameters:

        dir          directory to export all data to

        index        what index to export data from

     Optional Parameters:

        host         only export data from this specified host

        source       only export events from this specified source

        sourcetype   only export events from this sourcetype

        terms        only export events containing these specific terms

     Examples:

        ./splunk export eventdata main -dir /tmp/myData


      Type "help [command]" to get help with parameters for a specific command on eventdata.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

EXEC_LONG="""
    An object used to identify scripted inputs.

     Syntax:

        [list|add|edit|remove] exec scripted_input_source

     Objects:

        scripted_input_source     specified scripted input source

     Parameters:

        NONE


      Type "help [command]" to get help with parameters for a specific command on exec.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

FORWARDSERVER_LONG="""
     An object used to specify servers or to specify the operation of a command
     on a Splunk forwarder.

     Syntax:

        [add|remove] forward-server [-parameter <value>]...
        list forward-server

     Required Parameters:

        hostport   in the format <host>:<port> where host and port are hostname or IP address of
                   the indexing server and port that the indexer is listening on.

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6

     Optional Parameters:

        method     set forwarding method to data-cloning or load-balancing (default=clone)


      Type "help [command]" to get help with parameters for a specific command on forward-server.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""


GLOBALDATA_LONG="""

     An object used to specify global server data of your Splunk server
     configuration (ie. tags, source type aliases, host tags, etc.).

     Syntax:

        [clean] globaldata [-f] [-parameter <value>]

     Optional Parameters:

        f        forces clean to skip its confirmation prompt.


      Type "help [command]" to get help with parameters for a specific command on globaldata.

     Complete documentation is available online at: http://docs.splunk.com/Documentation



"""

INDEX_LONG="""
     An object used to specify an index.

     Syntax:

        validate index [-parameter <value>]

        [spool|monitor|tcp|udp] [path|file] source index [-parameter <value>]

        clean [object] index [-parameter <value>]


     Optional Parameters:

        name      name of index (if none specified, all indexes are used)


      Type "help [command]" to get help with parameters for a specific command on index.

     Complete documentation is available online at: http://docs.splunk.com/Documentation



"""

LOCALINDEX_LONG="""
     An object used to specify the local Splunk index.

     Note: Disabling local indexing only affects Splunk forwarders.

     Syntax:

        [enable|disable|display] local-index [-parameter <value>]

     Parameters:

        NONE


      Type "help [command]" to get help with parameters for a specific command on local-index.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""


PORT_LONG="""
     A parameter used to specify a network port to perform an action on.
     Also used as a parameter for other objects such as search-server.

     Syntax:

        [command] search-server server port port#

        [command] [udp|tcp] port#


     Objects:

        server    server hostname or IP address.

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6

        port#     specified port number (ie 8801)


      Type "help [command]" to get help with parameters for a specific command on port.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""


SEARCHSERVER_LONG="""
    An object used to specify servers to add/remove/list, or operate a
    command on that the current server distributes to.

    Syntax:

        [add|remove|edit|list] search-server <hostname/host-ip>:<management-port> [-parameter <value>]

    Required Parameters:

        <hostname/host-ip>:<management-port>    supply the hostname or IP address and splunkd port of the remote server

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6

     For add:

        remoteUsername   username to access the remote server

        remotePassword   password to access the remote server

     For edit:

        action           [enable|disable|quarantine|unquarantine]

     For remove:

        NONE


     Optional Parameters:

        NONE


    Examples:

          ./splunk add      search-server hulk:5555 -remoteUsername user1 -remotePassword passwd1

          ./splunk edit     search-server hulk:5555 -action quarantine

          ./splunk remove   search-server hulk:5555


    Type "help [command]" to get help with parameters for a specific command on search-server.

    Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

SPOOL_LONG="""
    Use "spool" to index a file once and forget about it.

    Use "add monitor" to index files and directories containing both live
    and closed files.

    Syntax:

        spool pathname [-parameter <value>] ...

    Objects:

        NONE

    Required Parameter:

        pathname    path to a file or directory to be unpacked, uncompressed and indexed

    Optional Parameters:

        source      source value to set on events from the file or directory

        sourcetype  source type value to set on events

        index       Splunk index into which to place events

        hostname    hostname to set as the host value for example, web01.mycorp.com

        auth        username:password to authenticate the command to Splunk

    Examples:

        ./splunk spool /var/log/messages.1

        ./splunk spool /mnt/old/logs -hostname web01 -auth gwb:d3cidr

     Type "help [object|topic]" to get help on a specific object, or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

URI_LONG="""

     A parameter used to instruct Splunk to send a command to a specified
     Splunk server.

     Note: Make sure you have a working connection with the Splunk server
     you want to send the command to. If you are not properly connected, Splunk
     will generate an error when executing a command with uri.


     Syntax:

        [command] [object] [-parameter <value>]...-uri [required parameter]

     Objects:

        specified server     [http|https]://[name of server|ip]:[port]

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6


     Type "help [object|topic]" to get help on a specific object, or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

USERDATA_LONG="""
     An object used to specify user account data for your Splunk server.

     Syntax:

        clean userdata [-parameter <value>]

        [import|export] userdata [-parameter <value>]...

     Required Parameters:

        NONE


      Type "help [command]" to get help with parameters for a specific command on userdata.

     Complete documentation is available online at: http://docs.splunk.com/Documentation



"""

WATCH_LONG="""

    Works exactly like monitor.  See help monitor for more details.

"""

###################################################################
# Meta-definitions

HELP_DEFAULT_LONG="""

  Welcome to Splunk's Command Line Interface (CLI).

  Type these commands for more help:

    help simple, cheatsheet    display a list of common commands with syntax
    help commands              display a full list of CLI commands
    help [command]             type a command name to access its help page
    help clustering            commands that can be used to configure the clustering setup
    help shclustering          commands that can be used to configure the shclustering setup
    help control, controls     tools to start, stop, manage Splunk processes
    help [object]              type an object name to access its help page
    help [topic]               type a topic keyword to get help on a topic
    help datastore             manage Splunk's local filesystem use
    help distributed           manage distributed configurations such as
                               data cloning, routing, and distributed search
    help forwarding            manage deployments
    help input, inputs         manage data inputs
    help licensing             manage licenses for your Splunk server
    help settings              manage settings for your Splunk server
    help tools                 tools to help your Splunk server
    help search                help with Splunk searches

  Universal Parameters:

    The following parameters are usable by any command. For more details on each
    parameter, type "help [parameter]".

    Parameter syntax:

      [command] [object] [-parameter <value> | <value>]... [-uri][-auth | -token]

      app        specify the app or namespace to run the command; for search, defaults to
                 the Search app

      auth       specify login credentials to execute commands that require you to be logged in

      token      specify a JavaScript Object Notation-style Web authentication token (JWT) to 
                 authenticate the use of the command. You must supply a token with every command you run 
                 that requires authentication. Do not supply both credentials and tokens at the same time

      owner      specify the owner/user context associated with an object; if not specified,
                 defaults to the currently logged in user

      uri        execute a command on any specified Splunk server. Use the
                 format: <ip>:<port>

     Note: IPv4 (127.0.0.1:80) and IPv6 ([2001:db8::1]:80) formats are both supported for specifying IP addresses.
           By default, splunkd listens on IPv4 only. To enable IPv6 support, refer to the instructions in:
           http://docs.splunk.com/Documentation/Splunk/latest/Admin/ConfigureSplunkforIPv6


     Type "help [object|topic]" to get help on a specific object or topic.

     Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

DATASTORE_LONG="""

 Manage indexes and user or global data that is stored on the server.

 Commands:

    add index [-name <name> | <name>] [-dir <value>] ...

    edit index [-name <name> | <name>] [-dir <value>] ...

    list index

    export [eventdata|userdata]

    import [eventdata|userdata]

    clean  [all|eventdata|globaldata|userdata] [-f] [-index <name>]

  Objects:

    all           everything on the server
    eventdata     indexed events and fields for each event
    globaldata    host tags, source type aliases, server tag data
    userdata      user account information

  Parameters:

    For add and edit index ONLY

    dir       <value>   specify a directory to add your index
    name      <value>   name of the index

    For clean ONLY

    f                   forces skip confirmation prompt
    index     <name>    name of the index


  Type "help [object|topic]" to get help on a specific object, or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""


DISTRIBUTED_SEARCH_LONG="""

  Distributed search, cloning, and deployment configuration management tools.

  Commands:

    disable [listen|dist-search|local-index|deploy-client|
            deploy-server] [-parameter <value>] ...

    enable  [listen|dist-search|local-index|deploy-client|
            deploy-server] [-parameter <value>] ...

    display [listen|dist-search|local-index|deploy-server]

    add [forward-server|search-server] server

    remove [forward-server|search-server] server

    list [deploy-clients|forward-server|search-server]

    reload deploy-server [-class <sc>]

    set [deploy-poll]

    show [deploy-poll]

  Objects:

    dist-search          distribute searches to other Splunk servers
    listen               reception of data to be indexed from other Splunk servers
    forward-server       a Splunk server to which to forward data to be indexed
    search-server        a Splunk server to which to forward searches
    local-index          maintain a search index on this Splunk server
    deploy-client        a deployment client
    deploy-clients       deployment clients
    deploy-server        a deployment server
    deploy-poll          enables deployment client and sets which deployment server
                         to poll

  Parameters:

    For a complete list of parameters, type "./splunk help [command|object]".


  Type "help [object|topic]" to get help on a specific object, or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

FILE_LONG="""

  To tell Splunk to index a file or directory, use one of these actions:

     spool [pathname]         read a file or directory one time

     add monitor [pathname]   continuously monitor a file or directory
                              for new live data and files

  Type "help [object|topic]" to get help on a specific object, or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

FORWARDING_LONG="""

  Data forwarding configuration management tools.

  Commands:

    enable local-index [-parameter <value>] ...

    disable local-index [-parameter <value>] ...

    display local-index

    add [forward-server|search-server] server

    remove [forward-server|search-server] server

    list [forward-server|search-server]


  Objects:

    forward-server       a Splunk forwarder to forward data to be indexed
    search-server        a Splunk server to forward searches
    local-index          a local search index on the Splunk server

  Parameters:

    For a complete list of parameters, type "./splunk help [command|object]".


  Type "help [object|topic]" to get help on a specific object, or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

INPUT_LONG="""

  Data input configuration options.

  Actions:

    add [exec|monitor|tcp|udp] [source] [-parameter <value>] ...

    edit [exec|monitor|tcp|udp] [source] [-parameter <value>] ...

    remove [monitor|tcp|udp] [source]

    list [monitor|tcp|udp]

  Objects:

    exec       a scripted input
    fifo       (no longer supported)
    monitor    a file or directory to be continuously monitored for new input
    tcp        a TCP socket
    udp        a UDP socket

  Default Parameter:

    source    file, directory, scripted input, or socket to manage

  Optional Parameters:

    For a complete list of parameters, type "./splunk help [command|object]".


  Type "help [object|topic]" to view help on a specific object or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

SAVEDSEARCH_LONG="""

  Configuration options for saved searches and alerts. Alerts are controlled by the
  saved-search object of the add and remove commands. Alerts can be scheduled to be
  run at a specified time, or can be set to trigger when a certain threshold is reached.

  Syntax:

    add saved-search [-parameter <value>]

    edit saved-search [-parameter <value>]

    list saved-search

    remove saved-search

  Required Parameters:

    name           (default) name of saved search to create

    terms          search terms to be associated with this saved search

  Optional Parameters:

    alert           make the search an alert (true|false, default=false)
                    IF alert=true, "schedule" and "threshold" are required, and
                    "email", "attach" or "script" options are required.

    end_time        the latest time for the search

    fields          a list of key-value pairs to annotate the events inserted into
                    the summary index. format pairs as key:value and separate multiple
                    entries with a semicolon

    summary_index   the name of the summary index where to add the results of the
                    scheduled search

    start_time      the earliest time for the search

    ttl             time-to-live (in seconds) for the artifacts of the scheduled search


    (IF optional parameter "alert" is set to true, then the following is REQUIRED)

    schedule        specify when the alert is run using full cron format


    (IF optional parameter "alert" is set to true, then AT LEAST ONE of the following
    is REQUIRED)

    email           comma-separated list of email addresses to send alerts to (true|false)
                    default=false

    attach          specify inclusion of search results in emails (true|false) default=false

    script          script to execute upon alert (ex: $SPLUNK_HOME/bin/myScript)

    threshold       the threshold to trigger the alert action
                    [<threshold type>:<relation>:<quantity>]
                    <threshold type>= num-events,num-sources,num-hosts
                    <quantity>= any integer


  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

SEARCHFIELDS_LONG="""

  Fields contain data that is identified in key/value pairs at index time. Splunk indexes
  time, host, source, and sourcetype data automatically. Fields can be used for searching,
  to refine the scope of an existing search, or for reporting purposes. Some fields let
  you use wildcards, regular expressions, and comparison operations to specify values to
  match. Custom fields can also be created. See the online documentation for a complete
  reference of custom and default fields.

  For a complete reference on Splunk search, search syntax, and all of the search commands
  see our online user documentation, starting with:
  http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/AboutCLIsearches


     _raw            the original raw data of an event
     _time           an event's timestamp in Unix Time
     date_hour       the hour that an event occurred in
     date_mday       the day of the month an event occurred on
     date_minute     the minute that an event occurred in
     date_month      the month that an event occurred in
     date_second     the seconds portion of an event's timestamp
     date_wday       the day of the week that an event occurred on
     date_year       the year that an event occurred in
     date_zone       the time of the local timezone of an event in Unix Time
     eventtype       event type names that an event matches
     host            the name of the host that the event originated from
     index           the name of the index where an event is located
     linecount       the number of lines and event contains
     punct           the punctuation pattern extracted from an event
     source          the name or path of the source where an event is from
     sourcetype      the name of an event's sourcetype
     splunk-server   the name of the splunk-server
     timestamp       an event's timestamp extracted at index time


  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

SEARCHMODIFIERS_LONG="""

  Use modifiers to narrow your searches within the "search" (or "dispatch") command.
  You can narrow(modify) your searches by constraining the time range (using time-based
  modifiers), or by specifying field tags, or a saved search to match. Some modifiers
  let you use wildcards, regular expressions, and comparison operations to specify values
  to match.  See the online documentation for a complete reference of the search modifiers.

  For a complete reference on Splunk search, search syntax, and all of the search commands
  see our online user documentation, starting with:
  http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/AboutCLIsearches


  Search modifiers:
     savedsearch             returns the search results of a saved search
     tag                     returns events with matching field values


  Time-based modifiers:
     daysago                 events within the last N days
     enddaysago              events are before the specified number of days ago
     endhoursago             events are before the specified number of hours ago
     endminutesago           events are before the specified number of minutes ago
     endmonthsago            events are before the specified number of months ago
     endtime                 events are before the specified time
     hoursago                events within the last N hours
     minutesago              events within the last N minutes
     monthsago               events within the last N months
     searchtimespandays      events within a specified range of days
     searchtimespanhours     events within a specified range of hours
     searchtimespanminutes   events within a specified range of minutes
     searchtimespanmonths    events within a specified range of months
     startdaysago            events after the specified number of days ago
     starthoursago           events after the specified number of hours ago
     startminutesago         events after the specified number of minutes ago
     startmonthsago          events after the specified number of months ago
     starttime               events after the specified timestamp
     starttimeeu             events after the specified European format timestamp
     timeformat              change the format of the timestamp


  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""

SEARCHCOMMANDS_LONG="""

  All Splunk Search commands can be piped together to form a more complex search string.
  Data-generating commands generate data. Data-processing commands require results from
  data-generating commands to perform their processing operations.

  For a complete reference on Splunk search, search syntax, and all of the search commands
  see our online user documentation, starting with:
  http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/AboutCLIsearches

  Common search commands:

    chart/timechart     Returns results in a tabular output for (time-series) charting.
    dedup               Removes subsequent results that match a specified criterion.
    eval                Calculates an expression.
    fields              Removes fields from search results.
    head/tail           Returns the first/last N results.
    lookup              Adds field values from an external source.
    rename              Renames a field. Use wildcards to specify multiple fields.
    rex                 Specifies regular expression named groups to extract fields.
    search              Filters results to those that match the search expression.
    sort                Sorts the search results by the specified fields.
    stats               Provides statistics, grouped optionally by fields.
    table               Specifies fields to keep in the result set. Retains data in tabular format.
    top/rare            Displays the most/least common values of a field.
    transaction         Groups search results into transactions.
    where               Filters search results using eval expressions. Used to compare two different fields.

  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

TOOLS_LONG="""

  Useful commands to help your Splunk server.  These commands don't require Splunk to be
  running, and don't reconfigure any of your Splunk settings.

  Syntax:

   anonymize source [-parameter <value>]...

   find logs searchpath

   validate object [-parameter <value>]


  Objects:

    logs           logs that find will identify and find in the specified searchpaths
    source         the source that anonymize will perform action on

    For validate ONLY:

    index          index to check for correctness

  Optional Parameters:

     For a complete list of parameters, type "./splunk help [command|object]".


  Type "help [object|topic]" to get help on a specific object, or topic.

  Complete documentation is available online at: http://docs.splunk.com/Documentation


"""

EXTRACT_I18N_LONG="""

  Extract translatable strings from an application, ready to be translated with a
  gettext compatible editor.

  Creates or replaces locale/messages.pot in the application's directory.

  Syntax:

    extract i18n -app <application name>

  Documentation on creating i18n compliant applications is available online at
  http://docs.splunk.com/Documentation

"""


CLONE_PREP_CLEAR_CONFIG__LONG="""

  Clear a Splunk instance of instance-unique config parameters, which are normally
  created on initial startup (first-time run, "ftr").  Intended for use after an
  instance has been cloned (i.e. all its files simply copied) from another instance.

  Syntax:

    clone-prep-clear-config

  Complete documentation is available online at: http://docs.splunk.com/Documentation

"""


###################################################################
# Deprecated search command info

TESTTRAIN_LONG="""
     The 'test' and 'train' commands have been deprecated.

     Type "help [object|topic]" to view help on a specific object or topic.

"""

REMOTE_LONG= """
     The remote command has been deprecated in versions 3.2 and later. Instead of using remote,
     use the "dispatch" CLI command to execute searches across remote machines.

     Type "help [object|topic]" to view help on a specific object or topic.

"""

FIFO_LONG="""
     The object 'fifo' is no longer supported.

     Type "help [command|object|topic]" to view help for a specific command, object, or topic.

"""

BLACKLIST_LONG="""
     The object 'blacklist' is no longer supported.

     Type "help [command|object|topic]" to view help for a specific command, object, or topic.

"""

###################################################################

########################### end help declarations #######################


###################################################################
######################   Begin Help calls ###############################
#
# format is addHelp("command name", "short help string", """long help string""")
#

# command help strings


# ANONYMIZE_LONG
addHelp("anonymize", "", ANONYMIZE_LONG)

# CLEAN_LONG
addHelp("clean", "", CLEAN_LONG)

#CLUSTER_LONG
addHelp("cluster", "", CLUSTER_LONG)
addHelp("clustering", "", CLUSTER_LONG)

#SHPOOL LONG
addHelp("shcluster", "", SHPOOL_LONG)
addHelp("shclustering", "", SHPOOL_LONG)

# DISPATCH_LONG
addHelp("dispatch", "", DISPATCH_LONG)

# EXPORTIMPORT_LONG
addHelp("export", "", EXPORTIMPORT_LONG)
addHelp("import", "", EXPORTIMPORT_LONG)

# FIND_LONG
addHelp("find", "", FIND_LONG)
addHelp("logs", "", FIND_LONG)

# HELP_LONG  aka default help string HELP_DEFAULT_LONG

# LOGINLOGOUT_LONG
addHelp("login", "", LOGINLOGOUT_LONG)
addHelp("logout", "", LOGINLOGOUT_LONG)

# CREATESSL_LONG
addHelp("createssl", "", CREATESSL_LONG)

# RTSEARCH_LONG
addHelp("rtsearch", "", RTSEARCH_LONG)
addHelp("realtime", "", RTSEARCH_LONG)
addHelp("real-time", "", RTSEARCH_LONG)
addHelp("livetail", "", RTSEARCH_LONG)
addHelp("live-tail", "", RTSEARCH_LONG)

# SEARCH_LONG
# search meta-definition
addHelp("search", "", SEARCH_LONG)
addHelp("searches", "", SEARCH_LONG)
addHelp("searching", "", SEARCH_LONG)
addHelp("search-help", "", SEARCH_LONG)

# SPOOL_LONG
addHelp("spool", "", SPOOL_LONG)

# STATUS_LONG
addHelp("status", "", STATUS_LONG)
addHelp("server-status", "", STATUS_LONG)

# VALIDATE_LONG
addHelp("validate", "", VALIDATE_LONG)

# VERSION_LONG
addHelp("version", "", VERSION_LONG)
addHelp("splunk-version", "", VERSION_LONG)


# object and parameter strings

# AUTH_LONG
addHelp("auth", "", AUTH_LONG)
addHelp("login", "", AUTH_LONG)

# TOKEN_LONG
addHelp("token","", TOKEN_LONG)

# BLACKLIST_LONG
addHelp("blacklist", "", BLACKLIST_LONG)

# BOOTSTART_LONG
addHelp("boot-start", "", BOOTSTART_LONG)

# DEPLOYCLIENT_LONG
addHelp("deploy-client", "", DEPLOYCLIENT_LONG)
addHelp("deploy-clients", "", DEPLOYCLIENT_LONG)
addHelp("client", "", DEPLOYCLIENT_LONG)

# DEPLOYPOLL_LONG
addHelp("deploy-poll", "", DEPLOYPOLL_LONG)
addHelp("deploypoll", "", DEPLOYPOLL_LONG)
addHelp("poll", "", DEPLOYPOLL_LONG)

# DEPLOYSERVER_LONG
addHelp("deploy-server", "", DEPLOYSERVER_LONG)
addHelp("deployserver", "", DEPLOYSERVER_LONG)
addHelp("server", "", DEPLOYSERVER_LONG)

# DISTSEARCH_LONG
addHelp("dist-search", "", DISTSEARCH_LONG)

# EVENTDATA_LONG
addHelp("eventdata", "", EVENTDATA_LONG)
addHelp("event", "", EVENTDATA_LONG)

# EXEC_LONG
addHelp("exec", "", EXEC_LONG)
addHelp("scripted", "", EXEC_LONG)

# FIFO_LONG
addHelp("fifo", "", FIFO_LONG)

# FORWARDSERVER_LONG
addHelp("forward-server", "", FORWARDSERVER_LONG)
addHelp("forwardserver", "", FORWARDSERVER_LONG)

# GLOBALDATA_LONG
addHelp("globaldata", "", GLOBALDATA_LONG)
addHelp("global", "", GLOBALDATA_LONG)

# LOCALINDEX_LONG
addHelp("local", "", LOCALINDEX_LONG)
addHelp("local-index", "", LOCALINDEX_LONG)

# PORT_LONG
addHelp("port", "", PORT_LONG)
addHelp("ports", "", PORT_LONG)

# SAVEDSEARCH_LONG
addHelp("alert", "", SAVEDSEARCH_LONG)
addHelp("alerts", "", SAVEDSEARCH_LONG)
addHelp("savedsearch", "", SAVEDSEARCH_LONG)
addHelp("saved-search", "", SAVEDSEARCH_LONG)

# SEARCHSERVER_LONG
addHelp("searchserver", "", SEARCHSERVER_LONG)
addHelp("search-server", "", SEARCHSERVER_LONG)

# SPOOL_LONG
addHelp("spool", "", SPOOL_LONG)

# URI_LONG
addHelp("uri", "", URI_LONG)


# USERDATA_LONG
addHelp("userdata", "", USERDATA_LONG)

# WATCH_LONG
addHelp("watch", "", WATCH_LONG)


# meta-definitions

# HELP_DEFAULT_LONG     aka DEFAULT HELP PAGE
addHelp("help", "", HELP_DEFAULT_LONG)
addHelp("splunk", "", HELP_DEFAULT_LONG)
addHelp("parameters", "", HELP_DEFAULT_LONG)
addHelp("parameter", "", HELP_DEFAULT_LONG)
addHelp("", "", HELP_DEFAULT_LONG)

# DATASTORE_LONG
addHelp("data", "", DATASTORE_LONG)
addHelp("datastore", "", DATASTORE_LONG)
addHelp("store", "", DATASTORE_LONG)

# DISTRIBUTED_SEARCH_LONG
addHelp("distributed", "", DISTRIBUTED_SEARCH_LONG)
addHelp("distributed-search", "", DISTRIBUTED_SEARCH_LONG)
addHelp("cloning", "", DISTRIBUTED_SEARCH_LONG)
addHelp("routing", "", DISTRIBUTED_SEARCH_LONG)
addHelp("deployments", "", DISTRIBUTED_SEARCH_LONG)
addHelp("deployment", "", DISTRIBUTED_SEARCH_LONG)

# FILE_LONG
addHelp("file", "", FILE_LONG)
addHelp("add files", "", FILE_LONG)
addHelp("dir", "", FILE_LONG)
addHelp("directory", "", FILE_LONG)
addHelp("path", "", FILE_LONG)
addHelp("pathname", "", FILE_LONG)

# FORWARDING_LONG
addHelp("forwarding", "", DISTRIBUTED_SEARCH_LONG)

# INPUT_LONG
addHelp("input", "", INPUT_LONG)
addHelp("inputs", "", INPUT_LONG)

# SEARCHFIELDS_LONG
addHelp("fields", "", SEARCHFIELDS_LONG)
addHelp("search fields", "", SEARCHFIELDS_LONG)
addHelp("search-fields", "", SEARCHFIELDS_LONG)
addHelp("search-field", "", SEARCHFIELDS_LONG)

# SEARCHMODIFIERS_LONG
addHelp("modifiers", "", SEARCHMODIFIERS_LONG)
addHelp("modifier", "", SEARCHMODIFIERS_LONG)
addHelp("search modifiers", "", SEARCHMODIFIERS_LONG)
addHelp("search modifier", "", SEARCHMODIFIERS_LONG)
addHelp("search-modifier", "", SEARCHMODIFIERS_LONG)
addHelp("search-modifiers", "", SEARCHMODIFIERS_LONG)

# SEARCHCOMMANDS_LONG
addHelp("search-commands", "", SEARCHCOMMANDS_LONG)
addHelp("search commands", "", SEARCHCOMMANDS_LONG)
addHelp("search command", "", SEARCHCOMMANDS_LONG)
addHelp("operators", "", SEARCHCOMMANDS_LONG)
addHelp("search-operators", "", SEARCHCOMMANDS_LONG)
addHelp("offline", "", OFFLINE_PEER)

# TOOLS_LONG
addHelp("tools", "", TOOLS_LONG)

# I18N TEXT EXTRACTION
addHelp('extract', '', EXTRACT_I18N_LONG)

# MISC
addHelp('clone-prep-clear-config', '', CLONE_PREP_CLEAR_CONFIG__LONG)


########################### end help calls ############################

def helpShort(cmd):
    return helpStrs[cmd]["helpShort"]

def helpLong(cmd):
    return helpStrs[cmd]["helpLong"]

def hasHelp(cmd):
    return cmd in helpStrs
