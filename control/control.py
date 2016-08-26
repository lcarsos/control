"""
Definitions of the paths that Control can take. build, restart, etc.

Things that are needed:
  - Clearly defined global options when ./control is run
  - Clearly defined options when ./control build is run
  - Override global defaults with Controlfile
  - Override Controlfile settings with CLI arguments
  - Note that docker 1.9 needs docker-py 1.7.x and docker 1.10 needs docker-py 1.8
  - Calling build should remove the old image that was using that name
  - Calling rere should remove the old image after the container has been
    restarted to use the new image
"""

import logging
import signal
import sys

from control.cli_args import build_parser
from control.controlfile import Controlfile
from control.dclient import dclient
from control.functions import function_dispatch
from control.options import options
from control.service import MetaService

module_logger = logging.getLogger('control')
module_logger.setLevel(logging.DEBUG)


def sigint_handler(sig, frame):  # pylint: disable=unused-argument
    """Gracefully handle receiving ctrl-c"""
    print("Killing builds")
    sys.exit(130)


def main(args):
    """create the parser and decide how to run"""
    # Shut up requests because the user has to make a conscious choice to be
    # insecure
    global options
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    console_loghandler = logging.StreamHandler()
    signal.signal(signal.SIGINT, sigint_handler)

    parser = build_parser()
    parser.parse_args(args, namespace=options)
    console_loghandler.setLevel(logging.INFO)
    if options.debug:
        console_loghandler.setLevel(logging.DEBUG)
    module_logger.addHandler(console_loghandler)
    module_logger.debug("switching to debug logging")

    # Read in a Controlfile if one exists
    ctrlfile_location = options.controlfile
    ctrl = Controlfile(ctrlfile_location)

    if not dclient:
        print('Docker is not running. Please start docker.', file=sys.stderr)
        sys.exit(2)

    # If no services were specified on the command line, default to required
    if len(options.services) == 0:
        module_logger.debug('No options specified. Using required service list')
        options.services = ctrl.required_services()
    # Flatten the service list by replacing metaservices with their service lists
    for name in (name
                 for name in options.services
                 if isinstance(ctrl.services[name], MetaService)):
        options.services += ctrl.services[name].services
        options.services.remove(name)

    # Override image name if only one service discovered
    if options.image and len(options.services) == 1:
        ctrl.services[options.services[0]]['image'] = options.image
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.image and len(options.services) > 1:
        module_logger.info('Ignoring image specified in arguments. Too many services.')
    # Override container name if only one service
    if options.name and len(options.services) == 1:
        ctrl.services[options.services[0]]['name'] = options.name
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.name and len(options.services) > 1:
        module_logger.info('Ignoring container name specified in arguments. '
                           'Too many services to start')
    # Override dockerfile location if only one service discovered
    if options.dockerfile and len(options.services) == 1:
        ctrl.services[options.services[0]]['dockerfile'] = options.image
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.dockerfile and len(options.services) > 1:
        module_logger.info('Ignoring dockerfile specified in arguments. Too many services.')
    module_logger.debug(vars(options))

    ret = function_dispatch(options, ctrl)

    if not ret:
        sys.exit(1)
