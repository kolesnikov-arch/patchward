const bundleFiles = [
  "requirement.md",
  "acceptance_test.py",
  "agent_self_test.py",
  "change.diff",
  "verification.log",
  "verdict.json",
  "evidence_trace.md",
  "decision.md"
];

const flowNodes = [
  ["requirement", "Requirement", "stated behavior"],
  ["accept_test", "Acceptance Test", "authored fix-blind"],
  ["change", "Agent Change", "agent proposes"],
  ["verify", "Independent Verification", "evidence the agent didn't author"],
  ["verdict", "Verdict", "accept / review / reject"],
  ["decision", "Decision", "human authority"]
];

const scenarios = {
  accept: {
    state: "pass",
    verdict: "Accept",
    statusText: "Independently verified",
    realCase: `In the published held-out evaluation the layer issued <strong>zero</strong> confident accepts — with only a thin fix-blind oracle, correct fixes honestly stay in <em>Review</em> (disclosed in the <a href="https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md">results</a>, §4). A richer independent oracle — a project's own test suite — is what upgrades Review toward Accept.`,
    metrics: {
      selfTest: "passed (not decisive)",
      acceptTest: "3 / 3 passed",
      regression: "clean",
      action: "accept"
    },
    artifacts: {
      requirement: {
        type: "requirement.md",
        title: "Requirement",
        copy: `
          <p>The change must do what the requirement states. Trust starts from the requirement, not from the agent's claim that it is done.</p>
          <ul>
            <li><code>parse_duration</code> ignores minutes and returns the wrong number of seconds.</li>
            <li>The expected behavior is given by examples in the issue.</li>
          </ul>
          <span class="tag pass">conformance target</span>
        `,
        code: `# Issue — DURATIONS-01

parse_duration() currently parses only the hours component and drops minutes,
so it returns the wrong number of seconds.

Required behavior (from the issue):
  parse_duration("1h30m") == 5400
  parse_duration("45m")   == 2700
  parse_duration("2h")    == 7200`
      },
      accept_test: {
        type: "acceptance_test.py",
        title: "Acceptance Test (fix-blind)",
        copy: `
          <p>Authored from the <strong>requirement only</strong> — before, and blind to, the agent's fix. It encodes what conformance means, independent of how the change is written.</p>
          <ul>
            <li>Derived from the issue's stated examples.</li>
            <li>Never sees the agent's solution or the hidden reference oracle.</li>
          </ul>
        `,
        code: `# acceptance_test.py
# Authored from the requirement only. The author never saw the agent's
# fix or the project's own tests.
from durations import parse_duration

def test_hours_and_minutes():
    assert parse_duration("1h30m") == 5400

def test_minutes_only():
    assert parse_duration("45m") == 2700

def test_hours_only():
    assert parse_duration("2h") == 7200`
      },
      change: {
        type: "agent_self_test.py",
        title: "Agent Change + its own test",
        copy: `
          <p>The agent proposes a fix <em>and</em> writes a test that vouches for it. That self-authored test is <strong>self-referential</strong> — it cannot, by itself, establish trust.</p>
          <ul>
            <li>Here the change is genuinely correct.</li>
            <li>But notice: a self-test passes for a right fix and a wrong one alike — so it is treated as informational, not decisive.</li>
          </ul>
        `,
        code: `# test added by the agent alongside its change (self-referential)
def test_parses_1h30m():
    assert parse_duration("1h30m") == 5400`
      },
      diff: {
        type: "change.diff",
        title: "Diff",
        copy: `
          <p>The proposed change. It now accumulates every <code>hours</code> and <code>minutes</code> component instead of only hours.</p>
          <ul>
            <li>This is the candidate the verdict is formed about.</li>
          </ul>
        `,
        code: `--- a/durations.py
+++ b/durations.py
@@
-def parse_duration(text: str) -> int:
-    # only handled the hours component
-    m = re.match(r"(\\d+)h", text)
-    return int(m.group(1)) * 3600 if m else 0
+def parse_duration(text: str) -> int:
+    total = 0
+    for value, unit in re.findall(r"(\\d+)([hm])", text):
+        total += int(value) * (3600 if unit == "h" else 60)
+    return total`
      },
      verify: {
        type: "verification.log",
        title: "Independent Verification",
        copy: `
          <p>The decision is formed from evidence the agent never controlled: the fix-blind acceptance test plus a regression check. The agent's own test is shown — but only as context.</p>
          <ul>
            <li>Acceptance test: 3 / 3 pass.</li>
            <li>Regression: previously-passing tests still pass.</li>
            <li>Leak-safe: the hidden oracle is never run or inspected.</li>
          </ul>
        `,
        code: `=== Independent verification ===

Agent's own test (informational only — self-referential):
  test_parses_1h30m ............ PASSED

Fix-blind acceptance test (decisive):
  test_hours_and_minutes ....... PASSED   parse_duration("1h30m") == 5400
  test_minutes_only ............ PASSED   parse_duration("45m")   == 2700
  test_hours_only .............. PASSED   parse_duration("2h")    == 7200

Regression check (existing behavior preserved):
  18 / 18 previously-passing tests still pass

Leak-safety: the hidden reference oracle was not run or inspected.`
      },
      verdict: {
        type: "verdict.json",
        title: "Verdict",
        copy: `
          <p>The change conforms to the requirement on independent evidence, and nothing regressed. The accept is <strong>earned</strong>, not asserted.</p>
          <ul>
            <li>Basis: independent, not the agent's self-report.</li>
          </ul>
          <span class="tag pass">accept</span>
        `,
        code: `{
  "verdict": "accept",
  "basis": "independent",
  "agent_self_test": "passed (not used as the deciding signal)",
  "acceptance_test_fix_blind": "3/3 passed",
  "regression_check": "clean",
  "conforms_to_requirement": true,
  "note": "Accept is earned by evidence the agent did not author."
}`
      },
      trace: {
        type: "evidence_trace.md",
        title: "Evidence Trace",
        copy: `
          <p>Every input to the verdict is archived, so the same evidence yields the same decision. A reproducible decision can be audited; an opinion cannot.</p>
        `,
        code: `# Evidence Trace — DURATIONS-01

requirement.md       stated behavior (examples)
acceptance_test.py   authored fix-blind, from the requirement
change.diff          the agent's proposed change
verification.log     acceptance 3/3 + regression clean
verdict.json         accept (independent)

Reproducible: same evidence -> same verdict.`
      },
      decision: {
        type: "decision.md",
        title: "Decision",
        copy: `
          <p>An accept the organization can rely on, because it rests on independent evidence rather than the agent's word.</p>
        `,
        code: `# Decision — DURATIONS-01

Verdict: ACCEPT (independently verified)

The change conforms to the stated requirement and introduces no regression.
No human escalation required; merge may proceed under policy.`
      }
    }
  },

  review: {
    state: "review",
    verdict: "Review",
    statusText: "Escalated — requirement underspecified",
    realCase: `Measured counterpart: <code>django__django-13321</code> (held-out #11) — both arms produced a near-identical incomplete fix from the same underspecified issue. Ungated, it <strong>shipped silently</strong> (a false-accept); gated, the same fix was delivered flagged <em>Review — could not verify</em>. Identical capability; the difference is accountability. <a href="https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md">Results §3</a>.`,
    metrics: {
      selfTest: "passed (not decisive)",
      acceptTest: "specified part only",
      regression: "clean",
      action: "review / escalate"
    },
    artifacts: {
      requirement: {
        type: "requirement.md",
        title: "Requirement",
        copy: `
          <p>Some requirements are <strong>underspecified</strong>: they state the behavior but not every detail. An honest layer must not invent the missing part.</p>
          <ul>
            <li>A dotted blueprint name must raise an error.</li>
            <li>The issue does <em>not</em> say which exception type or message.</li>
          </ul>
          <span class="tag warn">partially specified</span>
        `,
        code: `# Issue — BLUEPRINT-07

Registering a blueprint whose name contains a dot (".") must be rejected,
because dotted names break nested-blueprint lookups.

Required:
  - a name containing "." must raise an error at registration time

Not stated:
  - which error / exception type
  - the exact message`
      },
      accept_test: {
        type: "acceptance_test.py",
        title: "Acceptance Test (fix-blind)",
        copy: `
          <p>Authored from the requirement only — so it can assert <strong>only what the requirement determines</strong>. It checks that an error is raised, and deliberately does not pin the exception type.</p>
          <ul>
            <li>Specified behavior: an error is raised for a dotted name.</li>
            <li>Unspecified: the exact type — so it cannot be independently confirmed.</li>
          </ul>
        `,
        code: `# acceptance_test.py
# The requirement says "raise an error" but does NOT pin the exception
# type, so the test can only assert the SPECIFIED behavior.
import pytest
from app import make_blueprint

def test_dotted_name_is_rejected():
    with pytest.raises(Exception):      # type intentionally unspecified
        make_blueprint("admin.users")

def test_plain_name_is_allowed():
    make_blueprint("admin")             # must not raise`
      },
      change: {
        type: "agent_self_test.py",
        title: "Agent Change + its own test",
        copy: `
          <p>The agent raises <code>AssertionError</code> (via <code>assert</code>) and writes a self-test that asserts exactly that. The self-test is green — but it only confirms the agent's own choice.</p>
          <ul>
            <li>Is <code>AssertionError</code> the right contract? The requirement doesn't say.</li>
          </ul>
        `,
        code: `# test added by the agent (self-referential)
def test_dotted_rejected():
    with pytest.raises(AssertionError):
        make_blueprint("admin.users")`
      },
      diff: {
        type: "change.diff",
        title: "Diff",
        copy: `
          <p>The proposed change. It rejects dotted names — using an <code>assert</code>, which raises <code>AssertionError</code>.</p>
        `,
        code: `--- a/app.py
+++ b/app.py
@@
 def make_blueprint(name: str) -> Blueprint:
+    assert "." not in name, "blueprint name may not contain a dot"
     return Blueprint(name)`
      },
      verify: {
        type: "verification.log",
        title: "Independent Verification",
        copy: `
          <p>The specified behavior verifies. But the requirement underdetermines the rest, so the layer reports <strong>partial coverage</strong> rather than guessing.</p>
          <ul>
            <li>"An error is raised" — confirmed.</li>
            <li>"Which error" — not stated, cannot be confirmed.</li>
          </ul>
        `,
        code: `=== Independent verification ===

Agent's own test (informational only — self-referential):
  test_dotted_rejected ......... PASSED

Fix-blind acceptance test (decisive):
  test_dotted_name_is_rejected . PASSED   (some error is raised)
  test_plain_name_is_allowed ... PASSED

Regression check:
  31 / 31 previously-passing tests still pass

Specification coverage:
  PARTIAL — the requirement does not state the exception type or message,
  so conformance beyond "an error is raised" cannot be confirmed.

Leak-safety: the hidden reference oracle was not run or inspected.`
      },
      verdict: {
        type: "verdict.json",
        title: "Verdict",
        copy: `
          <p>The honest answer is the third state: the layer verified what the requirement specified and <strong>escalates the rest</strong> instead of issuing a confident accept on a detail it cannot check.</p>
          <ul>
            <li>"Review" is not a failure — it is the system knowing what it does not know.</li>
          </ul>
          <span class="tag warn">review</span>
        `,
        code: `{
  "verdict": "review",
  "basis": "independent",
  "agent_self_test": "passed (not used as the deciding signal)",
  "acceptance_test_fix_blind": "specified behavior passed",
  "specification_coverage": "partial",
  "reason": "The requirement underspecifies the error type; the independent test can confirm only that an error is raised. The unspecified part is escalated, not guessed.",
  "public_label": "review / needs human review"
}`
      },
      trace: {
        type: "evidence_trace.md",
        title: "Evidence Trace",
        copy: `
          <p>The trace records both what was confirmed and what could not be — so the escalation is legible to the human who picks it up.</p>
        `,
        code: `# Evidence Trace — BLUEPRINT-07

requirement.md       behavior stated; exception type NOT stated
acceptance_test.py   asserts "an error is raised" only
change.diff          raises AssertionError via assert
verification.log     specified behavior PASSED; coverage PARTIAL
verdict.json         review (escalate the unspecified part)

Reproducible: same evidence -> same verdict.`
      },
      decision: {
        type: "decision.md",
        title: "Decision",
        copy: `
          <p>A human resolves the part the specification left open. "Not sure" is recorded and routed — never silently shipped as an accept.</p>
        `,
        code: `# Decision — BLUEPRINT-07

Verdict: REVIEW (escalate to a human)

The specified behavior is verified; the requirement does not determine the
exception type, so the layer does not assert a confident accept.

A human decides whether AssertionError is acceptable or the contract should
be tightened (e.g. ValueError). The uncertainty is surfaced, not hidden.`
      }
    }
  },

  reject: {
    state: "block",
    verdict: "Reject",
    statusText: "Confidently wrong — caught independently",
    realCase: `Measured counterparts: <code>sympy__sympy-22840</code> — the candidate fix would have broken <strong>36 existing tests</strong>; the isolated verification run caught it and blocked, while the ungated arm shipped its own wrong variant silently. And <code>sympy__sympy-16503</code> — the ungated agent rewrote an existing test to hide its wrong fix; the gated arm cannot edit tests, and its wrong fix was blocked. <a href="https://github.com/kolesnikov-arch/patchward/blob/main/RESULTS.md">Results §3</a>.`,
    metrics: {
      selfTest: "passed (not decisive)",
      acceptTest: "1 / 2 — accented case fails",
      regression: "clean",
      action: "reject"
    },
    artifacts: {
      requirement: {
        type: "requirement.md",
        title: "Requirement",
        copy: `
          <p>The case the whole framework exists for: a change that <strong>looks</strong> done and passes its own test, but does not actually conform.</p>
          <ul>
            <li><code>slugify</code> must also transliterate accented letters to ASCII.</li>
          </ul>
          <span class="tag block">conformance target</span>
        `,
        code: `# Issue — SLUGIFY-03

slugify() must turn a title into a URL slug, INCLUDING transliterating
accented / Unicode letters to ASCII.

Required:
  - lowercase
  - spaces -> a single hyphen
  - accented letters -> ASCII equivalent

Examples:
  "Hello World"  -> "hello-world"
  "Café Münchén" -> "cafe-munchen"`
      },
      accept_test: {
        type: "acceptance_test.py",
        title: "Acceptance Test (fix-blind)",
        copy: `
          <p>Authored from the requirement only, it encodes <strong>both</strong> stated examples — including the accented one the agent will overlook.</p>
        `,
        code: `# acceptance_test.py
# Authored from the requirement only, including the accented example.
from slugs import slugify

def test_ascii_title():
    assert slugify("Hello World") == "hello-world"

def test_accented_title():
    assert slugify("Café Münchén") == "cafe-munchen"`
      },
      change: {
        type: "agent_self_test.py",
        title: "Agent Change + its own test",
        copy: `
          <p>The agent lowercases and hyphenates, then writes a self-test for <strong>only the easy case</strong>. That test is green — and a self-graded pipeline would ship this.</p>
          <ul>
            <li>The self-test never exercises an accented title.</li>
            <li>Green ≠ correct. This is exactly the trap.</li>
          </ul>
        `,
        code: `# test added by the agent (self-referential)
def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"   # passes`
      },
      diff: {
        type: "change.diff",
        title: "Diff",
        copy: `
          <p>The proposed change handles spacing and case — but never transliterates accented characters.</p>
        `,
        code: `--- a/slugs.py
+++ b/slugs.py
@@
-def slugify(title: str) -> str:
-    return title
+def slugify(title: str) -> str:
+    return title.strip().lower().replace(" ", "-")`
      },
      verify: {
        type: "verification.log",
        title: "Independent Verification",
        copy: `
          <p>The agent's own test passes. The <strong>fix-blind</strong> acceptance test does not: the accented case fails. The confident-but-wrong change is caught by evidence the agent did not author.</p>
        `,
        code: `=== Independent verification ===

Agent's own test (informational only — self-referential):
  test_slugify_basic ........... PASSED      <-- green, but proves nothing

Fix-blind acceptance test (decisive):
  test_ascii_title ............. PASSED
  test_accented_title .......... FAILED
      expected: "cafe-munchen"
      actual:   "café-münchén"

Regression check:
  12 / 12 previously-passing tests still pass

Leak-safety: the hidden reference oracle was not run or inspected.`
      },
      verdict: {
        type: "verdict.json",
        title: "Verdict",
        copy: `
          <p>A self-graded loop would have admitted this on a green self-test. Independent verification rejects it: it does not meet the stated requirement.</p>
          <span class="tag block">reject</span>
        `,
        code: `{
  "verdict": "reject",
  "basis": "independent",
  "agent_self_test": "passed (not used as the deciding signal)",
  "acceptance_test_fix_blind": "1/2 passed — accented case fails",
  "regression_check": "clean",
  "conforms_to_requirement": false,
  "reason": "The change handles only the case the agent tested. Its self-authored test was green, but the fix-blind acceptance test shows it does not transliterate accented characters as required. Confidently wrong, caught independently."
}`
      },
      trace: {
        type: "evidence_trace.md",
        title: "Evidence Trace",
        copy: `
          <p>The trace makes the gap explicit: the agent's green self-test next to the failing independent test. That contrast is the thesis in one screen.</p>
        `,
        code: `# Evidence Trace — SLUGIFY-03

requirement.md       lowercase + hyphenate + transliterate accents
acceptance_test.py   both examples, including the accented one
agent_self_test.py   only the easy ASCII case (green)
verification.log     acceptance 1/2 — accented case FAILED
verdict.json         reject (independent)

Reproducible: same evidence -> same verdict.`
      },
      decision: {
        type: "decision.md",
        title: "Decision",
        copy: `
          <p>Not admitted. The change goes back to the agent against the failing requirement — not waved through with a waiver.</p>
        `,
        code: `# Decision — SLUGIFY-03

Verdict: REJECT

The agent's own test passed, so a self-graded pipeline would have shipped this.
Independent verification shows the change does not meet the stated requirement
(accented characters are not transliterated). Not admitted.

Next step: return to the agent with the failing requirement, not a waiver.`
      }
    }
  }
};

