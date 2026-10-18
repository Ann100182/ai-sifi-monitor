# Loom Demo Script — AI SIFI Monitor

**Target length:** 4:30 – 5:00
**Target audience:** investors, analysts, hiring managers, portfolio reviewers
**Pacing:** conversational, ~140 words/min. Pause 1 second between scenes to let visuals settle.

---

## Before you hit record

1. **Install Loom** — https://www.loom.com/download (Chrome extension or desktop app)
2. **Start the dashboard** in Terminal:
   ```bash
   cd /Users/aniketa/ai-sifi-monitor
   source .venv/bin/activate
   streamlit run app.py
   ```
3. Open **http://localhost:8501** in a fresh browser window. Make the window full-screen.
4. **Open Loom** → "New recording" → **Screen + Camera** (or Screen Only if you prefer) → **Full desktop** (so the browser URL bar stays visible as context).
5. Mic check — speak a sentence, play it back, make sure levels are good.
6. **Close distractions** — Slack, Mail notifications. Turn on Do Not Disturb (⌘⇧D in some apps, or System Settings → Focus).
7. Have this script open on a second monitor OR printed. Read it like a radio broadcaster — don't rush, don't trail off.

---

## Scene 1 — Hook (0:00 – 0:25)

**Show:** AI SIFI Monitor homepage, "All Tiers" view visible with 45 players and the market-cap concentration chart.

**Say:**

> "Hey — I'm walking through a dashboard I built called the AI SIFI Monitor. The thesis is simple: the AI compute buildout today looks a lot like the pre-2008 banking system. A small number of institutions carry interlocking obligations, off-balance-sheet leverage, and single-source dependencies that no individual balance sheet makes visible. This dashboard tracks the 45 companies at the center of that chain — and the leading indicators of stress."

---

## Scene 2 — Why this exists (0:25 – 0:55)

**Show:** Scroll slowly past the subtitle on the main page. Hover briefly over the "Portfolio Overview" header.

**Say:**

> "The question I kept asking after reading Michael Cembalest's 2026 Outlook and the Morgan Stanley financing podcast was: where exactly is the systemic risk? Four semiscalers and four hyperscalers are now sixteen percent of global equity market cap. One point three trillion dollars of hyperscaler capex since ChatGPT. Oracle committed sixty billion a year of compute to OpenAI — which doesn't yet earn that much revenue. Meta's twenty-seven-billion-dollar Hyperion SPV sits off its balance sheet. I wanted a single view of all of that."

---

## Scene 3 — The 8-tier stack (0:55 – 1:30)

**Show:** Click into the sidebar — hover over each tier briefly from top to bottom (Power Gen, Grid, Semi Equip, Semi Design, Semi Mfg, AI Hardware, Hyperscalers, AI Software).

**Say:**

> "I grouped the forty-five players into eight interlocking tiers. The sidebar on the left lets you browse them. At the bottom you've got power generation — the utilities. Then grid capital equipment. Then semi equipment and EDA, which is just ASML and Cadence. Then semi design — NVIDIA, AMD, the designers. Then semi manufacturing, which is literally one company: TSMC. Then hardware and networking, then hyperscalers — Microsoft, Google, Amazon, Meta, Oracle, CoreWeave. And at the top, the software and apps layer. If any lower tier fails, everything above it stalls."

---

## Scene 4 — Portfolio tab, Hyperscalers drilldown (1:30 – 2:30)

**Show:** Click **Hyperscalers** in the sidebar. Let the page render. Point out the status pills (critical/elevated/watch counts) at the top, then scroll down into the Risk × Investment Matrix table.

**Say:**

> "Let me click into Hyperscalers to show the drilldown. You get a tier header with a one-line thesis — hyperscaler capex is the demand engine, if monetization disappoints the whole stack re-rates. The pill strip at the top shows the status breakdown: how many are rated Critical, Elevated, Watch, or Normal based on the composite risk score. And then the Risk by Investment Matrix is the core table — every player with a status badge, a ten-point risk score as the red-yellow-green bar, a ten-point opportunity score as the blue bar, and a one-line bull factor on the right. Oracle flagged critical here — levered to OpenAI, debt-funded capex. CoreWeave right behind it — most levered neocloud. Microsoft and Amazon elevated. Google and Meta are watch. The numbers are hand-tuned from Cembalest's analysis — not scraped, intentional."

