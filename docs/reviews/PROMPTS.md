# AI Review Prompts for BBB26 Dashboard

Use these prompts with different AI models to get diverse perspectives on the dashboard.

**Important**: Each agent must save their response to `docs/reviews/` with the filename format:
```
{MODEL_NAME}_{FOCUS}_{UNIQUE_ID}.md
```

Examples:
- `claude-opus_ux_a1b2c3.md`
- `gpt4o_technical_x7y8z9.md`
- `gemini_polish_m4n5o6.md`

---

## Prompt A: UX & Information Architecture Focus

**Suggested models**: Claude, GPT-4o, Gemini

**Prompt**:

```
You are reviewing a data dashboard for Big Brother Brasil 26 (BBB26).

FIRST, read the full handout at: docs/AI_REVIEW_HANDOUT.md

YOUR FOCUS: Sections 1-6 (Landing Page, Section Ordering, Cross-Page Data, Missing Insights, Visual Hierarchy, Page Layout)

DELIVERABLES (write all of these):
1. Executive Summary (3-5 bullet points of biggest UX opportunities)
2. Landing Page Recommendations (proposed section order, new sections, what to remove)
3. Cross-Page Architecture (what to duplicate vs link)
4. New Features/Insights (ranked by impact)
5. Section Ordering for each page (with rationale)
6. Storytelling Narrative (what story should the dashboard tell?)
7. Layout Format Recommendation (Quarto Dashboards vs articles)

CONSTRAINTS TO RESPECT:
- Portuguese (Brazilian) language
- Static hosting only (GitHub Pages)
- Free tier only (no paid services)
- Quarto + Plotly stack (don't suggest replacing)

ANSWER THE OPEN QUESTIONS in the handout with clear reasoning.

SAVE YOUR RESPONSE TO: docs/reviews/{YOUR_MODEL_NAME}_ux_{UNIQUE_6_CHAR_ID}.md

Use a 6-character alphanumeric ID (e.g., a1b2c3) to avoid filename conflicts.

Be specific and actionable. Include mock layouts or ASCII diagrams where helpful.
```

---

## Prompt B: Technical Implementation Focus

**Suggested models**: Claude, GPT-4o, Gemini, DeepSeek

**Prompt**:

```
You are reviewing the technical architecture of a data dashboard for Big Brother Brasil 26 (BBB26).

FIRST, read the full handout at: docs/AI_REVIEW_HANDOUT.md

YOUR FOCUS: Sections 7-11 (Interactivity, Deployment, Cartola BBB, Data Storage, Mobile/Accessibility)

DELIVERABLES (write all of these):
8. Interactivity Assessment
   - Is interactivity essential, nice-to-have, or unnecessary?
   - Recommended approach (Shiny, Observable, pure JS, or none)
   - Specific interactive features worth implementing
   - Trade-offs with static hosting

9. Deployment & Robustness Review
   - Is GitHub Pages + Actions sufficient?
   - Recommended safeguards
   - Performance concerns at 90+ days of data

10. Cartola BBB Page Design
    - Proposed visualizations
    - What can be auto-calculated vs manual
    - Page structure

11. Data Storage Architecture Assessment
    - Is JSON-per-snapshot optimal for 90+ days?
    - Pre-computation strategies
    - Support for interactive date selection
    - Git repository size management

12. Mobile & Accessibility Review
    - Key issues to fix
    - Recommended improvements

CONSTRAINTS TO RESPECT:
- Static hosting only (GitHub Pages) - no server-side code in production
- Free tier only
- Quarto + Plotly stack
- ~90 days of data by end of season

ANSWER THE OPEN QUESTIONS in the handout related to technical decisions.

SAVE YOUR RESPONSE TO: docs/reviews/{YOUR_MODEL_NAME}_technical_{UNIQUE_6_CHAR_ID}.md

Use a 6-character alphanumeric ID (e.g., x7y8z9) to avoid filename conflicts.

Provide code snippets or configuration examples where relevant.
```

---

## Prompt C: Polish, Growth & Quality Focus

**Suggested models**: Claude, GPT-4o, Gemini

**Prompt**:

```
You are reviewing the polish, discoverability, and quality aspects of a data dashboard for Big Brother Brasil 26 (BBB26).

FIRST, read the full handout at: docs/AI_REVIEW_HANDOUT.md

YOUR FOCUS: Sections 12-14 + overall polish (SEO, Social Sharing, Testing, Competitive Analysis)

DELIVERABLES (write all of these):
13. SEO & Social Sharing Strategy
    - Meta tags and Open Graph setup for Quarto
    - Shareable content features
    - How BBB fans will discover this

14. Testing Strategy Proposal
    - What to test (data loading, calculations, charts)
    - How to test (Python tests, CI checks, visual regression)
    - Error handling improvements

15. Competitive Analysis
    - Find 2-3 similar projects (BBB fan sites, reality TV analytics, social network visualizations)
    - What can we learn from them?
    - What makes our dashboard unique?

BONUS DELIVERABLES:
- Quick wins (low effort, high impact improvements)
- "Wow factor" features that would make this stand out
- Community/viral features (what would make people share this?)

CONSTRAINTS TO RESPECT:
- Portuguese (Brazilian) audience
- Static hosting only
- Free tier only
- No user accounts/login

SAVE YOUR RESPONSE TO: docs/reviews/{YOUR_MODEL_NAME}_polish_{UNIQUE_6_CHAR_ID}.md

Use a 6-character alphanumeric ID (e.g., m4n5o6) to avoid filename conflicts.

Include specific examples and links to comparable projects.
```

