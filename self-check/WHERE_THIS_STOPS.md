# Where this tool stops — on purpose

fa-patchward measures a **problem**. It does not sell you the cure, and it is
built so it *can't* accidentally become the cure. Four hard lines:

## 1. It measures. It does not decide.

fa-patchward reports one number: how many fixes your agent ships silently that turn
out wrong. That is the **ungated** number — what leaves when nothing checks the
agent. It never blocks, gates, verifies, or vouches for a patch. Deciding whether
a specific incoming patch is safe to ship is a different job — an independent
verdict layer — and it is deliberately **not** in this tool.

## 2. Ground truth is the benchmark's own tests — never a synthesized oracle.

Correctness here is judged **only** by the hidden reference tests that public
benchmarks (SWE-bench and friends) already ship with each task. fa-patchward reads
the public harness's `resolved` flag and takes it as truth. It **never**
synthesizes an acceptance test, and it never judges a fix by reasoning about the
fix. Judging correctness where no reference test exists — authoring a check blind
to the proposed change — is precisely the hard part, and it is not here.

## 3. Public-benchmark tasks only — because a *rate* needs an oracle.

fa-patchward runs strictly against public benchmarks that ship ground-truth tests.
There is intentionally **no** private-repo mode *for this measurement*. Your
private code has no reference tests, so computing a false-accept rate on it would
force the tool to synthesize an oracle blind to the fix — which is line 2, which
is the cure, which isn't this.

Note what that reasoning does and does not forbid. It rules out measuring
*correctness* without an oracle. It does not rule out reporting facts about a
change that need no oracle at all. [`../check/`](../check/) does exactly that: it
reads a diff and reports whether the change edited the tests that judge it — a
structural property of the diff, not a verdict on the code. That runs on any
repository, private or not, and it is free, MIT, and installable today.

So the honest line is narrower than "no private-repo mode": **anything requiring
an oracle needs a benchmark; anything that needs no oracle is yours to run.**

## 4. It produces the diagnosis, not the treatment plan.

You run it, you see your own scary number, and now you know what silently ships.
What to do about it — an independent, deterministic verdict layer that turns an
unaccountable patch into one that carries a verdict — is separate work, kept
private by design. The reasoning behind *why* an independent verdict beats an
agent grading its own homework is public and abstracted in the
[Verdict Layer Framework](https://github.com/kolesnikov-arch/verdict-layer-framework);
the tuned engine that implements it is not.

---

**In one line:** fa-patchward is a ruler, not a gate. It shows you how much leaks.
Stopping the leak is a different tool, available by conversation.

**And one thing that is not behind a conversation:** [`../check/`](../check/) —
`pip install patchward-check`. It flags changes that rewrite the tests judging them.
Free, MIT, offline, runs on your own repository, no oracle required.
