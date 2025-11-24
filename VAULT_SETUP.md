# Vault Setup Instructions

This document explains how to retrieve the Anthropic API key from vault and configure it for Wordlebot's AI agent feature.

## Prerequisites

- Access to vault.lab.thewortmans.org
- Vault CLI installed (optional, but recommended)

## Retrieving the API Key

### Option 1: Using Vault CLI

```bash
# Login to vault
vault login

# Retrieve the Anthropic API key
vault kv get secret/wordlebot/anthropic
```

### Option 2: Using Vault Web UI

1. Navigate to https://vault.lab.thewortmans.org
2. Login with your credentials
3. Navigate to secret/wordlebot/anthropic
4. Copy the ANTHROPIC_API_KEY value

## Configuring Wordlebot

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and paste your API key:
   ```bash
   ANTHROPIC_API_KEY=your_actual_api_key_here
   CLAUDE_MODEL=claude-3-5-sonnet-20241022
   ```

3. Verify the file is not tracked by git:
   ```bash
   git status
   # .env should NOT appear in the output
   ```

## Security Notes

- Never commit the `.env` file to version control
- The `.env` file is already listed in `.gitignore`
- Keep your API key secure and do not share it
- Rotate keys periodically per security best practices

## Troubleshooting

### API Key Not Found in Vault

If the API key doesn't exist in vault yet:

1. Obtain an Anthropic API key from https://console.anthropic.com
2. Store it in vault:
   ```bash
   vault kv put secret/wordlebot/anthropic ANTHROPIC_API_KEY="your_key_here"
   ```

### Permission Denied

Contact your vault administrator to ensure you have read access to the `secret/wordlebot/anthropic` path.
