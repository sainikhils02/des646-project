"""Quick sanity check for LaTeX environment balance."""
import re
from pathlib import Path

content = Path("paper.tex").read_text(encoding="utf-8")
begins = re.findall(r"\\begin\{(\w+)\}", content)
ends = re.findall(r"\\end\{(\w+)\}", content)

from collections import Counter
bc, ec = Counter(begins), Counter(ends)
all_envs = set(list(bc.keys()) + list(ec.keys()))
ok = True
for env in sorted(all_envs):
    b, e = bc.get(env, 0), ec.get(env, 0)
    status = "OK" if b == e else "MISMATCH!"
    if b != e:
        ok = False
    print(f"  {env}: {b} begins, {e} ends - {status}")

print(f"\nTotal lines: {len(content.splitlines())}")
print(f"References: {content.count('bibitem')}")
print(f"Figures: {content.count('includegraphics')}")
print(f"Cite commands: {content.count('cite{')}")

# Check for unresolved refs
labels = set(re.findall(r"\\label\{([^}]+)\}", content))
refs = set(re.findall(r"\\ref\{([^}]+)\}", content))
undefined = refs - labels
if undefined:
    print(f"\nUNDEFINED REFS: {undefined}")
    ok = False
else:
    print(f"\nAll {len(refs)} refs resolve to labels.")

print(f"\nOverall: {'PASS' if ok else 'FAIL'}")
