# Vainstein K 12aug2013


# # # Check a few prereqs.
feature='"splunk <verb> <object>" tab-completion'
[ `basename $SHELL` != 'bash' ]     && echo "Sorry, $feature is only for bash" >&2                                     && return 11
[ ${BASH_VERSINFO[0]} -lt 4 ]       && echo "Sorry, $feature only works with bash 4.0 or higher" >&2                        && return 12
[ `type -t complete` != 'builtin' ] && echo "Sorry, $feature requires a bash that supports programmable command completion" >&2 && return 13


die () {
	echo "(exit=$?) $@" >&2 && exit 42
}


ifSourced () { # do NOT exit(1) from this function!
	local readonly tempfile=`pwd`/tmp--cli-completion--$$
	rm -f $tempfile

	$BASH ${BASH_ARGV[0]} --populateTempfile $tempfile
	[ $? -eq 0 ] || return
	[ -e $tempfile ] || return
	. $tempfile
	rm -f $tempfile

	# # # Associate the completion function with the splunk binary.
	local readonly completionFunction=fSplunkComplete
	complete -r splunk 2>/dev/null
	complete -F $completionFunction splunk

	# You can view the completion function anytime via:      $ type fSplunkComplete
}


ifInvoked () { # all error checking happens in this function
	local readonly debug=false
	local readonly tempfile=$1
	$debug && echo "Told that tempfile=$tempfile"

	# # # If anything goes wrong, at least we don't pollute cwd with our tempfile.
	$debug || trap "rm -f $tempfile" SIGINT SIGQUIT SIGTERM SIGABRT SIGPIPE
	touch $tempfile || die "Cannot touch tempfile=$tempfile"

	# # # Decide where SPLUNK_HOME is.
	if [ "$(dirname $(pwd))" == 'bin' ]; then
		local readonly splunkHome=$(dirname $(dirname $(pwd)))
	elif [ -n "$SPLUNK_HOME" ]; then
		local readonly splunkHome=$SPLUNK_HOME
	else
		die 'Cannot figure out where SPLUNK_HOME is'
	fi
	$debug && echo "Decided SPLUNK_HOME=$splunkHome"

	# # # Check that splunk (the binary) exists.
	local readonly splunkBinary=$splunkHome/bin/splunk
	[ -e $splunkBinary -a -x $splunkBinary ] || die "Cannot find expected binary=$splunkBinary"

	# # # Find the file with object->{verb1,verb2,...} map.
	local readonly splunkrcCmdsXml=$splunkHome/etc/system/static/splunkrc_cmds.xml
	[ -e $splunkrcCmdsXml ] || die "Cannot find expected file $splunkrcCmdsXml"
	$debug && echo "Shall read verb-obj info from: $splunkrcCmdsXml"

	# # # Parse the map file, and generate our internal verb->{objA,objB,...} map.
	local -A verb_to_objects
	local line object verb objectsForThisVerb lineNumber=0
	local inItem=false
	local readonly regex_depr='\<depr\>'
	local readonly regex_verb='\<verb\>'
	local readonly regex_synonym='\<synonym\>'
	while read line; do
		lineNumber=$((lineNumber+1))

		if $inItem; then
			if [[ $line =~ '</item>' ]]; then
				$debug && echo "Exited item tag at line=$lineNumber; this was obj=$object"
				inItem=false
				object=''
			elif [[ $line =~ '<cmd name' && ! $line =~ $regex_depr && ! $line =~ $regex_synonym ]]; then
				[ -z "$object" ] && die "BUG: No object within item tag.  (At line $lineNumber of $splunkrcCmdsXml)"
				verb=${line#*\"}  # remove shortest match of .*" from the front
				verb=${verb%%\"*} # remove longest match of ".* from the back
				[ "$verb" == '_internal' ] && continue # Why the... eh, moving on.
				objectsForThisVerb=${verb_to_objects[$verb]}
				objectsForThisVerb="$objectsForThisVerb $object"
				verb_to_objects[$verb]=$objectsForThisVerb
				$debug && echo "Mapped object=$object to verb=$verb at line=$lineNumber; now objectsForThisVerb='$objectsForThisVerb'"
			fi

		else # ! inItem
			if [[ $line =~ '<item obj' && ! $line =~ $regex_depr && ! $line =~ $regex_verb && ! $line =~ $regex_synonym ]]; then
				inItem=true
				object=${line#*\"}  # remove shortest match of .*" from the front
				object=${object%%\"*} # remove longest match of ".* from the back
				$debug && echo "Entered item tag at line=$lineNumber, parsed object=$object"
				[ "$object" == 'on' ] && inItem=false # Do not expose Amrit's puerile jest.
				[ "$object" == 'help' ] && inItem=false # Although 'help' is a verb, splunkrc_cmds.xml constructs it as an object; ugh.  We'll deal with the objects (topics) of 'splunk help' separately, below.
			fi
		fi

	done < $splunkrcCmdsXml
	$debug && echo "Processed $lineNumber lines.  Map keys: ${!verb_to_objects[*]}, values: ${verb_to_objects[@]}"

	# # # Oh wait, '<verb> deploy-server' aren't in splunkrc_cmds.xml; thanks, Jojy!!!!!
	for verb in reload enable disable display; do
		objectsForThisVerb=${verb_to_objects[$verb]}
		objectsForThisVerb="$objectsForThisVerb deploy-server"
		verb_to_objects[$verb]=$objectsForThisVerb
	done

	# # # Find the file with topics understood by 'splunk help <topic>' command, and extract list of topics.
	local readonly literalsPy=$splunkHome/lib/python2.7/site-packages/splunk/clilib/literals.py
	[ -e $literalsPy ] || die "Cannot find expected file $literalsPy"
	$debug && echo "Shall read help topics list from: $literalsPy"
	local readonly helpTopics=$(sed '/^addHelp/! d; s/^addHelp//; s/,.*$//; s/[^a-zA-Z_-]/ /g; s/^[ ]*//; s/[ ].*$//; /^$/ d' $literalsPy | sort | uniq)
	$debug && echo "Parsed help topics list as: $helpTopics"

	#######################################################
	# # # Write the completion function to tempfile: BEGIN.
	local readonly completionFunction=fSplunkComplete
	echo -e 'function '$completionFunction' () {' >> $tempfile
    echo -e '\tlocal wordCur=${COMP_WORDS[COMP_CWORD]}' >> $tempfile
   	echo -e '\tlocal wordPrev=${COMP_WORDS[COMP_CWORD-1]}' >> $tempfile
	echo -e '\tcase $wordPrev in' >> $tempfile

	# # # What can follow 'splunk' itself?  Verbs used in main.c to key the 'cmd_handlers' array; and verbs from splunkrc_cmds.xml; and 'help'.
	local readonly keys__cmd_handlers='ftr start startnoss stop restart restartss status rebuild train fsck clean-dispatch clean-srtemp validate verifyconfig anonymize find clean createssl juststopit migrate --version -version version httpport soapport spool ftw envvars _RAW_envvars _port_check cmd _rest_xml_dump search dispatch rtsearch livetail _normalizepath _internal logout btool pooling offline clone-prep-clear-config diag'
	local allVerbs="${!verb_to_objects[*]}"
	echo -e '\t\tsplunk)\n\t\t\tCOMPREPLY=( $(compgen -W "'$keys__cmd_handlers $allVerbs' help" -- $wordCur) ) ;;' >> $tempfile

	# # # What can follow 'splunk _internal'?  see cmd_internal() of main.c
	local readonly actions_internal='http mgmt https pre-flight-checks check-db call rpc rpc-auth soap-call soap-call-auth prefixcount totalcount check-xml-files first-time-run make-splunkweb-certs-and-var-run-merged'
	echo -e '\t\t_internal)\n\t\t\tCOMPREPLY=( $(compgen -W "'$actions_internal'" -- $wordCur) ) ;;' >> $tempfile

	# # # Options to 'splunk clean' are in CLI::clean() of src/main/Clean.cpp; to 'splunk fsck', in usageBanner of src/main/Fsck.cpp; to 'splunk migrate', in CLI::migrate() of src/main/Migration.cpp
	echo -e '\t\tclean)\n\t\t\tCOMPREPLY=( $(compgen -W "all eventdata globaldata userdata inputdata locks deployment-artifacts raft" -- $wordCur) ) ;;' >> $tempfile
	echo -e '\t\tfsck)\n\t\t\tCOMPREPLY=( $(compgen -W "scan repair clear-bloomfilter make-searchable" -- $wordCur) ) ;;' >> $tempfile
	echo -e '\t\tmigrate)\n\t\t\tCOMPREPLY=( $(compgen -W "input-records to-modular-inputs rename-cluster-app" -- $wordCur) ) ;;' >> $tempfile

	# # # List the help topics.
	echo -e '\t\thelp)\n\t\t\tCOMPREPLY=( $(compgen -W "'$helpTopics'" -- $wordCur) ) ;;' >> $tempfile

	# # # What can follow 'splunk cmd'?  any executable in SPLUNK_HOME/bin/
	echo -e '\t\tcmd)\n\t\t\tCOMPREPLY=( $(compgen -o default -o filenames -G "'$splunkHome'/bin/*" -- $wordCur) ) ;;' >> $tempfile

	# # # Finally, let each verb be completed by its objects.
	for verb in $allVerbs; do
		echo -e '\t\t'$verb')\n\t\t\tCOMPREPLY=( $(compgen -W "'${verb_to_objects[$verb]}'" -- $wordCur) ) ;;' >> $tempfile
	done

	# # # And if we've run out of suggestions, revert to bash's default completion behavior: filename completion.
	echo -e '\t\t*)\n\t\t\tCOMPREPLY=( $(compgen -f -- $wordCur) ) ;;' >> $tempfile

	echo -e '\tesac' >> $tempfile
	echo -e '}' >> $tempfile
	$debug && cp $tempfile $tempfile~bak
	# # # Write the completion function to tempfile: DONE.
	######################################################

	# # # Sanity check: source the tempfile, make sure that the function we wrote can be parsed and loaded by the shell.
	unset $completionFunction
	. $tempfile
	[ "`type -t $completionFunction`" == 'function' ] || die 'BUG: generated completion function cannot be parsed by bash'
}


if [ $SHLVL -eq 1 ]; then
	[ $# -ge 1 ] && echo "Ignoring supplied arguments: $@" >&2
	ifSourced
elif [ $SHLVL -eq 2 ]; then
	if [ $# -eq 2 ] && [ $1 == '--populateTempfile' ]; then
		ifInvoked $2
	else
		echo -e "This script must be sourced, like so:\n\n\t\033[1m. $0\033[0m\n"
	fi
else
	: # user is running screen(1) or something of the sort.
fi


# # # Clean up.
unset die ifSourced ifInvoked
