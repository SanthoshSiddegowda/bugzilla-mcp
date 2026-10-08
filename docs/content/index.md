---
seo:
  title: Bugzilla MCP Server
  description: An MCP server that lets Claude and other AI assistants search, read, triage and update Bugzilla bugs. Runs on your machine, read-only by default.
---

::u-page-hero
#title
Bugzilla MCP Server

#description
Let Claude and other AI assistants search, read, triage and update your Bugzilla bugs. Runs on your machine, read-only by default. Install with one click in Claude Desktop, or `uvx bugzilla-mcp` anywhere else.

#links
  :::u-button
  ---
  color: neutral
  size: xl
  to: /getting-started/installation
  trailing-icon: i-lucide-arrow-right
  ---
  Install
  :::

  :::u-button
  ---
  color: neutral
  icon: simple-icons-github
  size: xl
  to: https://github.com/SanthoshSiddegowda/bugzilla-mcp
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
  [Update and File Bugs]{.text-primary}
  
  #description
  Change status, resolution, assignee, CC and custom fields, file new bugs, and add public or private comments. Clients confirm before changes.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-paperclip
  ---
  #title
  Read [Attachments]{.text-primary}
  
  #description
  Screenshots come back as images the assistant can see; logs and patches as text. Attach logs or files straight from the conversation.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-shield-check
  ---
  #title
  [Secure Access]{.text-primary}
  
  #description
  Read-only by default, a dry run before bulk updates, and approval hints on every tool. Your API key stays in Claude Desktop's secure storage or your environment.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-laptop
  ---
  #title
  [Runs Locally]{.text-primary}
  
  #description
  One click in Claude Desktop, or `uvx bugzilla-mcp` everywhere else. Your API key never leaves your machine. A hosted server is available for trying it out.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-plug
  ---
  #title
  [Easy Integration]{.text-primary}
  
  #description
  Works seamlessly with Claude Code, Claude Desktop, Cursor IDE, Visual Studio Code, and any MCP-compatible client. Simple JSON configuration.
  :::
::