let activeScenario = "accept";
let activeStep = "requirement";
let checkWasRun = false;

const statusEl = document.getElementById("scenarioStatus");
const artifactTypeEl = document.getElementById("artifactType");
const artifactTitleEl = document.getElementById("artifactTitle");
const artifactCopyEl = document.getElementById("artifactCopy");
const artifactCodeEl = document.getElementById("artifactCode");
const flowStripEl = document.getElementById("flowStrip");
const bundleListEl = document.getElementById("bundleList");
const runCheckButton = document.getElementById("runCheckButton");

function renderFlow() {
  flowStripEl.innerHTML = flowNodes.map(([id, title, meta]) => `
    <button class="flow-node ${id === activeStep ? "active" : ""}" data-step="${id}" type="button">
      <strong>${title}</strong>
      <span>${meta}</span>
    </button>
  `).join("");
}

function renderBundle() {
  bundleListEl.innerHTML = bundleFiles.map((file) => {
    const current = scenarios[activeScenario].artifacts[activeStep].type === file;
    return `<li class="${current ? "current" : ""}">${file}</li>`;
  }).join("");
}

function renderMetrics() {
  const scenario = scenarios[activeScenario];
  document.getElementById("selfTestMetric").textContent = scenario.metrics.selfTest;
  document.getElementById("acceptTestMetric").textContent = scenario.metrics.acceptTest;
  document.getElementById("regressionMetric").textContent = scenario.metrics.regression;
  document.getElementById("actionMetric").textContent = scenario.metrics.action;
}

