# Security Policy

## Project scope

R3TURN Public Signal Checker inspects selected signals exposed by publicly accessible websites.

Because the utility accepts URLs and may perform outbound network requests, network safety is part of the project's core security boundary.

## Supported versions

The project is currently in pre-release development.

Security support applies to the latest version available from the default branch or latest published release.

## Security principles

The implementation must follow these principles:

* treat all submitted URLs and remote responses as untrusted input
* permit only explicitly supported network schemes
* prevent access to localhost, loopback, private, link-local and otherwise restricted network ranges
* validate redirect destinations, not only the original URL
* apply request timeouts
* limit redirect depth
* limit response sizes where practical
* avoid executing remote JavaScript or arbitrary code
* never evaluate content retrieved from a target as executable application logic
* fail safely when a remote resource cannot be inspected
* avoid exposing internal network information through errors
* keep inspection deterministic and interpretation-free where possible

## SSRF protection

Server-Side Request Forgery is a primary threat for any implementation that accepts arbitrary URLs.

The checker must not intentionally permit requests to:

* localhost
* loopback addresses
* private network ranges
* link-local addresses
* cloud instance metadata endpoints
* internal hostnames
* unsupported URL schemes

Redirect chains must be revalidated before subsequent requests are made.

Protection must consider hostname resolution as well as literal IP-address input.

## Supported protocols

Initial public inspection should be restricted to:

```text
http
https
```

Other schemes are outside the v0.1 scope.

## Remote content

Remote pages, metadata, structured data, robots files and sitemaps must be treated as untrusted data.

Detection of a field does not imply that its contents are accurate, safe or independently verified.

## Secrets

This repository must not contain:

* API keys
* credentials
* private tokens
* customer secrets
* private repository credentials
* internal service endpoints
* proprietary R3TURN configuration
* production environment secrets

Secrets must never be committed to Git history.

## R3TURN private systems

This project must remain operationally independent from R3TURN's private Brand Intelligence, Growth Engine and other proprietary systems unless a future explicitly approved architecture introduces a reviewed interface.

Public Signal Checker must not require access to private R3TURN repositories to perform its public function.

## Dependency security

Dependencies should be kept minimal.

Before public release:

* dependency versions should be reviewed
* unnecessary packages should be removed
* tests should cover important network-validation behavior
* security-sensitive parsing and fetching behavior should be reviewed explicitly

## Reporting a vulnerability

Please report suspected security issues privately to:

**[info@r3turn.io](mailto:info@r3turn.io)**

Do not publish exploit details in a public GitHub issue before R3TURN has had a reasonable opportunity to investigate.

## v0.1 implementation notes

The current CLI applies the controls above as follows:

* schemes are restricted to `http` and `https`
* URLs with embedded credentials are rejected
* localhost, loopback, private, link-local, multicast, unspecified, reserved and other non-global IP addresses are rejected
* obviously internal hostnames (for example `localhost`, `*.local`, `*.internal`, `*.corp`) are rejected
* DNS resolution is performed before each request, including redirect hops, and every returned address is inspected
* redirects are followed manually with a depth limit; each destination is authorized before the next request
* connect, read, write and pool timeouts are set
* response bodies are capped
* `trust_env=False` is set so environment proxy settings are not used
* remote JavaScript is not executed and retrieved content is not evaluated
* CLI error messages do not include resolved IP addresses

## Known limitations

These controls reduce accidental requests to non-public destinations. They are not a complete SSRF guarantee:

* There is a time-of-check vs time-of-use window between DNS inspection and the subsequent TCP/TLS connection. This CLI does not pin the connection to the inspected addresses.
* The process uses the operator machine's resolver, routing and TLS stack.
* Hostname classification cannot enumerate every private naming convention.
* The tool is a local CLI, not a multi-tenant fetch service. Operators can still point it at destinations their own machine can reach if those destinations appear globally routable.

Do not describe this utility as providing complete SSRF prevention.

## No security guarantee

Public Signal Checker provides limited public-surface inspection.

Its findings are not a security audit, penetration test, vulnerability assessment or certification of the inspected website.
