"""2.137.0: Error reports stay private (feedback: "how can we make sure it never ends up public/uploaded to github").

  py tools/check_private.py      exit 1 (and says where) if anything could publish them

Error reports live only in the community board's database. Only a board admin's app reads them (GET /errors), and
it keeps the copy in its own data folder (error_reports.json) - never in the repo. This check fails when:
  - a GitHub workflow reads /errors or names error_reports (a workflow's logs and artifacts can be public)
  - a file named error_reports* is in the repo
  - the board serves GET /errors to anyone but an admin"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    bad = []
    for wf in glob.glob(os.path.join(ROOT, ".github", "workflows", "*.y*ml")):
        txt = open(wf, encoding="utf-8").read()
        if re.search(r"/errors\b|error_reports|app_errors", txt):
            bad.append(f"{os.path.relpath(wf, ROOT)}: a workflow touches error reports (its logs can be public)")
    for p in glob.glob(os.path.join(ROOT, "**", "error_reports*"), recursive=True):
        if "/tools/" not in p.replace("\\", "/"):
            bad.append(f"{os.path.relpath(p, ROOT)}: error reports in the repo")
    js = open(os.path.join(ROOT, "board", "src", "index.js"), encoding="utf-8").read()
    m = re.search(r"async function errorList\(([^)]*)\)\s*\{\s*([^\n]*)", js)
    if not m or "me?.admin" not in m.group(2):
        bad.append("board/src/index.js: GET /errors must start with the admin check")
    route = re.search(r'path === "/errors" && req.method === "GET"', js)
    gate = js.find('if (!me) return fail(401')
    if not route or gate < 0 or route.start() < gate:
        bad.append("board/src/index.js: GET /errors must come after the sign-in check")
    for b in bad:
        print("PRIVATE:", b)
    print("check_private: ok" if not bad else f"check_private: {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
