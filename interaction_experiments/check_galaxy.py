# Copyright (c) 2020 CRS4
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""\
Execute a Galaxy workflow from a crate and check results.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile

import yaml
import lifemonitor.test_params as tp

YamlDumper = getattr(yaml, "CDumper", getattr(yaml, "Dumper"))
METADATA_BASENAME = "ro-crate-metadata.jsonld"
GALAXY_IMG = "bgruening/galaxy-stable:20.05"


# https://github.com/workflowhub-eu/about/wiki/Workflow-RO-Crate
# https://researchobject.github.io/ro-crate/1.0/
def parse_metadata(crate_dir):
    fn = os.path.join(crate_dir, METADATA_BASENAME)
    if not os.path.isfile(fn):
        raise RuntimeError(f"{METADATA_BASENAME} not found in {crate_dir}")
    with open(fn, "rt") as f:
        json_data = json.load(f)
    entities = {_["@id"]: _ for _ in json_data["@graph"]}
    md_desc = entities[METADATA_BASENAME]
    root = entities[md_desc["about"]["@id"]]
    main = entities[root["mainEntity"]["@id"]]
    assert main["@type"] == ["File", "SoftwareSourceCode", "Workflow"]
    # Dataset @id SHOULD end with /
    return {
        "main": main["@id"],
        "test": "test" in [_.rstrip("/") for _ in entities]
    }


# pip install planemo
def check_workflow(wf_fn, tests):
    wd = tempfile.mkdtemp(prefix="check_galaxy_")
    wf_bn = os.path.basename(wf_fn)
    wf_tmp_fn = os.path.join(wd, wf_bn)
    shutil.copy2(wf_fn, wf_tmp_fn)
    head, tail = os.path.splitext(wf_bn)
    test_fn = os.path.join(wd, f"{head}-test.yml")
    for t in tests:
        print("RUNNING", t.name)
        assert t.definition.engine.type == "planemo"
        cases = tp.read_planemo(t.definition.path)
        tp.paths_to_abs(cases, t.definition.path)
        with open(test_fn, "wt") as f:
            yaml.dump(cases, f, YamlDumper)
        cmd = ["planemo", "test", "--engine", "docker_galaxy",
               "--docker_galaxy_image", GALAXY_IMG, wf_tmp_fn]
        p = subprocess.run(cmd)
        p.check_returncode()
        print(f"{t.name}: OK")
    shutil.rmtree(wd)


def main(args):
    metadata = parse_metadata(args.crate_dir)
    wf_fn = os.path.join(args.crate_dir, metadata["main"])
    test_dir = os.path.join(args.crate_dir, "test")
    if not os.path.isdir(test_dir):
        if metadata["test"]:
            raise RuntimeError("test dir not found")
        else:
            print("crate has no tests, nothing to do")
            return
    cfg_fn = os.path.join(test_dir, "test-metadata.json")
    tests = tp.read_tests(cfg_fn, abs_paths=True)
    check_workflow(wf_fn, tests)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("crate_dir", metavar="CRATE_DIR",
                        help="top-level crate directory")
    main(parser.parse_args())
