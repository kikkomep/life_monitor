# Copyright (c) 2020-2022 CRS4
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os

from prometheus_client import Info
from prometheus_flask_exporter import PrometheusMetrics

import lifemonitor.metrics.controller as controller
from lifemonitor import __version__ as version
from lifemonitor.auth.services import authorized_by_session_or_apikey

from . import model, services

# Config a module level logger
logger = logging.getLogger(__name__)

# Set the metrics endpoint
__METRICS_ENDPOINT__ = "/metrics"

# Set the global prefix for LifeMonitor metrics
__METRICS_PREFIX__ = 'lifemonitor_api'

# expose metrics class
metrics: PrometheusMetrics = None


def init_metrics(app, prom_registry=None):
    global metrics

    # Register the '/metrics' endpoint
    controller.register_blueprint(app, __METRICS_ENDPOINT__, __METRICS_PREFIX__)

    # configure prometheus exporter
    # must be configured after the routes are registered
    metrics_class = None
    if os.environ.get('FLASK_ENV') == 'production':
        if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
            from prometheus_flask_exporter.multiprocess import \
                GunicornPrometheusMetrics
            metrics_class = GunicornPrometheusMetrics
        else:
            logger.warning("Unable to start multiprocess prometheus exporter: 'PROMETHEUS_MULTIPROC_DIR' not set."
                           f"Metrics will be exposed through the `{__METRICS_ENDPOINT__}` endpoint.")
    if not metrics_class:
        metrics_class = PrometheusMetrics

    metrics = metrics_class(app, defaults_prefix=__METRICS_PREFIX__, registry=prom_registry, metrics_decorator=authorized_by_session_or_apikey)
    app.metrics = metrics

    app_version = Info(f"{__METRICS_PREFIX__}_app_version", "LifeMonitor service version")
    app_version.info({'version': version})

    # Set prefix for lifemonitor metrics
    model.PREFIX = __METRICS_PREFIX__

    # Initialize metrics
    services.update_stats()
