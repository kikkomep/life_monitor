
import datetime
import logging
import time
from typing import Optional

from apscheduler.triggers.interval import IntervalTrigger
from git import List

from lifemonitor.api.models.notifications import WorkflowStatusNotification
from lifemonitor.api.models.testsuites.testbuild import BuildStatus, TestBuild
from lifemonitor.api.serializers import BuildSummarySchema
from lifemonitor.auth.models import EventType, Notification
from lifemonitor.cache import Timeout
from lifemonitor.integrations.github.settings import GithubUserSettings
from lifemonitor.tasks.scheduler import TASK_EXPIRATION_TIME, schedule
from lifemonitor.utils import notify_workflow_version_updates

# set module level logger
logger = logging.getLogger(__name__)


logger.info("Importing task definitions")


@schedule(trigger=IntervalTrigger(seconds=Timeout.WORKFLOW * 3 / 4),
          queue_name='builds', options={'max_retries': 3, 'max_age': TASK_EXPIRATION_TIME})
def check_workflows():
    from flask import current_app

    from lifemonitor.api.controllers import workflows_rocrate_download
    from lifemonitor.api.models import Workflow
    from lifemonitor.auth.services import login_user, logout_user

    logger.info("Starting 'check_workflows' task....")
    for w in Workflow.all():
        try:
            for v in w.versions.values():
                with v.cache.transaction(str(v)):
                    u = v.submitter
                    with current_app.test_request_context():
                        try:
                            if u is not None:
                                login_user(u)
                            logger.info("Updating RO-Crate...")
                            workflows_rocrate_download(w.uuid, v.version)
                            logger.info("Updating RO-Crate... DONE")
                        except Exception as e:
                            logger.error(f"Error when updating the workflow {w}: {str(e)}")
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.exception(e)
                        finally:
                            try:
                                logout_user()
                            except Exception as e:
                                logger.debug(e)
        except Exception as e:
            logger.error("Error when executing task 'check_workflows': %s", str(e))
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
    logger.info("Starting 'check_workflows' task.... DONE!")


@schedule(trigger=IntervalTrigger(seconds=Timeout.BUILD * 3 / 4),
          queue_name='builds', options={'max_retries': 3, 'max_age': TASK_EXPIRATION_TIME})
def check_last_build():
    from lifemonitor.api.models import Workflow

    logger.info("Starting 'check_last build' task...")
    workflows = Workflow.all() if not workflow_uuid else [Workflow.find_by_uuid(workflow_uuid)]
    for w in workflows:
        logger.debug("Processing workflow: %r -- %r", w.name, w.latest_version.name)
        try:
            for workflow_version in w.versions.values():
                if workflow_version and len(workflow_version.github_versions) > 0:
                    logger.warning("Workflow skipped because updated via github app")
                    continue
                for s in workflow_version.test_suites:
                    logger.info("Updating workflow: %r", w)
                    for i in s.test_instances:
                        # old_builds = i.get_test_builds(limit=10)
                        with i.cache.transaction(str(i)):
                            builds = i.get_test_builds(limit=10)
                            logger.info("Updating latest builds: %r", builds)
                            for b in builds:
                                logger.info("Updating build: %r", i.get_test_build(b.id))
                            i.save(commit=False, flush=False)
                            workflow_version.save()
                            notify_workflow_version_updates([workflow_version], type='sync')
                            last_build = i.last_test_build
                            logger.debug("Latest build: %r", last_build)

                            # check state transition
                            if last_build:
                                logger.debug("Latest build status: %r", last_build.status)
                                failed = last_build.status == BuildStatus.FAILED
                                if len(builds) == 1 or \
                                        builds[0].status in (BuildStatus.FAILED, BuildStatus.PASSED) and \
                                        builds[1].status in (BuildStatus.FAILED, BuildStatus.PASSED) and \
                                        len(builds) > 1 and builds[1].status != last_build.status:
                                    logger.error("Updating latest build: %r", last_build)
                                    notification_name = f"{last_build} {'FAILED' if failed else 'RECOVERED'}"
                                    if len(Notification.find_by_name(notification_name)) == 0:
                                        users = workflow_version.workflow.get_subscribers()
                                        n = WorkflowStatusNotification(
                                            EventType.BUILD_FAILED if failed else EventType.BUILD_RECOVERED,
                                            notification_name,
                                            {'build': BuildSummarySchema(exclude_nested=False).dump(last_build)},
                                            users)
                                        n.save()
                # save workflow version and notify updates
                workflow_version.save()
                notify_workflow_version_updates([workflow_version], type='sync')
        except Exception as e:
            logger.error("Error when executing task 'check_last_build': %s", str(e))
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
    logger.info("Checking last build: DONE!")


