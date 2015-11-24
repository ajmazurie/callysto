
__all__ = ("install_kernel", "launch_kernel")

import logging

import ipykernel.kernelapp
import jupyter_client.kernelspec

from . import kernel

_logger = logging.getLogger(__file__)

def _ensure_kernel (kernel_class):
    if (not issubclass(kernel_class, kernel.BaseKernel)) or \
       (kernel_class == kernel.BaseKernel):
        raise ValueError(
            "invalid value for kernel_class (must be a subclass of BaseKernel)")

def install_kernel (kernel_module, kernel_class, user_only = True):
    _ensure_kernel(kernel_class)

    if (kernel_module is None):
        kernel_module = kernel_class.__module__

    kernel_spec_manager = jupyter_client.kernelspec.KernelSpecManager()

    # create the kernel specifications
    import json
    import os
    import shutil
    import tempfile

    kernel_spec = {
        "argv": [
            "python",
            "-m", kernel_module,
            "-f", "{connection_file}"],
        "display_name": kernel_class.implementation_name,
        "language": kernel_class.language_name}

    _logger.debug("kernel specifications: %s" % kernel_spec)

    kspec_path = tempfile.mkdtemp()
    kspec_fn = os.path.join(kspec_path, "kernel.json")

    json.dump(kernel_spec, open(kspec_fn, "w"),
        indent = 4, sort_keys = True, separators = (',', ': '))

    # install the kernel specifications
    _logger.debug("installing kernel %s" % kernel_class)
    kernel_spec_manager.install_kernel_spec(
        kspec_path,
        kernel_name = kernel_class.implementation_name,
        user = user_only)

    shutil.rmtree(kspec_path)

def launch_kernel (kernel_class, debug = False):
    _ensure_kernel(kernel_class)

    if (debug):
        logging.basicConfig(
            format = "[%(asctime)s] %(levelname)s: %(message)s",
            level = logging.DEBUG)

    _logger.debug("launching kernel %s" % kernel_class)
    ipykernel.kernelapp.IPKernelApp.launch_instance(kernel_class = kernel_class)
    _logger.debug("launching kernel %s: done" % kernel_class)
