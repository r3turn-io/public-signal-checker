# R3TURN Public Signal Checker

A lightweight utility for inspecting selected public, machine-readable signals exposed by a website.

> **This is not a R3TURN Brand Intelligence report.**
>
> Public Signal Checker performs limited factual inspection only. It does not reproduce R3TURN's proprietary scoring, diagnostic, interpretation or commercial intelligence methodology.

## Purpose

Public websites expose signals that search engines, AI systems, directories and other machines may use when interpreting an organization.

Public Signal Checker provides a small, deterministic inspection layer for selected signals that can be observed directly from a public URL.

The project is designed as a public technical utility and evidence artifact from [R3TURN](https://www.r3turn.io).

## v0.1 Scope

Given a public URL, the checker may inspect:

* HTTP accessibility
* final URL and redirects
* canonical URL
* page title
* meta description
* `robots.txt`
* sitemap discovery
* Organization JSON-LD
* `sameAs` references
* `hreflang`
* selected basic machine-readable identity signals

Results are observations about what was detected or not detected at inspection time.

## What this project does not do

Public Signal Checker does **not**:

* produce a Brand Intelligence score
* calculate a Digital Reflection Gap score
* rank or grade companies
* perform Growth Engine analysis
* discover or verify buyers
* generate commercial recommendations
* reproduce proprietary R3TURN methodology
* use private R3TURN scoring weights
* access private R3TURN repositories
* process customer data
* claim that absence of a signal proves absence of a real-world capability

## Core principle

**Observation is not interpretation.**

For example:

```text
Organization JSON-LD detected: YES
```

is an observable result.

A conclusion such as:

```text
Your company has weak entity visibility.
```

requires broader evidence and interpretation and is therefore outside the scope of this utility.

## Output

The initial version is intended to provide:

* human-readable inspection results
* structured JSON output

The same observed signal should produce the same interpretation-free result under equivalent inspection conditions.

## Public / private boundary

This repository may contain:

* public inspection logic
* public schemas
* documentation
* tests
* safe example outputs

This repository will not contain:

* R3TURN proprietary engines
* Brand Intelligence scoring logic
* Growth Engine logic
* proprietary weights
* private collectors
* customer evidence
* internal prompts
* private operational workflows
* commercially sensitive inference logic

## Status

**v0.1 — private development / pre-release**

The repository will remain private until its scope, security behavior, tests and public IP boundary have been reviewed.

## R3TURN

R3TURN is the operating and public brand of **RETURN Teknoloji ve Dış Ticaret Ltd. Şti.**

R3TURN operates through two primary intelligence products:

* [Brand Intelligence](https://www.r3turn.io/en/brand-intelligence)
* [Growth Engine](https://www.r3turn.io/en/growth-engine)

**Evidence Before Output.**

Website: https://www.r3turn.io
Contact: [info@r3turn.io](mailto:info@r3turn.io)