@schedule(trigger=IntervalTrigger(seconds=Timeout.BUILD),
          queue_name='builds', options={'max_retries': 0, 'max_age': TASK_EXPIRATION_TIME})
def periodic_builds(workflows_list: Optional[List[str]] = None):
    from lifemonitor.api.models import Workflow
    logger.info("Task 'periodic builds': STARTED!")
    workflows = Workflow.all() if not workflows_list else [Workflow.find_by_uuid(w) for w in workflows_list]
    updated_workflows = set()
    for w in workflows:
        for workflow_version in w.versions.values():
            workflow_updated = False

            periodic_builds_enabled = False
            periodic_builds_interval: Optional[datetime.timedelta] = None

            # try to get the configuration for the workflow version
            found_conifg = False
            try:
                config = workflow_version.repository.config
                periodic_builds_enabled = config.periodic_builds
                periodic_builds_interval = config.periodic_builds_interval_as_timedelta
                found_conifg = True
                logger.debug(f"Using repository configuration for the workflow {workflow_version}: {config}")
            except Exception as e:
                logger.error(f"Error when getting the configuration for the workflow {workflow_version}: {str(e)}")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)

            # if the configuration is not available, try to get the user configuration
            if not found_conifg:
                try:
                    config: GithubUserSettings = workflow_version.submitter.github_settings
                    periodic_builds_enabled = config.periodic_builds
                    periodic_builds_interval = config.periodic_builds_interval_as_timedelta
                    logger.debug(f"Using global Github user settings for the workflow {workflow_version}: {config}")
                except Exception as e:
                    logger.error(f"Error when getting the user configuration for the workflow {workflow_version}: {str(e)}")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception(e)

            for s in workflow_version.test_suites:
                for i in s.test_instances:
                    try:
                        last_build = None
                        with i.cache.transaction(str(i)):
                            last_build: TestBuild = i.last_test_build
                        if not last_build:
                            logger.warning("No build to rerun")
                        else:
                            # calculate the datetime (in UTC format) of the last run of the last build
                            last_exec_datetime = datetime.datetime.fromtimestamp(last_build.timestamp)

                            # Summary of the workflow version and periodic builds configuration
                            logger.debug("Last build: %r", last_build)
                            logger.debug("Last build status: %r", last_build.status)
                            logger.debug("Last build timestamp: %r", last_exec_datetime)
                            logger.debug("Periodic builds enabled: %r", periodic_builds_enabled)
                            logger.debug("Periodic builds interval: %r", periodic_builds_interval)

                            # check if periodic builds are enabled
                            if not periodic_builds_enabled:
                                logger.info("Skipping periodic build of test suite %s on test instance %s for workflow version %s (periodic builds disabled)", s, i, workflow_version)
                            # if periodic builds are enabled, check if a new build is needed
                            else:
                                # set the current time in UTC timezone
                                current_time = datetime.datetime.utcnow()
                                logger.warning("Current time: %r", current_time)
                                # compute the elapsed time since the last build
                                elapsed_time = current_time - last_exec_datetime
                                logger.warning("Elapsed time: %r", elapsed_time)
                                # check if the elapsed time is greater than the periodic builds interval
                                if elapsed_time <= periodic_builds_interval:
                                    logger.info("Skipping periodic build of test suite %s on test instance %s for workflow version %s (elapsed time %s)", s, i, workflow_version, elapsed_time)
                                # if the elapsed time is greater than the periodic builds interval, start a new build
                                else:
                                    logger.warning("Triggered periodic build of test suite %s on test instance %s for workflow version %s (elapsed time %s)", s, i, workflow_version, elapsed_time)
                                    with last_build.cache.transaction(str(last_build)):
                                        logger.info("Triggering build of test suite %s on test instance %s for workflow version %s", s, i, workflow_version)
                                        time.sleep(10)
                                        if i.start_test_build():
                                            workflow_updated = True

                    except Exception as e:
                        logger.error("Error when starting periodic build on test instance %s: %s", i, str(e))
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.exception(e)

            if workflow_updated:
                # save workflow version
                updated_workflows.add(workflow_version)

    # notify updates to the live clients
    notify_workflow_version_updates(updated_workflows, type='sync')
    logger.info("Task 'periodic builds': DONE!")
