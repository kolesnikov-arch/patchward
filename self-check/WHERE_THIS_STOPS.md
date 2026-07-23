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

## 3. Public-benchmark tasks only. There is no "point it at my repo" mode.

fa-patchward runs strictly against public benchmarks that ship ground-truth tests.
There is intentionally **no** private-repo mode. Your private code has no
reference tests, so measuring it would force the tool to synthesize an oracle
blind to the fix — which is line 2, which is the cure, which isn't this. If you
want to know your false-accept rate on *your own* code, that is a conversation,
not a download.

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
