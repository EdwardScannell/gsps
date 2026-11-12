# Security

GSPS reads local CSV, YAML and markdown files and writes new files. It makes no network
calls.

Design choices that matter for safety:

- Estimate methods are evaluated with a restricted AST walker: numbers, anchor IDs and
  `+ - * / **` only. Names, calls, attributes and subscripts are refused.
- YAML is loaded with `yaml.safe_load`.
- Files are created with exclusive create; existing files are never overwritten.
- Locators in token registries are regular expressions supplied by the library owner.
  Treat a token registry from an untrusted source as you would any untrusted regex.

To report a vulnerability, open a private security advisory on the repository rather than
a public issue.
