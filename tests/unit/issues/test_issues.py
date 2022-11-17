# Copyright (c) 2020-2021 CRS4
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

import pytest
from lifemonitor.api.models.issues.common.files.missing import \
    MissingWorkflowFile
from lifemonitor.api.models.repositories import ZippedWorkflowRepository
from lifemonitor.api.models.repositories.local import LocalWorkflowRepository

logger = logging.getLogger(__name__)


@pytest.fixture
def crates_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


@pytest.fixture
def repository(crates_path) -> LocalWorkflowRepository:
    repo = ZippedWorkflowRepository(
        os.path.join(crates_path, 'ro-crate-galaxy-sortchangecase.crate.zip'), auto_cleanup=False)
    return repo


@pytest.fixture
def issue() -> MissingWorkflowFile:
    return MissingWorkflowFile()


def test_save(repository: LocalWorkflowRepository, issue: MissingWorkflowFile):
    logger.debug("Workflow RO-Crate: %r", repository)

    # detect workflow file
    workflow_file = repository.find_workflow()
    logger.debug("Detected workflow file: %r", workflow_file)
    assert workflow_file, "Workflow file not found"

    # Temporary remove the workflow file from the repo
    repository.remove_file(workflow_file)
    logger.debug(repository._transient_files)
    assert repository.find_workflow() is None, "Unexpected workflow on repo"

    # save temp change
    repository.save()
    logger.debug("Local path: %r", repository.local_path)

    # try to find the removed workflow file
    workflow_file = repository.find_workflow()
    logger.debug("Detected workflow file: %r", workflow_file)
    assert workflow_file is None, "Unexpected workflow found"