---

## Scene 5 — Vintage Analysis tab (2:30 – 3:15)

**Show:** Click the **Vintage Analysis** tab. Wait for the growth-of-$10K chart to render.

**Say:**

> "Second tab answers a specific question: if I'd put ten thousand dollars into each of these companies five, ten, or fifteen years ago, where would I be today? Default is top ten by current market cap, you can override the selection. The chart shows the growth paths. The table gives you CAGR and max drawdown for each vintage. Useful for sanity-checking the quality-of-moat argument — the hyperscalers really did generate three to four times the market return over fifteen years."

---

## Scene 6 — News & Risk Monitor (3:15 – 4:05)

**Show:** Click **News & Risk Monitor** tab. Wait for the feeds to load. Scroll to the "Risk theme activity" chart, then to the flagged headlines with the red/yellow/green indicators.

**Say:**

> "Third tab is the live news layer. Per ticker, it pulls Google News RSS — which aggregates Bloomberg, WSJ, Reuters, FT. Plus direct Bloomberg Markets, Tech, and Opinion feeds for the broader stack. Every headline is tagged against an eleven-theme risk taxonomy — Taiwan Strait, China sanctions, US power grid, GPU oversupply, OpenAI concentration, SPV leverage, rare earths, and so on. Each hit carries a severity weight from one to three. The chart shows which themes are hot right now. The flagged headlines down here have red dots for severity-three events — stuff like 'Nvidia, Oracle, CoreWeave sink on OpenAI revenue report.' That score feeds back into the Portfolio tab ranking."

---

## Scene 7 — Stack Comparison (4:05 – 4:30)

**Show:** Click **Stack Comparison** tab. Point at the dispersion strip plot. Expand one of the tier drilldowns (Semi Manufacturing or Hyperscalers).

**Say:**

> "Fourth tab compares peers inside each tier. The strip plot shows YTD return dispersion by layer. Within each tier you can see best and worst performer, best and worst FCF margin, highest and lowest leverage. Where this matters most is the concentrated tiers — if TSMC is the only player in semi manufacturing, there's no diversification. If the hyperscaler cohort splits — say Oracle and CoreWeave selling off while Google and Meta hold up — that's a thesis signal worth acting on."

---

## Scene 8 — Close (4:30 – 5:00)

**Show:** Click back to Portfolio tab or scroll to the top. Pan to the URL bar briefly.

**Say:**

> "Repo is on GitHub at github dot com slash Ann one hundred one eighty-two slash ai dash sifi dash monitor. It's a Streamlit app — three pip installs and it runs. No API keys. No paid services. The point isn't the dashboard itself — it's that the SIFI framing applied to the AI compute stack surfaces a lot of risk that institutional capital hasn't fully priced yet. If any of this resonates, hit me up. Thanks for watching."

---

## Post-recording checklist

1. **Trim the dead air** at the start and end in Loom.
2. **Title it** something searchable: "AI SIFI Monitor — Dashboard Walkthrough" or "Pre-2008 SIFI Framework for the AI Buildout."
3. **Thumbnail**: pick a frame showing the Risk × Investment Matrix (visually distinctive).
4. **Description:** paste the Scene 1 opener + repo link.
5. **Share settings:** make it public if you want it discoverable; link-only if private.
6. **Share** the Loom URL in LinkedIn / email / portfolio.

---

## If you prefer AI narration instead of your own voice

The script above reads clean for text-to-speech. For a non-voice option:

1. Copy each scene's "Say:" block
2. Generate audio in **ElevenLabs** (free tier works), **Play.ht**, or **macOS Terminal**: `say -v "Samantha" -o scene1.aiff "..."` → convert to mp3
3. Record the screen separately with QuickTime (⌘⇧5)
4. Combine in **iMovie** (free, built-in) or **Descript** (free tier) — put audio on one track, screen capture on the other

Loom's native "voice over existing video" feature also works if you'd rather record the screen first and dub over it.
