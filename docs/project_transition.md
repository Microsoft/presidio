# Presidio has transitioned to a community-owned project

We want to share an important update regarding the future of Presidio.

The Presidio project has completed its transition from a Microsoft-owned project to an independent, community-governed open source project under the GitHub organization Data Privacy Stack. Its official URL is: <https://github.com/data-privacy-stack/presidio>

Microsoft supported this transition and the continued success of the Presidio project as an open source community initiative.

Our goal remains to ensure Presidio serves the privacy engineering and data protection community as an open, transparent, and vendor-neutral project.

## What this means

* Presidio continues to be open source under the MIT license.
* Existing functionality, APIs, and documentation remain available.
* The project is maintained by contributors and volunteers from the community.
* The project is not owned or operated by a commercial entity.
* The focus on privacy, responsible AI, and data protection tooling remains unchanged.

## Microsoft and Azure users

This transition does not change the experience for users of Presidio, including organizations using Presidio alongside Microsoft and Azure services.

Integrations, dependencies, and usage patterns continue to work as expected.

## Why this change

Over the years, Presidio has grown beyond its original scope and has been adopted by organizations, researchers, and developers across industries. Moving to an independent community initiative positions the project for long-term sustainability, broader collaboration, and open governance.

## What to expect next
Now that the migration is complete:

* Repositories, documentation links, and package references have moved to the new organization. Please update your references.
* Legacy GitHub URLs and documentation links redirect to the new location.
* New Docker image releases are published to [GitHub Container Registry](https://github.com/orgs/data-privacy-stack/packages) under the Data Privacy Stack organization. Legacy Microsoft Container Registry (MCR) images remain available for older tags but are no longer updated; update `mcr.microsoft.com/presidio-*` image references to `ghcr.io/data-privacy-stack/presidio-*`.
* Contribution and governance processes are now community-driven.
* The Technical Steering Committee (TSC) includes maintainers and contributors from across the community.

## Maintainers and contributors

Maintainers and contributors continue to actively drive the project. We welcome new contributors who care about privacy-preserving technologies and responsible data handling.

Details regarding contribution guidelines and Docker image publishing are available in the repository documentation.

Thank you to everyone who supported Presidio through this transition and helped make it a valuable resource for the privacy engineering community.
