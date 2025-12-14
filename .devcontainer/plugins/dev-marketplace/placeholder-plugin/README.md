# Placeholder Plugin

This is a placeholder plugin for the local development marketplace.

## Purpose

This plugin serves as a template and ensures the local marketplace structure remains valid when no actual plugins are installed.

## Creating New Plugins

To add a new plugin to this marketplace:

1. Create a new directory under `.devcontainer/plugins/dev-marketplace/`
2. Add `.claude-plugin/plugin.json` with plugin metadata
3. Add commands in `commands/` directory (`.md` files)
4. Add agents in `agents/` directory (`.md` files)
5. Add skills in `skills/` directory
6. Update `../.claude-plugin/marketplace.json` to register the plugin

## Plugin Structure

```
your-plugin/
├── .claude-plugin/
│   └── plugin.json      # Plugin metadata
├── README.md            # Documentation
├── commands/            # Slash commands
│   └── example.md
├── agents/              # Specialized agents
│   └── example.md
├── skills/              # Skills
│   └── example/
│       └── SKILL.md
└── hooks/               # Event hooks
    └── hooks.json
```
