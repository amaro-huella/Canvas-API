# Canva Connect APIs

How to integrate into Canva using our REST API.

The Canva Connect APIs let you integrate Canva's capabilities into your own web apps and platforms.

You can use the Connect APIs to create web app integrations that create and sync assets, designs, comments, and more. You can also collaborate and communicate with different platforms, or embed Canva into project management workflows.

For example, you could use the Connect APIs to create an integration between Canva and your digital asset management system. With an integration you can upload your assets to Canva, programmatically create designs for your users to edit, and then export the finished designs back to your system.

## Public vs. private integrations

An integration that uses the Connect APIs can be _public_ (available to all Canva users), or _private_ (available only to your team on a [Canva Enterprise](https://www.canva.com/enterprise/) plan).

Public integrations must first be reviewed by Canva and meet the [integration requirements](https://www.canva.dev/docs/connect/submission-checklist) before they can be made available to all Canva users.

## First steps

- Follow the [Quickstart](https://www.canva.dev/docs/connect/quickstart) to get started with a Canva-created app that demonstrates some of the main API features. It's also a great template for creating an integration.
- [Create a new integration](https://www.canva.dev/docs/connect/creating-integrations) from scratch.

## Connect APIs Starter Kit

Canva has created a [Starter Kit repository](https://github.com/canva-sdks/canva-connect-api-starter-kit) that includes an example web app which demonstrates some of the Connect APIs' main features. The [Quickstart](https://www.canva.dev/docs/connect/quickstart) walks you through installing and running the example app.

## OpenAPI description

Canva provides an OpenAPI description of the Connect APIs. You can use this with code generation libraries, such as [openapi-generator](https://github.com/OpenAPITools/openapi-generator), to generate client SDKs in various languages. The OpenAPI description is publicly available at [https://www.canva.dev/sources/connect/api/latest/api.yml](https://www.canva.dev/sources/connect/api/latest/api.yml).

## Preview APIs

Some APIs and features have notices declaring they're provided as a preview. Although you can use these APIs for development and experimentation, they are not finalized and we don't recommend them for use in production environments.

Specifically, you should be aware of the following for preview APIs and features:

- There might be unannounced breaking changes.
- Any breaking changes to preview APIs won't produce a new [API version](https://www.canva.dev/docs/connect/versions).
- Public integrations that use preview APIs or features will not pass the review process, and can't be made available to all Canva users.

## Want to add features to Canva?

In addition to the Connect APIs, Canva also offers the Apps SDK, which lets developers create plugins that enhance a user's experience when designing in Canva. If you're interested, [check out the documentation](https://www.canva.dev/docs/apps).
