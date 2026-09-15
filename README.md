# Shark Tank AI

Pitch a startup to an AI investment committee and get real, evidence-grounded feedback.

Shark Tank AI is a turn-based Streamlit app. You (**"Little Fish"**) submit a
proposal; a neutral **Moderator** runs the session; three independent
**Sharks** — Conservative, Growth, and Balanced, each with a different
investment philosophy — question you one at a time, research your market,
deliberate privately, make their own offers, and negotiate with you. At the
end you get a two-page **Founder Feedback Report** you can download as a PDF.

## How it works

1. You paste or upload your pitch.
2. The Moderator checks it's a real proposal and pulls out the key facts (ask amount, equity, valuation).
3. The committee researches your market and competitors before questioning you.
4. Each of the three Sharks asks a question based on your pitch and the research — you answer each in turn.
5. The Sharks deliberate privately (you don't see this part).
6. A Verification step checks whether each Shark's reasoning is actually supported by the evidence.
7. A Consensus step reconciles all three positions into one formal committee view — never just a majority vote.
8. A financial analysis computes valuation, margins, growth, and runway from your numbers, and flags anything inconsistent.
9. Interested Sharks each make their own offer, one at a time.
10. You get one negotiation round with each interested Shark.
11. You get a clear final outcome — a deal, a pass, or no deal reached.
12. A Founder Feedback Report is generated: what's strong, what needs work, and a prioritized action plan — grounded in how real early-stage investors (YC, Techstars, Sequoia, and others) evaluate startups.

Every stage degrades gracefully if the AI provider is unavailable — you'll see an honest "unavailable" message, never a fake decision.

## Do I need an API key?

The app **runs without one** — every stage falls back to a simple deterministic placeholder, so you can try the full flow with no setup. For real AI-driven analysis (real questions, real research, real feedback), you need an [Anthropic API key](https://console.anthropic.com/). Usage is billed by Anthropic per their pricing; you're responsible for your own account. Shark Tank AI does not include a shared key.

## Getting it

Three ways to run it, depending on who you are:

| | Best for | You need |
|---|---|---|
| [**Windows app**](#windows-app-easiest) | Just want to use it | Nothing — no Python, no Git |
| [**Docker**](#docker) | Reproducible, isolated | Docker Desktop |
| [**Python**](#python-developers) | Developers / contributors | Python 3.11+ |

### Windows app (easiest)

1. Go to the project's [GitHub Releases page](https://github.com/ShantanuDutt1/Shark-Tank-AI/releases) and download the latest `SharkTankAI-Windows.zip`.
2. Right-click the ZIP → **Extract All** → choose a folder → open it.
3. Double-click **`SharkTankAI.exe`**. Your browser opens to the app automatically.
4. First time only: create a file named `.env` in the same folder as the `.exe`, containing:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
   Without it, the app still runs — just without real AI reasoning.
5. Use the app. When you're done, close the window (or press Ctrl+C in the console) to shut it down.
6. Click **Reset** any time to start a new pitch with a clean slate.

Your key stays in your local `.env` file — it's never sent anywhere except directly to Anthropic's API, never bundled into the app, and never logged.

> Windows may show a SmartScreen warning because this executable isn't code-signed (code signing costs money most solo/open-source projects don't have). If you trust the source, click **More info → Run anyway**. See [Troubleshooting](#troubleshooting).

### Docker

```bash
git clone https://github.com/ShantanuDutt1/Shark-Tank-AI.git
cd Shark-Tank-AI
cp .env.example .env   # optional — add your ANTHROPIC_API_KEY here
docker compose up --build
```

Open `http://localhost:8501`. Stop with `Ctrl+C`, or `docker compose down` to remove the container.

### Python (developers)

Requires Python 3.11+.

```bash
git clone https://github.com/ShantanuDutt1/Shark-Tank-AI.git
cd Shark-Tank-AI
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # optional — add your ANTHROPIC_API_KEY here
streamlit run app.py
```

## Privacy and data handling

- Your API key lives only in your own `.env` file / environment variable — it's read locally to call Anthropic's API and is never logged, displayed, or embedded in any distributed build.
- Nothing is stored between sessions. There's no database and no persistent memory — closing the app or clicking Reset discards everything (proposal, research, Shark reasoning, report) permanently.
- Emails, phone numbers, and street addresses in your proposal and answers are redacted before they reach any AI prompt (regex-based — not a comprehensive PII filter).
- Market research sends parts of your proposal to Anthropic's web search tool to find comparable companies and market data; retrieved sources are treated as untrusted data, never as instructions.

## Resetting a session

Click **End Session**. This immediately discards the current proposal, conversation, research, Shark positions, and report — nothing carries over to your next pitch.

## Troubleshooting

**App won't start.** Check the console/terminal for an error. For the Windows app, make sure you extracted the full ZIP first (don't run the `.exe` from inside the archive).

**Windows blocks the executable.** SmartScreen flags unsigned apps by default. Click **More info → Run anyway** if you trust the source (this project isn't code-signed — see [Windows app](#windows-app-easiest)). Don't disable your antivirus; just approve this one file.

**"API key problem" / analysis looks generic.** You're missing or have an invalid `ANTHROPIC_API_KEY`. Check your `.env` file has the right key with no extra quotes or spaces.

**Port already in use.** The Windows app automatically tries the next port if 8501 is busy — check the console output for the actual URL. For Docker/Python, stop whatever else is using port 8501, or edit `SERVER_PORT` in `.env`.

**Browser doesn't open automatically.** Open `http://localhost:8501` (or whatever port the console shows) manually.

**Report won't generate / research fails.** Usually a transient API issue — the app still completes the session with an honest "unavailable" message rather than crashing. Try a new session.

**App seems frozen.** Real AI calls take a few seconds each; the UI shows a spinner during them. If nothing changes for over a minute, check the console for errors.

Still stuck? [Open an issue](https://github.com/ShantanuDutt1/Shark-Tank-AI/issues).

## Limitations

- Analysis quality depends on available web evidence — private companies and niche markets may have thin research.
- Valuation feedback is an evidence-grounded range, not an objective "correct" valuation.
- AI analysis can be wrong; this is a practice tool, not investment advice.
- One negotiation round per interested Shark — no counter-to-a-counter.
- No persistence across sessions or app restarts.
- The Windows build is unsigned.
- PII redaction and prompt-injection defenses are best-effort, not a guarantee.

Full technical details and the maintained roadmap: [docs/architecture.md](docs/architecture.md), [docs/release_backlog.md](docs/release_backlog.md).

## Project structure

```
agents/         AI agents (Moderator, Sharks, Research, Verification, Financial Analyst, Founder Feedback)
orchestrator/   Session Director, Event Bus, turn/negotiation control, Consensus Engine
providers/      LLM + research provider abstractions (Anthropic)
models/         Shared data models
prompts/        Prompt templates
ui/             Streamlit interface
config/         Settings and logging
utils/          PII redaction, PDF extraction/rendering, financial calculations
packaging/      Standalone Windows build (launcher, build script)
tests/          Unit and end-to-end tests
docs/           Architecture, state machines, event catalog, and release history
```

## For developers

```bash
python -m compileall -q .
ruff check .
pytest -q
```

The test suite includes unit tests for every agent and component, plus `tests/test_release_0_9_5_e2e.py` — a full end-to-end simulation driven through the real UI with a realistic reference proposal (`tests/fixtures/proposals/`). None of it requires a live API key or network access.

See [docs/architecture.md](docs/architecture.md) for system design, [docs/folder_structure.md](docs/folder_structure.md) for what owns what, [docs/agent_personas.md](docs/agent_personas.md) for the Shark personas, and [docs/release_log.md](docs/release_log.md) for what shipped in each release. Building the standalone Windows package: see [packaging/README.md](packaging/README.md).

## License

Apache License 2.0 — see [LICENSE](LICENSE).
