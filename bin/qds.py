#!/bin/env python

from qds_sdk.qubole import Qubole
from qds_sdk.commands import *
import qds_sdk.exception

import os
import sys
import traceback
import logging
from optparse import OptionParser

log = logging.getLogger("qds")

usage_str = ("Usage: \n"
             "qds [options] "
             "<hivecmd|hadoopcmd|pigcmd> <submit|run|check|cancel> [args .. ]\n"
             "\tsubmit [cmd-specific-args .. ] : submit cmd & print id \n"
             "\trun [cmd-specific-args .. ] : submit cmd & wait. print results \n"
             "\tcheck <id> : print the cmd object for this Id\n"
             "\tcancel <id> : cancels the cmd with this Id\n")

def usage():
    sys.stderr.write(usage_str)
    sys.exit(1)

def checkargs_id(args):
    if len(args) != 1:
        sys.stderr.write("expecting single argument command id\n")
        usage()


def submitaction(cmdclass, args):
    args = cmdclass.parse(args)
    if args is not None:
        cmd = cmdclass.create(**args)
        print "Submitted %s, Id: %s" % (cmdclass.__name__, cmd.id)


def runaction(cmdclass, args):
    args = cmdclass.parse(args)
    if args is not None:
        cmd = cmdclass.run(**args)
        log.info("Fetching results for %s, Id: %s" % (cmdclass.__name__, cmd.id))
        print cmd.get_results()


def checkaction(cmdclass, args):
    checkargs_id(args)
    o = cmdclass.find(args.pop(0))
    print str(o)
    return 0

def cancelaction(cmdclass, args):
    checkargs_id(args)
    cmdclass.cancel_id(args.pop(0))
    return 0


def cmdmain(cmd, args):
    cmdclassname = cmd[0].upper() + cmd[1:] + "Command"
    cmdclass = globals()[cmdclassname]


    actionset = set(["submit", "run", "check", "cancel"])
    if len(args) < 1:
        sys.stderr.write("missing argument containing action\n")
        usage()
    
    action = args.pop(0)
    if action not in actionset:
        sys.stderr.write("action must be one of <%s>\n" % "|".join(actionset))
        usage()


    return globals()[action + "action"](cmdclass, args)


def main():

    optparser = OptionParser(usage=usage_str)
    optparser.add_option("--token", dest="api_token", 
                         default=os.getenv('QDS_API_TOKEN'),
                         help="api token for accessing Qubole")
    optparser.add_option("--url", dest="api_url", 
                         default=os.getenv('QDS_API_URL'),
                         help="base url for QDS REST API")
    optparser.add_option("--version", dest="api_version", 
                         default=os.getenv('QDS_API_VERSION'),
                         help="version of REST API to access")
    optparser.add_option("--poll_interval", dest="poll_interval", 
                         default=os.getenv('QDS_POLL_INTERVAL'),
                         help="interval for polling API for completion and other events")

    optparser.add_option("-v", "--v", dest="verbose", action="store_true",
                         default=False,
                         help="verbose mode - info level logging")

    optparser.add_option("--vv", dest="chatty", action="store_true",
                         default=False,
                         help="very verbose mode - debug level logging")


    optparser.disable_interspersed_args()
    (options, args) = optparser.parse_args()

    if options.chatty:
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        # whatever is dictated by logging config
        pass

    if options.api_token is None:
        raise Exception("No API Token provided")

    if options.api_url is None:
        options.api_url = "https://api.qubole.com/api/";

    if options.api_version is None:
        options.api_version = "v1.2";

    if options.poll_interval is None:
        options.poll_interval = 5;

        
    Qubole.configure(api_token=options.api_token,
                     api_url=options.api_url,
                     version=options.api_version,
                     poll_interval=options.poll_interval)
                     

    if len(args) < 1:
        sys.stderr.write("Missing first argument containing command type\n")
        usage()

    cmdset = set(["hive", "pig", "hadoop"])
    cmdsuffix = "cmd"

    cmd = args.pop(0)

    if ((cmd.find(cmdsuffix) != len(cmd)-3) or
        (cmd[:cmd.find(cmdsuffix)] not in cmdset)):
        sys.stderr.write("First command must be one of <%s>\n" % "|".join(cmdset))
        usage()
        
    return cmdmain(cmd[:cmd.find(cmdsuffix)], args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except qds_sdk.exception.Error as e:
        sys.stderr.write("Error: Status code %s from url %s\n" % 
                         (e.request.status_code, e.request.url))
        sys.exit(1)
    except qds_sdk.exception.ParseError as e:
        sys.stderr.write("Error: %s\n" % str(e))
        sys.stderr.write("Usage: %s\n" % e.usage)
        sys.exit(2)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(3)
