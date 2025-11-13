---
seo:
  title: Bugzilla MCP Server
  description: A Model Context Protocol server for secure interaction with Bugzilla bug tracking systems. Connect AI applications to Bugzilla with ease.
---

::u-page-hero
#title
Bugzilla MCP Server

#description
A secure Model Context Protocol (MCP) server that enables AI applications to interact with Bugzilla bug tracking systems through a controlled, authenticated interface.

#links
  :::u-button
  ---
  color: neutral
  size: xl
  to: /getting-started/introduction
  trailing-icon: i-lucide-arrow-right
  ---
  Get started
  :::

  :::u-button
  ---
  color: neutral
  icon: simple-icons-github
  size: xl
  to: https://github.com/your-org/bugzilla-mcp
  variant: outline
  ---
  View on GitHub
  :::
::

::u-page-section
#title
Powerful features for bug tracking

#features
  :::u-page-feature
  ---
  icon: i-lucide-bug
  ---
  #title
  Query [Bug Information]{.text-primary}
  
  #description
  Retrieve complete details about any bug by ID, including status, assignee, priority, and all metadata. Get full bug information with a single API call.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-search
  ---
  #title
  [Search Bugs]{.text-primary} with Quicksearch
  
  #description
  Use Bugzilla's powerful quicksearch syntax to find bugs. Search by product, component, status, assignee, and more. Built-in documentation access for learning the syntax.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-message-square
  ---
  #title
  [Manage Comments]{.text-primary}
  
  #description
  Add public or private comments to bugs. Retrieve comment history with optional private comment access. Full comment management capabilities.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-shield-check
  ---
  #title
  [Secure Access]{.text-primary}
  
  #description
  API key-based authentication through HTTP headers. Follow security best practices with minimal permissions. Never expose credentials in code.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-cloud
  ---
  #title
  [Hosted Server]{.text-primary}
  
  #description
  Use the production server at `https://bugzilla.fastmcp.app/mcp` with no local setup required. Or run locally for development and testing.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-plug
  ---
  #title
  [Easy Integration]{.text-primary}
  
  #description
  Works seamlessly with Claude Desktop, Cursor IDE, Visual Studio Code, and any MCP-compatible client. Simple JSON configuration.
  :::
::
