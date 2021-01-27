# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.10.0]

Released for version consistency with other DSW tools.

## [2.9.0]

Released for version consistency with other DSW tools.

## [2.8.1]

### Changed

- Fix matching template files that have relative path to template dir
- Fix starter Jinja template file (questionnaireReplies)
- Add LICENSE to Python package

## [2.8.0]

Initial DSW Template Development Kit (versioned as part of the [DSW platform](https://github.com/ds-wizard))

### Added

- `new` for initializing new template project
- `list` for listing remote templates
- `get` for retrieving remote template and storing it locally
- `put` for uploading local template project to DSW instance including `watch` functionality for smooth template development
- `verify` for checking template metadata
- `package` for creating an importable ZIP package from local project

[Unreleased]: /../../compare/master...develop
[2.8.0]: /../../tree/v2.8.0
[2.8.1]: /../../tree/v2.8.1
[2.9.0]: /../../tree/v2.9.0
[2.10.0]: /../../tree/v2.10.0
