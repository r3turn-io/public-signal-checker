# R3TURN Public Boundary

## Purpose

This document defines the public/private boundary for **R3TURN Public Signal Checker**.

The repository exists to provide a small, genuine public technical utility without reproducing or exposing R3TURN's proprietary intelligence systems.

The governing principle is:

> **Evidence Before Output.**

Public availability does not imply that every R3TURN method, schema, signal, workflow or implementation is appropriate for public release.

---

## PUBLIC_SAFE

Material may enter this repository when it is independently appropriate for the utility and does not reveal proprietary R3TURN intelligence logic.

Examples include:

* generic public-web fetching logic
* canonical-link detection
* HTML title detection
* meta-description detection
* `robots.txt` discovery
* sitemap discovery
* `hreflang` detection
* public JSON-LD parsing
* Organization JSON-LD detection
* `sameAs` extraction
* generic HTTP redirect observations
* public CLI behavior
* public output schemas created specifically for this utility
* unit and integration tests using safe fixtures
* synthetic examples
* documentation
* security protections
* publicly documented web standards

Public-safe functionality should preferably be independently implemented for this repository.

---

## REVIEW_REQUIRED

The following material must not be added automatically.

It requires explicit review before public exposure:

* terminology derived from internal R3TURN methodology
* schemas resembling private Brand Intelligence artifacts
* anonymized real customer examples
* scoring-like outputs
* interpretation rules
* confidence models
* evidence classification logic
* adjudication concepts
* methodology version mappings
* internal taxonomies
* private-repository-derived code
* internal prompts
* datasets originating from R3TURN operations
* internal benchmark definitions
* functionality that begins to resemble diagnosis rather than observation

When uncertain, classify material as:

`REVIEW_REQUIRED`

not `PUBLIC_SAFE`.

---

## NEVER_PUBLIC

The following material must not enter this repository:

* proprietary Brand Intelligence engine code
* proprietary Growth Engine code
* private R3TURN OS / Office logic
* private Alpha application internals
* proprietary scoring weights
* deterministic commercial scoring logic
* private collectors
* customer data
* customer evidence
* buyer pipelines
* internal buyer-ranking logic
* proprietary market-ranking logic
* internal commercial inference logic
* private adjudication rules
* private prompts
* credentials
* tokens
* private API endpoints
* internal infrastructure details that create material security risk
* private repository history
* confidential commercial workflows
* anything copied from a private R3TURN repository merely because it would make the public project appear more sophisticated

---

## Functional boundary

Public Signal Checker may answer questions such as:

```text
Canonical URL detected: YES
Organization JSON-LD detected: NO
robots.txt reachable: YES
sameAs entries detected: 3
```

It must not independently transform these observations into proprietary R3TURN conclusions such as:

```text
Digital Reflection Gap Score: 64
Entity Confidence Score: 72
Brand Intelligence Grade: B
Commercial Readiness: LOW
```

The boundary is:

**observation → public utility**

**diagnosis / scoring / intelligence interpretation → proprietary R3TURN systems**

---

## Repository independence

Public Signal Checker should be independently buildable from its public repository.

It must not rely on cloning, importing or accessing private R3TURN repositories.

No private repository should be added as:

* a Git submodule
* a package dependency
* a build dependency
* a hidden runtime requirement
* a copied source-code origin

---

## Public release gate

Before changing this repository from private to public, verify that:

* no private R3TURN code is present
* no credentials or secrets are present in current files or Git history
* no proprietary scoring or interpretation logic is present
* documentation accurately describes actual functionality
* security-sensitive URL fetching has been reviewed
* tests cover the released behavior
* example outputs contain no customer information
* public claims do not exceed implemented functionality
* the README clearly states that this utility is not a Brand Intelligence report

If any requirement fails, the repository remains private.

---

## Default rule

When classification is uncertain:

> **Do not publish first and review later.**

Classify the material as `REVIEW_REQUIRED` and keep it private until reviewed.
