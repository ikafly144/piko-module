# Twitter Piko Magisk / KernelSU Module

[![CI](https://github.com/ikafly144/piko-module/actions/workflows/ci.yml/badge.svg)](https://github.com/ikafly144/piko-module/actions/workflows/ci.yml)

Automated builder for [Twitter Piko](https://github.com/crimera/piko) Magisk & KernelSU modules.

Get the latest build from [Releases](../../releases).

## Features
- Builds root modules for Twitter patched with [crimera/piko](https://github.com/crimera/piko) and [crimera/piko-newx](https://github.com/crimera/piko-newx)
- Includes classic Twitter branding restoration (blue bird logo and name)
- Automatically tracks and builds against the latest compatible version
- Automatic daily update checks via GitHub Actions (only builds and releases updated variants)
- Supports Magisk, KernelSU, and APatch module update channel

## Manual Build Options

You can trigger a build from the GitHub Actions tab (`Build Modules` workflow) with custom options:
- **`target`**: Choose which variant to build (`all`, `piko`, or `piko-newx`).
- **`twitter_version`**: Specify a target Twitter APK version (e.g. `auto`, `12.19.1-release.0`, `12.25.0-prod.01`).
- **`patches_version`**: Specify a target patch release tag (e.g. `latest`, `v3.9.0`, `v3.19.1`).
- **`included_patches`**: Specify custom patch names to include (e.g. `'Bring back twitter'`).
- **`force_all`**: Force build regardless of update checks.