---

## Prompt D: Fresh Eyes / Holistic Review

**Suggested models**: Any model not used above, or a second pass with a different model

**Prompt**:

```
You are a fresh reviewer looking at a data dashboard for Big Brother Brasil 26 (BBB26) for the first time.

FIRST, read the full handout at: docs/AI_REVIEW_HANDOUT.md

YOUR TASK: Provide a holistic review without being constrained to specific sections. Look at the big picture.

ANSWER THESE QUESTIONS:
1. What's the single biggest problem with the current approach?
2. What's the single best thing about it?
3. If you could only make 3 changes, what would they be?
4. What's missing that seems obvious to an outsider?
5. What would make a casual BBB viewer visit this daily?
6. What would make a data enthusiast share this on Twitter/LinkedIn?
7. Is the 5-page structure right, or should it be reorganized?
8. Rate the current approach (1-10) and explain why.

ALSO PROVIDE:
- Top 5 "quick wins" (things that could be done in a day)
- Top 3 "big bets" (things worth significant investment)
- 1 "wild idea" (something unconventional that might work)

CONSTRAINTS TO RESPECT:
- Static hosting only (GitHub Pages)
- Free tier only
- Portuguese (Brazilian) language
- Quarto + Plotly stack (don't suggest replacing)

SAVE YOUR RESPONSE TO: docs/reviews/{YOUR_MODEL_NAME}_holistic_{UNIQUE_6_CHAR_ID}.md

Use a 6-character alphanumeric ID (e.g., h9j0k1) to avoid filename conflicts.

Be direct and opinionated. We want honest feedback, not diplomatic hedging.
```

---

## Prompt E: Data Visualization Specialist

**Suggested models**: Claude, GPT-4o (especially good for viz recommendations)

**Prompt**:

```
You are a data visualization expert reviewing charts and visual design for a Big Brother Brasil 26 dashboard.

FIRST, read the full handout at: docs/AI_REVIEW_HANDOUT.md

YOUR FOCUS: The visualizations themselves - chart types, design, effectiveness

REVIEW THESE CURRENT VISUALIZATIONS:
1. Horizontal bar chart (sentiment ranking)
2. 22×22 heatmap with emoji (reaction matrix)
3. Diverging bar chart (winners/losers)
4. Difference heatmap (changes between days)
5. Sankey diagram (reaction flow)
6. Scatter plots (various correlations)
7. Line charts (sentiment over time)
8. Network graph (relationship visualization)
9. Stacked bar charts (various breakdowns)
10. Pie charts (vote coherence)

FOR EACH, ANSWER:
- Is this the right chart type for this data?
- What would you change about the design?
- Are there better alternatives?

ALSO PROVIDE:
- 3 new visualizations we should add
- Chart types we're overusing or misusing
- Color scheme recommendations (currently dark theme)
- Mobile-friendly visualization alternatives
- Accessibility improvements for charts

CONSTRAINTS:
- Must use Plotly (Python) - no D3.js or other libraries
- Dark theme (#222 background, #303030 chart backgrounds)
- Emoji must be readable in charts
- Static output (no server-side interactivity)

SAVE YOUR RESPONSE TO: docs/reviews/{YOUR_MODEL_NAME}_dataviz_{UNIQUE_6_CHAR_ID}.md

Use a 6-character alphanumeric ID to avoid filename conflicts.

Include sketch descriptions or ASCII mockups for new visualization ideas.
```

---

## How to Run Multiple Agents

### Option 1: Sequential (One at a time)
Run each prompt with a different model, wait for completion, then run the next.

### Option 2: Parallel (Recommended)
If you have access to multiple AI interfaces, run all prompts simultaneously:
- Tab 1: Claude with Prompt A
- Tab 2: GPT-4o with Prompt B
- Tab 3: Gemini with Prompt C
- Tab 4: DeepSeek with Prompt D
- Tab 5: Another Claude/GPT with Prompt E

### Option 3: Same Model, Different Prompts
Run the same model (e.g., Claude) with each prompt. The different focus areas will produce different outputs.

---

## After Collecting Reviews

Create a consolidation document:

```
docs/reviews/CONSOLIDATION.md
```

Structure:
1. **Consensus items** - Recommendations that appear in multiple reviews
2. **Conflicts** - Contradictory recommendations (need human decision)
3. **Unique insights** - Ideas from only one review worth considering
4. **Filtered out** - Suggestions that violate constraints
5. **Action items** - Prioritized list of what to implement

---

## Filename Examples

After running all prompts, the `docs/reviews/` directory should look like:

```
docs/reviews/
├── PROMPTS.md                          # This file
├── CONSOLIDATION.md                    # Your synthesis (create after)
├── claude-opus_ux_a1b2c3.md
├── gpt4o_technical_x7y8z9.md
├── gemini_polish_m4n5o6.md
├── deepseek_holistic_h9j0k1.md
├── claude-sonnet_dataviz_p2q3r4.md
└── ... (more reviews)
```
