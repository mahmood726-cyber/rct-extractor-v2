# RCT Extractor Maintenance Roadmap
## Long-Term Support and Development Plan

**Version:** 1.0
**Date:** 2026-01-31
**Status:** Active Development

---

## 1. Version Policy

### 1.1 Semantic Versioning

RCT Extractor follows [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH (e.g., 4.0.6)
```

| Version Component | When to Increment | Example |
|-------------------|-------------------|---------|
| **MAJOR** | Breaking API changes, major architecture overhaul | 4.x → 5.0 |
| **MINOR** | New features, pattern additions, non-breaking improvements | 4.0 → 4.1 |
| **PATCH** | Bug fixes, pattern corrections, documentation updates | 4.0.5 → 4.0.6 |

### 1.2 Current Version: 4.0.6

**Release Date:** 2026-01-31
**Status:** Stable, Production-Ready
**Next Planned:** 4.1.0 (Q2 2026)

---

## 2. Release Schedule

### 2.1 Release Cadence

| Release Type | Frequency | Contents |
|--------------|-----------|----------|
| Patch (4.0.x) | As needed | Bug fixes, urgent pattern fixes |
| Minor (4.x.0) | Quarterly | New patterns, features, validation updates |
| Major (x.0.0) | Annually | Breaking changes, major overhauls |

### 2.2 Planned Releases

| Version | Target Date | Key Features |
|---------|-------------|--------------|
| 4.0.7 | 2026-02 | Bug fixes from community feedback |
| 4.1.0 | 2026-04 | Multi-language expansion (German, French) |
| 4.2.0 | 2026-07 | Enhanced table extraction |
| 4.3.0 | 2026-10 | Forest plot recognition improvements |
| 5.0.0 | 2027-01 | ML hybrid extraction, API v2 |

---

## 3. Quarterly Validation Protocol

### 3.1 Schedule

| Quarter | Month | Activity |
|---------|-------|----------|
| Q1 | January | Full validation suite, annual report |
| Q2 | April | Pattern performance review |
| Q3 | July | Mid-year validation check |
| Q4 | October | Pre-release validation for next major |

### 3.2 Validation Procedure

1. **Literature Sampling**
   - Sample 20 new publications from major journals
   - Include at least 2 from each major therapeutic area
   - Prioritize novel effect reporting formats

2. **Pattern Testing**
   - Run all 82 regulatory tests
   - Execute stratified validation (100+ trials)
   - Test against new publications

3. **Performance Analysis**
   - Calculate sensitivity on new papers
   - Update calibration curves
   - Document any pattern failures

4. **Remediation**
   - Add patterns for failed extractions
   - Update confidence thresholds if needed
   - Release patch version

### 3.3 Quarterly Report Template

```markdown
# RCT Extractor Quarterly Validation Report
## Q[X] 2026

### Summary
- Papers tested: [n]
- New patterns added: [n]
- Sensitivity: [%]
- Issues identified: [n]

### Pattern Updates
[List new patterns]

### Known Limitations
[Document any persistent issues]

### Next Quarter Focus
[Priorities for next quarter]
```

---

## 4. Deprecation Policy

### 4.1 Deprecation Timeline

| Phase | Duration | Actions |
|-------|----------|---------|
| **Announcement** | 0 months | Deprecation notice in release notes |
| **Warning Period** | 6 months | Runtime warnings, documentation updates |
| **Migration Period** | 6 months | Both old and new APIs available |
| **Removal** | 12+ months | Old API/feature removed |

### 4.2 Current Deprecations

| Feature | Deprecated | Removal Target | Replacement |
|---------|------------|----------------|-------------|
| `extract_v2()` | v4.0.0 | v5.0.0 | `extract()` |
| `legacy_patterns` | v4.0.0 | v5.0.0 | `enhanced_patterns` |

### 4.3 Migration Guides

For each deprecation, a migration guide will be provided in `docs/migration/`.

---

## 5. Support Policy

### 5.1 Version Support Matrix

| Version | Status | Security Fixes | Bug Fixes | New Features |
|---------|--------|----------------|-----------|--------------|
| 4.0.x | Active | Yes | Yes | No |
| 3.x.x | Maintenance | Yes | Critical only | No |
| 2.x.x | EOL | No | No | No |
| 1.x.x | EOL | No | No | No |

### 5.2 Support Channels

| Channel | Response Time | Use For |
|---------|---------------|---------|
| GitHub Issues | 48-72 hours | Bug reports, feature requests |
| GitHub Discussions | 1 week | Questions, community support |
| Email (critical) | 24 hours | Security vulnerabilities |

### 5.3 End of Life (EOL) Policy

- Major versions supported for **2 years** after next major release
- Security patches for **1 year** after EOL
- No new development after EOL

---

## 6. Pattern Contribution Process

### 6.1 Submitting New Patterns

1. **Open Issue**
   - Title: `[Pattern Request] Description`
   - Include: Source text, expected extraction, journal source

2. **Pattern Development**
   - Fork repository
   - Add pattern to appropriate file
   - Add test case to validation set

3. **Pull Request**
   - Reference issue number
   - Include test coverage
   - Document pattern rationale

4. **Review Process**
   - Automated tests must pass
   - Pattern reviewed for specificity/generality balance
   - Negative testing for false positives

5. **Merge and Release**
   - Merged to `main` branch
   - Included in next patch/minor release

### 6.2 Pattern Quality Criteria

| Criterion | Requirement |
|-----------|-------------|
| Specificity | Must not increase false positive rate |
| Coverage | Should match ≥3 known examples |
| Complexity | Prefer simpler patterns |
| Documentation | Include example text in comment |

---

## 7. Breaking Change Policy

### 7.1 Definition

A breaking change is any modification that:
- Changes the output format of `extract()`
- Removes a previously available function
- Changes default behavior
- Requires code changes for existing users

### 7.2 Breaking Change Procedure

1. **RFC (Request for Comments)**
   - Document proposed change
   - Gather community feedback (30 days)

2. **Implementation**
   - Implement behind feature flag
   - Maintain backwards compatibility

3. **Deprecation**
   - Mark old behavior as deprecated
   - Add migration documentation

4. **Release**
   - Include in next major version
   - Highlighted in release notes

---

## 8. Security Policy

### 8.1 Reporting Vulnerabilities

**Email:** security@example.com (hypothetical)
**PGP Key:** Available in `SECURITY.md`

### 8.2 Vulnerability Response

| Severity | Response Time | Disclosure |
|----------|---------------|------------|
| Critical | 24 hours | After fix available |
| High | 72 hours | After fix available |
| Medium | 1 week | With next release |
| Low | 2 weeks | With next release |

### 8.3 Security Considerations

- No network access required (offline operation)
- No user data storage
- Input validation for PDF paths
- Sandboxed PDF processing recommended

---

## 9. Performance Monitoring

### 9.1 Metrics Tracked

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Sensitivity | >95% | <90% |
| False Positive Rate | 0% | >1% |
| ECE | <0.10 | >0.15 |
| Processing Speed | <100ms/doc | >500ms/doc |

### 9.2 Monitoring Tools

- Quarterly validation reports
- GitHub Actions CI/CD metrics
- Community-reported issues tracking

---

## 10. Roadmap Summary

### 2026 Priorities

1. **Q1:** Consolidate validation, publish methodology paper
2. **Q2:** Multi-language support (German, French)
3. **Q3:** Enhanced table extraction module
4. **Q4:** ML hybrid approach research

### 2027 Vision

- Version 5.0 with ML integration
- Real-time extraction API
- Integration with systematic review tools
- Extended effect type coverage

---

## 11. Contact

**Maintainers:** RCT Extractor Core Team
**Repository:** https://github.com/xxx/rct-extractor
**Documentation:** https://rct-extractor.readthedocs.io

---

*This roadmap is subject to change based on community feedback and research priorities.*
