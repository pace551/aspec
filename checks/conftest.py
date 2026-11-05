"""pytest session setup for checks/: drop inherited GIT_* repo variables.

Git exports GIT_DIR to hooks run from a linked worktree, and the pre-push hook runs this
suite. Left in place, it points every test's throwaway-repo git commands (and the scripts
they run) at the real repository. Tests build their own repos, so none of them needs it.
"""

import os

for _name in [n for n in os.environ if n.startswith("GIT_")]:
    del os.environ[_name]
