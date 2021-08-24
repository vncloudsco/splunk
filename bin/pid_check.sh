#!/bin/sh

# tests to see if the given pid is held by a valid owner.
# Exit codes: 
# 0/success  pid is a valid owner -- service is up/locked
# 3          pid is not a valid owner (no such pid, or some other process)
#            3 is chosen here in keeping with the value from 'splunk status'
#            This value is used by the Linux Standard Base for "service is not running"
# 1          Error was encountered.
#
# Running the command with no arguments returns 0 also along with printing usage

usage() {
    if [ x"$1" = x ]; then
        fd=1
    else
        fd=$1
    fi
    echo >&$fd "Usage: $0 <type> <pid>"
    echo >&$fd "       valid types: conf-mutator, splunkd"
    echo >&$fd "       pid:         pid to check for ownership"
}

if [ $# = 0 ]; then
    usage
    exit
fi

if [ "$#" != 2 ]; then
    echo >&2 "$0: error. incorrect arguments provided."
    usage 2
    exit 1
fi

pid_type="$1"
check_pid="$2"

# Some system binaries will error/warn about control env variables
# they don't like or honor.  We want real errors reported, but these 
# "fake errors" will cry wolf all the time.  So give a fairly plain
# environment to 'ps'.
clean_env() {
    # Don't run some nonsystem ps (/usr/ucb etc)
    PATH=/usr/xpg4/bin:/usr/bin:/bin
    unset LIBPATH
    unset SHLIB_PATH
    unset PYTHONPATH
    # paranoia
    LC_ALL=C
    export LC_ALL
    # This is a bit sensitive to maximum line length, but it won't work in a
    # pipeline because that's a subshell.
    for env_var in `env | egrep '^(DYLD_|LD_)' | sed 's/=.*//'`; do
        unset $env_var
    done
}

check_mutator() {
    check_pid="$1"
    case `uname`x in
        x)
            echo >&2 "$0: error. uname did not provide the os name."
            exit 1
            ;;
        HP-UXx)
            # HP-UX doesn't implement -o unless an empty-string UNIX95 is in the env
            command_name=`UNIX95= ps -p "$check_pid" -o comm=`
            ;;
        *)
            command_name=`ps -p "$check_pid" -o comm=`
            ;;
    esac
    case "$command_name"x in
        # Some unixes show a path, some don't
        */splunkx|*/splunkdx|splunkx|splunkdx)
            has_valid_owner=true
            ;;
        *)
            # This includes no output, which means that pid isn't around
            has_valid_owner=false
            ;;
    esac
}

check_splunkd() {
    check_pid="$1"
    case `uname`x in
        x)
            echo >&2 "$0: error. uname did not provide the os name."
            exit 1
            ;;
        HP-UXx)
            # HP-UX doesn't implement -o unless an empty-string UNIX95 is in the env
            command_name=`UNIX95= ps -p "$check_pid" -o comm=`
            command_args=`UNIX95= ps -p "$check_pid" -o args=`
            command_ppid=`UNIX95= ps -p "$check_pid" -o ppid=`
            ;;
        FreeBSDx)
            command_name=`ps -p "$check_pid" -o comm=`
            # FreeBSD truncates the args unless -ww
            command_args=`ps -ww -p "$check_pid" -o args=`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
        SunOSx)
            command_name=`ps -p "$check_pid" -o comm=`
            # Solaris ps *always* truncates the args, but pargs does not
            command_args=`pargs -c -l "$check_pid" 2>/dev/null`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
        *)
            command_name=`ps -p "$check_pid" -o comm=`
            command_args=`ps -p "$check_pid" -o args=`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
    esac
    # get rid of leading whitespace for the ppid -- 
    # there could be whitespace for the other values, but we don't actually care
    set -- $command_ppid
    command_ppid=$1

    case "$command_name"x in 
        # Some unixes show a path, some don't
        */splunkdx|splunkdx)
            # ok!
            ;;
        *)
            # not splunkd
            has_valid_owner=false
            return
            ;;
    esac
    # Init does not exist in some environments :-(
    has_valid_owner=true
    return
    #case "$command_args"x in 
    #    *--nodaemonx)
    #        # the nodaemon switch is a good indicator it's the main splunkd
    #        has_valid_owner=true
    #        return
    #        ;;
    #    *)
    #        ;;
    #esac
    #case "$command_ppid"x in
    #    1x)
    #        # parent is init.
    #        has_valid_owner=true
    #        return
    #        ;;
    #    *)
    #        has_valid_owner=false
    #        return
    #        ;;
    #esac
}

check_splunkweb() {
    check_pid="$1"
    case `uname`x in
        x)
            echo >&2 "$0: error. uname did not provide the os name."
            exit 1
            ;;
        HP-UXx)
            # HP-UX doesn't implement -o unless an empty-string UNIX95 is in the env
            command_name=`UNIX95= ps -p "$check_pid" -o comm=`
            command_args=`UNIX95= ps -p "$check_pid" -o args=`
            command_ppid=`UNIX95= ps -p "$check_pid" -o ppid=`
            ;;
        FreeBSDx)
            command_name=`ps -p "$check_pid" -o comm=`
            # FreeBSD truncates the args unless -ww
            command_args=`ps -ww -p "$check_pid" -o args=`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
        SunOSx)
            command_name=`ps -p "$check_pid" -o comm=`
            # Solaris ps *always* truncates the args, but pargs does not
            command_args=`pargs -c -l "$check_pid" 2>/dev/null`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
        *)
            command_name=`ps -p "$check_pid" -o comm=`
            command_args=`ps -p "$check_pid" -o args=`
            command_ppid=`ps -p "$check_pid" -o ppid=`
            ;;
    esac
    # get rid of leading whitespace for the ppid -- 
    # there could be whitespace for the other values, but we don't actually care
    set -- $command_ppid
    command_ppid=$1

    case "$command_name"x in 
        # Some unixes show a path, some don't
        */pythonx|pythonx)
            # ok!
            ;;
        *)
            # not python, not splunkweb
            has_valid_owner=false
            return
            ;;
    esac
    case "$command_args"x in 
        *root.py*)
            # splunkweb contains the string 'root.py', because that's how it's started up
            ;;
        *)
            # python commands without root.py are not splunkweb
            has_valid_owner=false
            return
            ;;
    esac
    # init doesn't exist in some environments. :-(
    has_valid_owner=true
    return
    #case "$command_ppid"x in
    #    1x)
    #        # parent is init.
    #        has_valid_owner=true
    #        return
    #        ;;
    #    *)
    #        has_valid_owner=false
    #        return
    #        ;;
    #esac
}
clean_env

case "$pid_type"x in
    conf-mutatorx)
        check_mutator "$check_pid"
        ;;
    splunkdx)
        check_splunkd "$check_pid"
        ;;
    splunkwebx)
        check_splunkweb "$check_pid"
        ;;
    *)
        echo >&2 "$0: error. unknown pid type $pid_type"
        exit 1
        ;;
esac

if [ "$has_valid_owner"x = "true"x ]; then
    exit 0
else
    # using 3 value, in keeping with LSB that we use for 'splunk status' 
    # to mean "its not running"
    exit 3 
fi
