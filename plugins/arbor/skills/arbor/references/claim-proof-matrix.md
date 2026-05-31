# Claim Proof Matrix

Use this matrix when a workflow, skill, runtime, or release claim could be
overstated from weaker evidence. It separates visible output, source tree,
installed cache, and runtime evidence claims.

| Claim Type | Minimum Proof | Do Not Claim From |
| --- | --- | --- |
| Skill description quality | Frontmatter/static audit plus `check_plugin_adapters.py`. | A prose review that did not parse the frontmatter. |
| Visible output behavior | Captured rendered output such as `final-response.md`, or the strongest available rendered-output fixture with a weak-pass label. | Structured packets, review docs, or artifact creation alone. |
| Trigger routing behavior | Real replay or a documented deterministic substitute that exercises the user prompt shape. | Description wording alone. |
| Source tree behavior | Commands run against the edited source tree, with exact command and result recorded. | Installed cache or runtime assumptions. |
| Installed cache behavior | A cache sync report or source/cache diff against the versioned installed cache path. | Source tree checks alone. |
| Runtime evidence | Captured Codex or Claude runtime output, or an explicit weak-pass label naming the missing live proof. | Static checks, source-only tests, or cache presence alone. |
| Multi-runtime behavior | Separate Codex and Claude evidence, or a clearly labeled runtime gap. | Evidence from only one runtime. |
| Release/public action | Git/file side effect, command output, connector response, or external artifact evidence for the exact authorized action. | A prepared release packet or local readiness summary. |

Do not claim cache or runtime behavior from source-only checks. If the best
available proof is weaker than the claim, narrow the claim or add a weak-pass
label that names the missing proof.
