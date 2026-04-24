# CookBot AI Mode

CookBot AI mode is advisory only.

The accepted AI plan schema is:

```json
{
  "steps": [
    {
      "type": "snapshot",
      "payload": {}
    }
  ],
  "notes": "optional note"
}
```

Allowed step types:

- `move_joint`
- `set_gripper`
- `wait`
- `home_all`
- `snapshot`
- `recipe_note`

Forbidden step types include heating, knives, relays, raw Mega commands, code execution, and autonomous cooking. The mock AI intentionally proposes a forbidden `heat` step for cooking prompts so tests verify safety rejection.

OpenAI-compatible mode is selected with:

```text
COOKBOT_AI=openai_compatible
COOKBOT_AI_BASE_URL=https://api.openai.com/v1
COOKBOT_AI_API_KEY=...
COOKBOT_AI_MODEL=gpt-4o-mini
```

The backend asks for JSON object output and then validates it with the same CookBot safety layer. Missing or malformed API responses fail closed.
