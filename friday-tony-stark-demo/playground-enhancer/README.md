# LiveKit Playground Code Enhancer

This userscript improves source-code responses on `https://agents-playground.livekit.io/` with fenced-code rendering, syntax highlighting, and a copy button.

## Hosted Playground Setup

1. Install Tampermonkey for Chrome or Edge.
2. Create a new userscript.
3. Paste the contents of `agents_playground_code_enhancer.user.js`.
4. Save and enable the script.
5. Reopen the LiveKit Agents Playground.

The script detects fenced code blocks, highlights the declared language, and adds a Copy button. For best results, instruct the agent to always return multiline source code in Markdown fenced code blocks with a language tag such as `python`, `javascript`, or `bash`.

## Troubleshooting

- Confirm Tampermonkey and the script are enabled.
- Confirm the userscript `@match` includes `https://agents-playground.livekit.io/*`.
- Open DevTools and check for the enhancer startup log.
- Use the reformat control once when existing messages were rendered before the script loaded.

For deeper visual changes, self-host the LiveKit Agents Playground and modify its React message renderer directly.
