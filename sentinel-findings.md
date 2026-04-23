# sentinel-findings.md

*Written by Sentinel — WARN-tier findings.*

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-15T15:47:49.916628+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-15T15:47:49.992423+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-15T15:47:58.263365+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-15T15:47:58.323407+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:13:17.881984+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:13:18.085837+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:13:18.560960+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:13:18.620031+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:13:53.175973+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:13:53.242039+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:13:53.888020+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:13:53.964746+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:14:34.398249+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:14:34.723051+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:14:34.937188+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:14:35.158121+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:69`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:15:16.196777+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:158`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T11:15:16.642467+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:15:17.512824+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T11:15:17.654712+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T15:50:38.871335+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T15:50:39.242591+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T15:50:40.100114+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T15:50:40.430805+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T15:50:42.297812+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T15:50:42.297812+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T15:50:42.297812+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T15:50:42.297812+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T15:50:42.297812+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T17:44:55.740413+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-21T17:44:55.791913+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T17:44:56.252671+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-21T17:44:56.275922+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T17:44:57.567875+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T17:44:57.567875+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T17:44:57.567875+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T17:44:57.567875+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-21T17:44:57.567875+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T13:08:59.109878+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T13:08:59.431194+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T13:08:59.759813+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T13:08:59.786826+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T13:09:01.067493+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T13:09:01.067493+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T13:09:01.067493+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T13:09:01.067493+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T13:09:01.067493+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T15:48:03.536439+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T15:48:03.769803+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T15:48:05.189666+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T15:48:05.591598+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T15:48:09.292457+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T15:48:09.292457+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T15:48:09.292457+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T15:48:09.292457+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T15:48:09.292457+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T16:11:08.872047+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T16:11:08.882522+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T16:11:09.595869+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T16:11:09.798191+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:11:12.146067+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:11:12.146067+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:11:12.146067+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:11:12.146067+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:11:12.146067+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_gold_standard.py:163`
- **Detail:** pattern matched: row = df[df[study_col] == study_name].iloc[0]
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T16:13:26.830003+00:00

## [WARN] P1-empty-dataframe-access
- **Location:** `scripts/build_mega_gold.py:74`
- **Detail:** pattern matched: review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
- **Fix hint:** Guard with `if df.empty: return <sentinel>` or `if len(df) == 0: ...` immediately before the positional access, OR use `.iat[0]` / `.at[...]` with a prior existence check. If the file is a generator where this access is provably safe repo-wide, add `# sentinel:skip-file` near the top of the file.

- **Source:** MEMORY.md#top-5-cross-project-defects
- **When:** 2026-04-23T16:13:26.954334+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/diagnose_external_no_tune_no_match.py:223`
- **Detail:** pattern matched: return "unknown_no_expected_candidate"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T16:13:27.588724+00:00

## [WARN] P1-silent-failure-sentinel
- **Location:** `scripts/analyze_residual_extracted_no_match.py:128`
- **Detail:** pattern matched: return "unknown_type_and_no_raw_data"
- **Fix hint:** Raise KeyError or a domain-specific exception instead of returning a sentinel string. Include expected-vs-received schema in the exception message.

- **Source:** lessons.md#integration-contracts-learned-2026-04-14
- **When:** 2026-04-23T16:13:27.857167+00:00

## [WARN] P2-autogen-tracked
- **Location:** `DECISIONS.md`
- **Detail:** DECISIONS.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached DECISIONS.md` + append `DECISIONS.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:13:29.612413+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.jsonl`
- **Detail:** STUCK_FAILURES.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.jsonl` + append `STUCK_FAILURES.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:13:29.612413+00:00

## [WARN] P2-autogen-tracked
- **Location:** `STUCK_FAILURES.md`
- **Detail:** STUCK_FAILURES.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached STUCK_FAILURES.md` + append `STUCK_FAILURES.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:13:29.612413+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.jsonl`
- **Detail:** sentinel-findings.jsonl is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.jsonl` + append `sentinel-findings.jsonl` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:13:29.612413+00:00

## [WARN] P2-autogen-tracked
- **Location:** `sentinel-findings.md`
- **Detail:** sentinel-findings.md is auto-generated but tracked in git
- **Fix hint:** `git rm --cached sentinel-findings.md` + append `sentinel-findings.md` to .gitignore
- **Source:** lessons.md#portfolio-audit-patterns
- **When:** 2026-04-23T16:13:29.612413+00:00