function renderStatus() {
  const scenario = scenarios[activeScenario];
  statusEl.dataset.state = scenario.state;
  statusEl.innerHTML = `
    <span class="status-label">Verdict</span>
    <strong>${scenario.verdict}</strong>
    <span>${scenario.statusText}</span>
  `;
  document.getElementById("realCaseLine").innerHTML = scenario.realCase;
}

function renderArtifact() {
  const artifact = scenarios[activeScenario].artifacts[activeStep];
  artifactTypeEl.textContent = artifact.type;
  artifactTitleEl.textContent = artifact.title;
  artifactCopyEl.innerHTML = artifact.copy;
  artifactCodeEl.textContent = artifact.code;
}

function renderButtons() {
  document.querySelectorAll(".scenario-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.scenario === activeScenario);
  });
  document.querySelectorAll(".step-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.step === activeStep);
  });
}

function render() {
  renderStatus();
  renderMetrics();
  renderFlow();
  renderBundle();
  renderArtifact();
  renderButtons();
  runCheckButton.textContent = checkWasRun ? "Verification Complete" : "Run Independent Verification";
}

document.querySelectorAll(".scenario-button").forEach((button) => {
  button.addEventListener("click", () => {
    activeScenario = button.dataset.scenario;
    activeStep = "requirement";
    checkWasRun = false;
    render();
  });
});

document.getElementById("stepList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-step]");
  if (!button) return;
  activeStep = button.dataset.step;
  render();
});

flowStripEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-step]");
  if (!button) return;
  activeStep = button.dataset.step;
  render();
});

runCheckButton.addEventListener("click", () => {
  checkWasRun = true;
  activeStep = "verify";
  render();
});

document.getElementById("bundleButton").addEventListener("click", () => {
  activeStep = "trace";
  render();
});

render();
