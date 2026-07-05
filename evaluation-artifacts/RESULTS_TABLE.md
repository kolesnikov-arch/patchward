# Per-instance paired results — held-out 50

Both arms, same task, same underlying model. `gated_patch_resolves` / `ungated_resolves` = the hidden reference tests' gold verdict on that arm's patch (from `reports/`).

| # | instance | gated verdict | gated patch resolves | gated outcome | ungated resolves | ungated outcome |
|---|---|---|---|---|---|---|
| 1 | django__django-11001 | Needs review | yes | needs review correct | yes | shipped correct |
| 2 | django__django-12184 | Needs review | yes | needs review correct | no | silent false accept |
| 3 | django__django-12286 | Needs review | yes | needs review correct | yes | shipped correct |
| 4 | django__django-12700 | Needs review | yes | needs review correct | yes | shipped correct |
| 5 | django__django-12708 | Blocked | yes | false reject | yes | shipped correct |
| 6 | django__django-12856 | Needs review | yes | needs review correct | yes | shipped correct |
| 7 | django__django-12915 | Blocked | yes | false reject | yes | shipped correct |
| 8 | django__django-13158 | Needs review | yes | needs review correct | yes | shipped correct |
| 9 | django__django-13265 | Needs review | no | needs review wrong | no | silent false accept |
| 10 | django__django-13315 | Needs review | yes | needs review correct | yes | shipped correct |
| 11 | django__django-13321 | Needs review | no | needs review wrong | no | silent false accept |
| 12 | django__django-13925 | Needs review | yes | needs review correct | yes | shipped correct |
| 13 | django__django-14730 | Needs review | no | needs review wrong | no | silent false accept |
| 14 | django__django-14855 | Needs review | yes | needs review correct | yes | shipped correct |
| 15 | django__django-14997 | Needs review | no | needs review wrong | yes | shipped correct |
| 16 | django__django-15202 | Needs review | no | needs review wrong | no | silent false accept |
| 17 | django__django-15213 | Needs review | yes | needs review correct | yes | shipped correct |
| 18 | django__django-15252 | Needs review | no | needs review wrong | no | silent false accept |
| 19 | django__django-15738 | Needs review | yes | needs review correct | no | silent false accept |
| 20 | django__django-16041 | Needs review | yes | needs review correct | yes | shipped correct |
| 21 | django__django-16046 | Needs review | yes | needs review correct | yes | shipped correct |
| 22 | django__django-16527 | Blocked | yes | false reject | yes | shipped correct |
| 23 | django__django-17087 | Blocked | yes | false reject | yes | shipped correct |
| 24 | pylint-dev__pylint-5859 | Needs review | yes | needs review correct | yes | shipped correct |
| 25 | pylint-dev__pylint-7993 | Blocked | no | correct block | yes | shipped correct |
| 26 | sphinx-doc__sphinx-10325 | Needs review | yes | needs review correct | yes | shipped correct |
| 27 | sphinx-doc__sphinx-7738 | Needs review | no | needs review wrong | no | silent false accept |
| 28 | sphinx-doc__sphinx-8282 | Blocked | no | correct block | no | silent false accept |
| 29 | sphinx-doc__sphinx-8435 | Needs review | yes | needs review correct | yes | shipped correct |
| 30 | sphinx-doc__sphinx-8595 | Needs review | no | needs review wrong | no | silent false accept |
| 31 | sphinx-doc__sphinx-8801 | Blocked | no | correct block | yes | shipped correct |
| 32 | sympy__sympy-12454 | Needs review | no | needs review wrong | yes | shipped correct |
| 33 | sympy__sympy-13471 | Needs review | yes | needs review correct | yes | shipped correct |
| 34 | sympy__sympy-13971 | Blocked | yes | false reject | yes | shipped correct |
| 35 | sympy__sympy-14024 | Needs review | no | needs review wrong | no | silent false accept |
| 36 | sympy__sympy-15011 | Needs review | yes | needs review correct | yes | shipped correct |
| 37 | sympy__sympy-15346 | Needs review | yes | needs review correct | yes | shipped correct |
| 38 | sympy__sympy-15678 | Blocked | no | correct block | yes | shipped correct |
| 39 | sympy__sympy-16503 | Blocked | no | correct block | no | silent false accept |
| 40 | sympy__sympy-18621 | Needs review | yes | needs review correct | yes | shipped correct |
| 41 | sympy__sympy-20322 | Needs review | no | needs review wrong | no | silent false accept |
| 42 | sympy__sympy-21055 | Needs review | yes | needs review correct | yes | shipped correct |
| 43 | sympy__sympy-21614 | Needs review | yes | needs review correct | yes | shipped correct |
| 44 | sympy__sympy-22005 | Needs review | no | needs review wrong | yes | shipped correct |
| 45 | sympy__sympy-22840 | Blocked | no | correct block | no | silent false accept |
| 46 | sympy__sympy-24213 | Needs review | yes | needs review correct | yes | shipped correct |
| 47 | sympy__sympy-24909 | Needs review | no | needs review wrong | no | silent false accept |
| 48 | pydata__xarray-4094 | Needs review | yes | needs review correct | yes | shipped correct |
| 49 | pydata__xarray-4248 | Blocked | no | correct block | no | silent false accept |
| 50 | pydata__xarray-4493 | Needs review | no | needs review wrong | no | silent false accept |
