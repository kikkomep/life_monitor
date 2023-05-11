
import logging

from apscheduler.triggers.cron import CronTrigger

from lifemonitor.auth.models import User
from lifemonitor.integrations.github import LifeMonitorGithubApp
from lifemonitor.integrations.github.controllers import get_event_handler
from lifemonitor.integrations.github.events import GithubEvent
from lifemonitor.integrations.github.settings import GithubUserSettings

from ..scheduler import TASK_EXPIRATION_TIME, schedule

# set module level logger
logger = logging.getLogger(__name__)


logger.info("Importing task definitions")


@schedule(name="ping", queue_name="github")
def ping(name: str = "Unknown"):
    logger.info(f"Pong, {name}")
    return "pong"


@schedule(name='githubEventHandler', queue_name="github", options={'max_retries': 0, 'max_age': TASK_EXPIRATION_TIME})
def handle_event(event):
    logger.debug("Github event: %r", event)

    e = GithubEvent.from_json(event)
    logger.debug("Github event: %r", e)
    logger.debug("Github event type: %r", e.type)
    logger.debug("Github event installation: %r", e.installation)
    logger.debug("Github installation target id: %r", e.installation.target_id)
    logger.debug("Github installation target type: %r", e.installation.target_type)

    try:
        # use the try block to avoid exceptions when the event is not related to a single repository
        # (i.e. the installation event)
        logger.debug("Github event repository reference: %r", e.repository_reference)
        logger.debug("Github event repository reference branch: %r", e.repository_reference.branch)
        logger.debug("Github event repository reference tag: %r", e.repository_reference.tag)
        logger.debug("Github event repository owner: %r", e.repository_reference.owner_id)
    except ValueError as ex:
        logger.debug("Unable to get repository reference from event: %r", ex)

    # find user by provider user id
    installation_sender = e.sender_as_user
    logger.debug("Installation sender: %r", installation_sender)
    if not installation_sender:
        logger.warning(f"No LifeMonitor user associated to the GitHub sender {e.sender_id} for the repository")
        return

    logger.debug("Installation sender ID: %r", installation_sender.username)

    # check if the target user is an organization and if so, ensure that the organization is mapped to a LifeMonitor user
    if e.installation.target_type == "Organization":
        gh_app = LifeMonitorGithubApp.get_instance()
        org = gh_app.get_organization(e.installation.target_id)
        # return "ok", 200
        logger.debug("Organization: %r", org)
        if not org:
            org = gh_app.register_organization(e.installation.account._rawData)
        if not org:
            logger.warning("Unable to find or register the organization")
            return "Unable to find or register the organization", 400

    gh_settings: GithubUserSettings = installation_sender.github_settings
    logger.debug("Github settings: %r", gh_settings)
    if not gh_settings:
        logger.warning("No GitHub settings found for the installed repository")
        return

    # check if the Github integration is enabled
    if not gh_settings.enable_integration:
        logger.warning("GitHub integration is not enabled")
        return

    # Dispatch event to the proper handler
    event_handler = get_event_handler(e.type)
    logger.debug("Event handler: %r", event_handler)
    if event_handler:
        try:
            return event_handler(e)
        except Exception as ex:
            logger.error(ex)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(ex)

    logger.warning("No handler for GitHub event: %r", e.type)


@schedule(trigger=CronTrigger(minute=0, hour=4),
          queue_name='github', options={'max_retries': 0, 'max_age': TASK_EXPIRATION_TIME})
def check_installations():
    gh_app = LifeMonitorGithubApp.get_instance()
    installations = [str(_.id) for _ in gh_app.installations]
    logger.debug("Installations: %r", installations)
    for u in User.all():
        for i in u.github_settings.installations:
            installation_id = str(i['info']['id'])
            if installation_id not in installations:
                u.github_settings.remove_installation(installation_id)
                logger.info(f"Installation {installation_id} removed from account of user '{u.id}'")
            else:
                logger.debug(f"Installation {installation_id} still alive")
        u.save()
