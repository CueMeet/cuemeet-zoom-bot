# Upgrade

All instructions to upgrade this project from one release to the next will be
documented in this file. Upgrades must be run sequentially, meaning you should
not skip minor/major releases while upgrading (fix releases can be skipped).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- AI features are now limited to users who are authenticated. Before this release, even anonymous
  users who gained editor access on a document with link reach used to get AI feature.
  IF you want anonymous users to keep access on AI features, you must now define the
  `AI_ALLOW_REACH_FROM` setting to "public".
