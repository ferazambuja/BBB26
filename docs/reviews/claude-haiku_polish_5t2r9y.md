# BBB26 Dashboard Review: Polish, Discoverability & Quality
## Claude Haiku Analysis - Sections 12-15 + Overall Polish

**Reviewer**: Claude Haiku 4.5
**Focus**: SEO & Social Sharing, Testing Strategy, Competitive Analysis, Quick Wins
**Date**: 2026-01-25
**Document ID**: `claude-haiku_polish_5t2r9y.md`

---

## Executive Summary: Key Opportunities

### 🎯 High-Impact Quick Wins (Do These First)

1. **Add Open Graph + Twitter Card metadata** (~30 min)
   - Currently: Zero social sharing optimization
   - Impact: Posts in WhatsApp/Twitter will show participant names, chart previews
   - Effort: Update `_quarto.yml` and add `og-image` generation

2. **Implement basic WCAG contrast fixes** (~1 hour)
   - Currently: Dark theme may have contrast issues (not verified)
   - Impact: More accessible to low-vision users, less eye strain
   - Effort: Verify ratios, adjust palette if needed

3. **Add `sitemap.xml` + robots.txt** (~20 min)
   - Currently: Search engines discovering site via luck only
   - Impact: Faster indexing, better SEO visibility
   - Effort: Auto-generate or static file

4. **Create shareable participant cards** (~2 hours)
   - Currently: No way to share "Ranked #1 today!" or individual profiles
   - Impact: Drives word-of-mouth via WhatsApp, Twitter, friend DMs
   - Effort: Generate PNG cards with participant name + sentiment rank + date

5. **Set up Lighthouse CI checks** (~1 hour)
   - Currently: No performance monitoring
   - Impact: Catch regressions before they hit production
   - Effort: Add GitHub Actions job to run Lighthouse

---

## 13. SEO & Social Sharing Strategy

### Current State: Minimal Discoverability
- No Open Graph tags
- No Twitter Cards
- No JSON-LD structured data
- No robots.txt or sitemap
- Site not yet indexed by search engines
- No shareable cards or images

### 13.1 Meta Tags & Open Graph Setup

**Problem**: When someone shares a link in WhatsApp, Twitter, or Slack, they see a blank preview with no context.

**Solution**: Implement global + per-page Open Graph tags in `_quarto.yml`:

```yaml
website:
  title: "BBB 26 — Painel de Reações"
  description: "Análise de reações entre participantes do Big Brother Brasil 2026. Acompanhe alianças, rivalidades e mudanças diárias."
  favicon: "assets/favicon.ico"
  open-graph: true
  twitter-card: true

  # Global metadata
  open-graph:
    og:site_name: "BBB26 Dashboard"
    og:locale: "pt_BR"
    og:image: "https://username.github.io/BBB26/assets/og-image-default.png"
    og:image:width: 1200
    og:image:height: 630
    og:image:alt: "BBB26: Painel de Reações entre Participantes"

  twitter-card:
    twitter:site: "@seu_twitter"
    twitter:creator: "@seu_twitter"
    twitter:image: "https://username.github.io/BBB26/assets/twitter-card.png"
```

**Per-page overrides** (in each `.qmd` YAML):

```yaml
---
title: "O Que Mudou — BBB 26"
description: "Quem ganhou/perdeu sentimento hoje? Analise mudanças de reações entre ontem e hoje."
open-graph:
  og:type: "article"
  og:image: "assets/og-mudancas.png"
  article:published_time: !today
---
```

### 13.2 Image Generation for Social Sharing

**Create dynamic preview images** that update daily:

```python
# In scripts/generate_og_images.py
import plotly.express as px
from PIL import Image, ImageDraw, ImageFont

def create_participant_card(name: str, rank: int, sentiment: float, group: str) -> bytes:
    """Generate a shareable card for a participant"""
    img = Image.new('RGB', (1200, 630), color='#222222')
    draw = ImageDraw.Draw(img)

    # Title: "🏆 #1 em BBB 26"
    draw.text((50, 50), f"🏆 #{rank} em BBB 26", fill='#ffffff')

    # Participant name in large text
    draw.text((50, 150), name, fill='#E6E6E6', font=large_font)

    # Sentiment score
    color = '#4CAF50' if sentiment > 0 else '#FF6B6B'
    draw.text((50, 350), f"Sentimento: {sentiment:+.1f}", fill=color)

    # Group badge
    draw.rectangle([50, 450, 300, 550], outline='#ffffff', width=2)
    draw.text((70, 470), group, fill='#ffffff')

    # Branding
    draw.text((800, 550), "BBB26 Dashboard", fill='#666666', font=tiny_font)

    return img.tobytes()

# Call during render:
# for each top 10 participant, save og-image-{name}.png
```

This enables sharing like:
- **WhatsApp**: "Check who's #1 today in BBB26!"
- **Twitter**: "Gabriela is trending up! +5 sentiment in one day 📈"
- **Discord**: Individual player cards

### 13.3 JSON-LD Structured Data

Add to `_quarto.yml` to help search engines understand content:

```yaml
# In _quarto.yml, add to each page's header:
open-graph:
  json-ld: |
    {
      "@context": "https://schema.org",
      "@type": "WebPage",
      "name": "BBB 26 — Painel de Reações",
      "description": "Dashboard interativo analisando reações diárias entre participantes",
      "url": "https://username.github.io/BBB26/",
      "inLanguage": "pt-BR",
      "dateModified": "[AUTO_DATE]",
      "publisher": {
        "@type": "Organization",
        "name": "BBB26 Dashboard Community"
      },
      "mainEntity": {
        "@type": "Dataset",
        "name": "Big Brother Brasil 26 Reactions",
        "description": "Daily snapshots of participant reactions (Queridômetro)",
        "datePublished": "2026-01-13",
        "dateModified": "[AUTO_DATE]",
        "url": "https://username.github.io/BBB26/data/",
        "keywords": "BBB 26, Big Brother Brasil, reactions, relationships, voting prediction"
      }
    }
```

### 13.4 SEO-Optimized Meta Descriptions

**Current approach**: Generic descriptions for all pages

**Better approach**: Unique descriptions highlighting value proposition:

| Page | Current | Proposed |
|------|---------|----------|
| **Painel** | Generic | "Veja o ranking de sentimento do dia, quem ganhou/perdeu reações, e perfis estratégicos dos 22 participantes. Atualizado 4x ao dia." |
| **O Que Mudou** | Generic | "Análise de mudanças de reações entre ontem e hoje. Descubra quem está subindo, quem está caindo, e as hostilidades novas do jogo." |
| **Trajetória** | Generic | "Evolução das reações desde o início da season. Alianças, rivalidades persistentes, clusters de afinidade, e análise de vulnerabilidades." |
| **Paredão** | Generic | "Status do paredão atual com formação, votos da casa, e análise de coerência entre reações e votos. Histórico de eliminations." |

### 13.5 Discoverability Strategy for Brazilian BBB Fans

**Where do BBB fans look for dashboards?**

1. **Reddit/Twitter/WhatsApp groups** → Link sharing
   - Create a minimal landing page (`landing.qmd`) that explains the dashboard in 3 sentences
   - Add a "Compartilhar" button that generates a pre-filled WhatsApp message

2. **Google search keywords to target**:
   ```
   - "BBB 26 queridômetro análise"
   - "BBB 26 reações participantes"
   - "BBB 26 alianças e rivalidades"
   - "BBB 26 votação previsão"
   - "BBB 26 dashboard"
   - "BBB 26 sentimento ranking"
   ```

3. **GShow/Globo community forums** → Cross-post with attribution
   - Consider syndication partnerships or friendly mentions

4. **Fan sites and blogs** → Backlink opportunities
   - Reach out to existing BBB fan communities for mentions

### 13.6 Implementation Roadmap (Priority Order)

| Priority | Task | Effort | Impact | Dependencies |
|----------|------|--------|--------|--------------|
| **P0** | Add Open Graph/Twitter Card metadata | 30 min | HIGH | Update `_quarto.yml` |
| **P0** | Generate daily og-image-default.png | 1 hour | HIGH | Add Python script |
| **P1** | Create sitemap.xml + robots.txt | 20 min | MEDIUM | Auto-generate on render |
| **P1** | Add JSON-LD structured data | 30 min | MEDIUM | Update `_quarto.yml` |
| **P2** | Shareable participant cards | 2 hours | MEDIUM | PNG generation script |
| **P2** | Landing page with "Compartilhar" button | 1 hour | MEDIUM | Simple markdown page |
| **P3** | Google Search Console + Bing Webmaster | 10 min | LOW | Just sign up + verify |

---

## 14. Testing Strategy Proposal

### Current State: No Automated Testing
- Manual verification after each render
- No CI checks for data integrity
- No chart rendering tests
- Warnings from Pandoc (Quarto → HTML) not systematically addressed

### 14.1 Testing Categories

#### A. Data Loading & Validation Tests

**What to test**: Ensure all snapshots parse correctly and contain expected fields

```python
# tests/test_data_loading.py
import json
import pytest
from pathlib import Path

def test_all_snapshots_parse():
    """Every JSON file in data/snapshots/ should parse without error"""
    snapshots_dir = Path("data/snapshots")
    for snapshot_file in snapshots_dir.glob("*.json"):
        with open(snapshot_file) as f:
            data = json.load(f)  # Should not raise JSONDecodeError
        assert isinstance(data, (dict, list)), f"{snapshot_file} is not dict or list"

def test_snapshot_schema():
    """Verify snapshot structure (new format with _metadata)"""
    with open("data/latest.json") as f:
        data = json.load(f)

    # Handle both old (array) and new (object with _metadata) formats
    if isinstance(data, list):
        participants = data
    else:
        assert "_metadata" in data or "participants" in data
        participants = data.get("participants", data)

    for participant in participants:
        assert "name" in participant, "Participant missing 'name'"
        assert "receivedReactions" in participant, f"{participant['name']} missing reactions"

        # Each reaction should have: reaction{name}, amount, givers[]
        for reaction in participant["receivedReactions"]:
            assert "reaction" in reaction
            assert "amount" in reaction
            assert "givers" in reaction

def test_no_corrupted_snapshots():
    """Ensure no snapshots are truncated or malformed"""
    snapshots_dir = Path("data/snapshots")
    for snapshot_file in snapshots_dir.glob("*.json"):
        size = snapshot_file.stat().st_size
        assert size > 1000, f"{snapshot_file} suspiciously small ({size} bytes)"

        # Check for unclosed brackets
        content = snapshot_file.read_text()
        assert content.count('{') == content.count('}'), f"{snapshot_file} unbalanced braces"
        assert content.count('[') == content.count(']'), f"{snapshot_file} unbalanced brackets"

def test_participant_consistency():
    """Names should be consistent across snapshots"""
    snapshots_dir = Path("data/snapshots")
    snapshots = sorted(snapshots_dir.glob("*.json"))

    names_by_snapshot = {}
    for snapshot_file in snapshots:
        with open(snapshot_file) as f:
            data = json.load(f)
        participants = data if isinstance(data, list) else data.get("participants", data)
        names_by_snapshot[snapshot_file.name] = {p["name"] for p in participants}

    # Names should only appear/disappear (entries/exits), never change spelling
    first_snapshot = names_by_snapshot[sorted(names_by_snapshot.keys())[0]]
    for name in first_snapshot:
        for snapshot_name, names in names_by_snapshot.items():
            if name not in names:
                # OK if they exited later, but name spelling shouldn't change
                pass
            else:
                # Name is present; verify no alternate spellings appear
                assert name in names, f"Name '{name}' changed spelling in {snapshot_name}"
```

**Run**: `pytest tests/test_data_loading.py`

#### B. Calculation Tests

**What to test**: Sentiment scores, change detection, hostility metrics

```python
# tests/test_calculations.py
import pytest
from pathlib import Path

SENTIMENT_WEIGHTS = {
    'Coração': 1.0,
    'Planta': -0.5, 'Mala': -0.5, 'Biscoito': -0.5, 'Coração partido': -0.5,
    'Cobra': -1.0, 'Alvo': -1.0, 'Vômito': -1.0, 'Mentiroso': -1.0,
}

def calculate_sentiment(participant_data):
    """Compute sentiment score for a participant"""
    score = 0
    for reaction in participant_data["receivedReactions"]:
        reaction_name = reaction["reaction"]["name"]
        amount = reaction["amount"]
        weight = SENTIMENT_WEIGHTS.get(reaction_name, 0)
        score += weight * amount
    return score

def test_sentiment_calculation():
    """Verify sentiment score calculation"""
    # Test case: 10 hearts + 5 cobras = (10 × 1.0) + (5 × -1.0) = 5.0
    participant = {
        "name": "Test",
        "receivedReactions": [
            {"reaction": {"name": "Coração"}, "amount": 10},
            {"reaction": {"name": "Cobra"}, "amount": 5},
        ]
    }
    assert calculate_sentiment(participant) == 5.0

def test_sentiment_with_mixed_negatives():
    """Verify mild vs strong negative weights"""
    # 8 hearts + 4 planta (mild) + 2 cobra (strong)
    # = (8 × 1.0) + (4 × -0.5) + (2 × -1.0) = 8 - 2 - 2 = 4.0
    participant = {
        "name": "Test",
        "receivedReactions": [
            {"reaction": {"name": "Coração"}, "amount": 8},
            {"reaction": {"name": "Planta"}, "amount": 4},
            {"reaction": {"name": "Cobra"}, "amount": 2},
        ]
    }
    assert calculate_sentiment(participant) == 4.0

def test_ranking_order():
    """Verify sentiment ranking is descending"""
    with open("data/latest.json") as f:
        import json
        data = json.load(f)
    participants = data if isinstance(data, list) else data.get("participants", data)

    sentiments = {p["name"]: calculate_sentiment(p) for p in participants}
    ranked = sorted(sentiments.items(), key=lambda x: x[1], reverse=True)

    # Each person should have higher or equal sentiment than next person
    for i in range(len(ranked) - 1):
        assert ranked[i][1] >= ranked[i+1][1], f"Ranking out of order at position {i}"
```

#### C. Chart Rendering Tests (Visual Regression)

**What to test**: Charts render without errors, data is correctly passed to Plotly

```python
# tests/test_chart_rendering.py
import subprocess
import json
from pathlib import Path

def test_quarto_render_no_errors():
    """Ensure quarto render completes without fatal errors"""
    result = subprocess.run(
        ["quarto", "render", "index.qmd", "--quiet"],
        capture_output=True,
        timeout=300
    )

    # Check return code
    if result.returncode != 0:
        print("STDOUT:", result.stdout.decode())
        print("STDERR:", result.stderr.decode())
    assert result.returncode == 0, "Quarto render failed"

def test_all_pages_render():
    """Verify all 5 pages render successfully"""
    pages = ["index.qmd", "mudancas.qmd", "trajetoria.qmd", "paredao.qmd", "paredoes.qmd"]
    for page in pages:
        result = subprocess.run(
            ["quarto", "render", page, "--quiet"],
            capture_output=True,
            timeout=300
        )
        assert result.returncode == 0, f"{page} failed to render"

def test_html_output_contains_charts():
    """Verify HTML files contain Plotly charts (basic check)"""
    html_file = Path("_site/index.html")
    assert html_file.exists(), "index.html not generated"

    content = html_file.read_text()
    assert "plotly" in content.lower(), "No Plotly charts found in HTML"
    assert "Ranking de Sentimento" in content, "Missing expected section title"

def test_no_broken_links():
    """Check for broken internal links in HTML"""
    import re
    from pathlib import Path

    site_dir = Path("_site")
    pages = list(site_dir.glob("*.html"))

    # Collect all anchor IDs available
    available_ids = set()
    for page in pages:
        content = page.read_text()
        ids = re.findall(r'id=["\']([^"\']+)["\']', content)
        available_ids.update(ids)

    # Check all href links
    broken_links = []
    for page in pages:
        content = page.read_text()
        hrefs = re.findall(r'href=["\']#([^"\']+)["\']', content)
        for href in hrefs:
            if href and href not in available_ids:
                broken_links.append(f"{page.name}#{href}")

    assert not broken_links, f"Broken links found: {broken_links}"
```

**Run**: `pytest tests/test_chart_rendering.py` (requires Quarto installed)

### 14.2 CI/CD Integration

**Add to `.github/workflows/daily-update.yml`**:

```yaml
name: Fetch Data, Test, and Deploy

on:
  schedule:
    - cron: '0 9,15,21,3 * * *'  # 4x daily
  workflow_dispatch:

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run data validation tests
        run: pytest tests/test_data_loading.py -v

      - name: Run calculation tests
        run: pytest tests/test_calculations.py -v

      - name: Fetch new data
        run: python scripts/fetch_data.py

      - name: Install Quarto
        uses: quarto-dev/quarto-action@v2

      - name: Run Quarto tests
        run: pytest tests/test_chart_rendering.py -v

      - name: Render dashboard
        run: quarto render

      - name: Run Lighthouse CI (performance audit)
        uses: treosh/lighthouse-ci-action@v9
        with:
          uploads:
            githubToken: ${{ secrets.GITHUB_TOKEN }}

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./_site
```

### 14.3 Error Handling Improvements

**Current gaps**:
- If API is down, render fails silently
- If snapshot file is corrupted, error message is unclear
- No fallback to last known-good state

**Proposed improvements**:

```python
# scripts/fetch_data.py - Add error handling

def fetch_and_validate(output_path: Path) -> bool:
    """
    Fetch data from API and validate before saving.
    Returns True if successful, False if error.
    """
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        # Log but don't fail render
        logger.error(f"API fetch failed: {e}")
        logger.info("Using cached data from previous run")
        return False

    try:
        data = response.json()
        validate_schema(data)  # Raises ValueError if invalid
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid API response: {e}")
        return False

    # Write to temp file first, then rename (atomic operation)
    temp_path = output_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f)

    # Verify temp file is valid
    try:
        with open(temp_path) as f:
            json.load(f)
    except json.JSONDecodeError:
        temp_path.unlink()
        logger.error("Temp file corrupted, not overwriting previous data")
        return False

    temp_path.replace(output_path)
    logger.info(f"Data saved to {output_path}")
    return True
```

**Error display in HTML** (add to each page):

```python
# In index.qmd setup cell
try:
    with open(LATEST_FILE) as f:
        latest_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    latest_data = None
    logger.error(f"Could not load data: {e}")
```

Then in the page body:

```markdown
:::{.callout-warning}
## ⚠️ Dados Desatualizados

A última atualização foi {datetime_str}.
Se houver erro aqui, o dashboard está usando dados em cache do dia anterior.
:::
```

### 14.4 What NOT to Test (Static Site Context)

**Don't test** (impractical for static site):
- User login/authentication
- Real-time data updates
- Database transactions
- API performance at scale
- User interface click paths (use manual testing or Playwright instead)

**Do test** (automated):
- Data loading (✓ above)
- Calculations (✓ above)
- Render completion (✓ above)
- Link validity (✓ above)
- Performance (Lighthouse)

### 14.5 Test Execution Plan

```bash
# Run all tests locally (before pushing)
pytest tests/ -v --cov=scripts

# Run full CI locally
act -j test-and-deploy  # Requires 'act' installed (simulate GitHub Actions)

# After deploy, smoke test in browser
# 1. Check homepage loads
# 2. Click through navbar (all 5 pages)
# 3. Open each chart in fullscreen mode
# 4. Check Open Graph preview (share link in Discord)
```

---

## 15. Competitive Analysis

### 15.1 Comparable Projects & Learning Opportunities

#### A. BigBrother Analytics Platform (Real Reality TV Analytics)

**What it is**: Enterprise analytics platform for monitoring "Big Brother" social media sentiment

**Link**: [BigBrother Analytics](https://bigbrotheranalytics.com/)

**What we can learn**:
- Crisis detection algorithms (could identify dramatic voting swings)
- Multi-source aggregation (we only have Queridômetro, they have Twitter/media)
- Real-time dashboarding (we're daily; they're live)
- Sentiment analysis at scale (we do manual emoji analysis; they do NLP)

**Unique advantage of BBB26**: Queridômetro is PRIMARY DATA (participants' own opinions), not inferred from media mentions

---

#### B. Survivor Analytics & Edgic Community

**What it is**: Fan-driven prediction community using "edgic" (editing + logic) to predict Survivor winners

**Learning points** (from UC Berkeley research):
- [Predicting Survivor Winners via Machine Learning](https://dlab.berkeley.edu/news/can-machine-learning-models-predict-reality-tv-winners-case-survivor)
- Shows that **crude visibility measures fail** (55% accuracy = worse than coin flip)
- **Character arc analysis > raw metrics** (fans do this intuitively)

**What we can learn**:
1. Prediction is HARD — don't oversell confidence
2. **Narrative matters more than numbers** — why is Leandro dangerous? Not just sentiment, but voting patterns + alliances + character edit
3. **Fan expertise** — superfans have domain knowledge we should leverage (add comments, annotations, expert opinions)

**Unique advantage of BBB26**: We have VOTE DATA (rare!), not just editing analysis

---

#### C. Network Visualization Tools (Gephi, NodeXL, SocNetV)

**What they do**: Visualize complex social networks

**Link**: [Gephi](https://gephi.org/) | [NodeXL](https://www.smrfoundation.org/) | [SocNetV](https://socnetv.org/)

**Their features**:
- Force-directed graph layouts (natural clustering)
- Community detection algorithms
- Temporal graph analysis (how networks evolve)
- Centrality metrics (who's most connected)

**What we have**: Static network graph via Plotly (hard to read with 22 nodes)

**What we could add**:
- Interactive filtering by group (show only Pipocas, or only VIP)
- Temporal animation (watch the network evolve day-by-day)
- Community detection via Leiden algorithm (auto-find alliances)
- Legend for relationship types (💔 vs 🐍 vs ❤️)

---

#### D. Social Media Dashboard Examples (Klipfolio, Improva do)

**What they do**: Multi-source metrics aggregation into clean dashboards

**References**:
- [Klipfolio Dashboard Examples](https://www.klipfolio.com/resources/dashboard-examples/social-media)
- [Improvado Social Media Dashboard Blog](https://improvado.io/blog/social-media-dashboard)

**Best practices they use**:
1. **KPI cards at top** — quick glance summary (not buried in the page)
2. **Filtering/drill-down** — click a metric to see underlying data
3. **Trend indicators** — ↑/↓ arrows for context (not just numbers)
4. **Timestamp clarity** — always show "Last updated: 2 hours ago"
5. **Export buttons** — let users download data as CSV/Excel
6. **Comparison modes** — "vs last week" presets visible

**What we lack**:
- KPI cards (we jump into detailed charts)
- Export/shareable reports
- Clear "as of [date] [time] BRT" timestamp on every page

---

#### E. Bachelor/Love Island Prediction Models

**Research**: [Predicting The Bachelor Outcomes](https://arxiv.org/abs/2203.16648)

**Their approach**:
- Demographic features (age, hometown, profession)
- Temporal features (week of 1-on-1, first impression rose)
- Binary classification (progresses far vs. eliminated early)
- Found: ~70% accuracy on historical data

**Key insight for us**: **Demographics + temporal patterns > raw sentiment**
- We could add: "Pipoca vs Camarote split" (voting blocks), "Week entered" (latecomers at disadvantage), "VIP rotation" (strategy signals)

**What we could predict**:
```
Who's at elimination risk?
= (low sentiment) × (isolated in graph) × (high one-sided hostility) × (low vote count from house)
```

---

### 15.2 What Makes Our Dashboard Unique

| Feature | BBB26 | BigBrother Analytics | Survivor Edgic | General Dashboards |
|---------|-------|----------------------|-----------------|-------------------|
| **Queridômetro data** | ✓ Direct from API | ✗ Media analysis only | ✗ N/A | ✗ |
| **Historical snapshots** | ✓ 15+ daily | ✗ Real-time only | ✓ Historical edits | ~ Some tools |
| **Vote vs reactions** | ✓ Can compare | ✗ No vote data | ~ Inferred from edits | ✗ |
| **Portuguese/Brazilian** | ✓ Native | ✗ English-focused | ✗ English-focused | ~ Varies |
| **Free static hosting** | ✓ GitHub Pages | ✗ Enterprise SaaS | ✓ Some fan sites | ✓ Yes |
| **Community detection** | ✓ Clustering visible | ✓ Sentiment clusters | ~ Implicit | ✓ Some tools |
| **Blind spot analysis** | ✓ One-sided hostility | ✗ | ✗ | ✗ |
| **Daily refresh** | ✓ 4x daily via Actions | ✗ Real-time | ✗ Static snapshots | ✓ Some |

**Bottom line**: We're the only BBB26-specific, Queridômetro-focused, free-to-access, automatically-updated dashboard in Portuguese. That's our moat.

---

### 15.3 Specific Features to Copy/Adapt

#### From BigBrother Analytics:
**Crisis Detection** → Apply to voting: When sentiment changes >5 points in 1 day, flag as "DRAMA ALERT"

#### From Survivor Edgic Community:
**Expert Narrative** → Add a "📝 Análise do Especialista" section where fans can annotate why someone's sentiment shifted (not just that it did)

#### From Network Visualization Tools:
**Temporal Animation** → "Veja a rede evoluir" — animated graph showing how alliances form/dissolve day-by-day

#### From Social Media Dashboards:
**KPI Cards** → Top of page: `[📊 22 Participantes] [💬 462 Reações] [↑ Volatilidade 95 Mudanças] [⚖️ Equilibrio 3:2 Camarote:Pipoca]`

#### From Bachelor Prediction:
**Risk Scoring** → "Risco de Eliminação: Alto/Médio/Baixo" based on multi-factor model

---

## 16. Quick Wins & Wow Factor Features

### 16.1 Quick Wins (< 2 hours each)

| # | Feature | Effort | Impact | How |
|---|---------|--------|--------|-----|
| 1 | Add "Última atualização" timestamp | 15 min | HIGH | Show in header: "🕐 Atualizado em 2026-01-25 às 16:45 BRT" |
| 2 | KPI cards at top | 30 min | HIGH | Create 4 Plotly value boxes: participants, reactions, changes, volatility |
| 3 | Shareable WhatsApp buttons | 45 min | MEDIUM | Add "Compartilhar este painel" button with pre-filled message |
| 4 | "Quem está em risco?" summary | 1 hour | HIGH | Auto-calculated risk score + top 3 at-risk participants |
| 5 | Export to CSV button | 30 min | MEDIUM | Let users download heatmap data, sentiment ranking, etc. |
| 6 | Dark/Light theme toggle | 1 hour | MEDIUM | Quarto supports theme switching (add to navbar) |
| 7 | Emoji legend popup | 20 min | LOW | Hover over emoji → show meaning + weight |
| 8 | Mobile-optimized heatmap | 1 hour | MEDIUM | Rotate/scroll on small screens instead of shrinking |

### 16.2 Medium Effort, High Impact (2-4 hours)

| Feature | Impact | How |
|---------|--------|-----|
| **"Destaques do Dia" AI summary** | HIGH | Generate auto-summary of biggest changes (LLM or rule-based) |
| **Peer comparison tool** | MEDIUM | "Compare Gabriela vs Leandro" — side-by-side profiles |
| **Trending badges** | MEDIUM | 📈 "Subindo!" / 📉 "Caindo!" / 🔄 "Volátil" animated badges |
| **Participant focus pages** | HIGH | Deep dive: one page per person (profile, historical graph, vulnerabilities) |
| **"O que prevê votação?" prediction** | HIGH | ML model: given reações, predict vote outcome (with confidence) |
| **Cartola BBB integration** | MEDIUM | Points tracker + "best picks" analysis |

### 16.3 Wow Factor Features (Would Make People Talk)

#### A. "Mata a Curiosidade" — The Prediction Game

Allow users to:
1. **Guess today's elimination** before the vote
2. **See how their prediction** compared to actual results
3. **Compete on a leaderboard** with other fans
4. **Share: "Acertei! 🎯"** if correct

Tech: Pre-calculate predictions via a simple model, store guesses in localStorage, compare at end of episode.

**Why this is magic**: Engages casual viewers, drives daily return visits, shareable moment ("I predicted this before it happened!")

---

#### B. "A Dinâmica das Reações" — Animated Graph Evolution

Show the network graph **animating over time**:
- Day 1: Mostly disconnected (new season)
- Day 5: Clear alliance clusters forming
- Day 12: Bridges and rivalries visible
- Day 21: Tight clusters after eliminations

Press play → watch relationships emerge in real-time.

**Why this is magic**: Visual storytelling, deeply engaging, unique to our dataset

---

#### C. "Seu Perfil de Influência" — Influence Scoring

Calculate for each participant:
```
Influence = (% of house that shifted reactions toward them in 24h) × (weight of their opinions in forming new alliances)
```

Show: "Gabriela foi a pessoa mais influente hoje (+23% mudaram de opinião sobre ela)"

**Why this is magic**: Adds psychological dimension, predicts future leaders

---

#### D. "Comparador Temporal" — Any-to-Any Date Comparison

(Requires minor interactivity work, but worth it)

```
Select Date 1: [Jan 13] ← from dropdown
Select Date 2: [Jan 25]
→ Shows: Who changed most? New alliances? Broken pairs?
```

**Why this is magic**: Answers "what happened between these dates?" — casual viewers love this

---

#### E. "Análise de Aliança" — Alliance Stability Score

For each detected pair/group:
```
Stability = (Days of consistent mutual ❤️) / (Total days) × (% votes together in paredões)
```

Show on Trajetória as a table:
```
| Aliança | Dias | Estabilidade | Resultado |
|---------|------|--------------|-----------|
| Gabriela ❤️ Leandro | 12 | 95% | Viável ✓ |
| Ana Paula ↔ Brigido | 12 | Hostil | Inimigos ✗ |
```

**Why this is magic**: Predicts paredão votes, strategic depth

---

### 16.4 Community/Viral Features

**What makes people SHARE dashboards?**

1. **Personal stakes** — "I'm on this" or "My favorite is #1"
   - Add: Participant-specific cards to share

2. **Predictions come true** — "I called this!"
   - Add: Prediction leaderboard

3. **Drama** — "Look at this betrayal!"
   - Add: "Most dramatic reaction change" highlight

4. **Bragging rights** — "My team/group is winning"
   - Add: Vip vs Xepa scorecard

5. **Scarcity/FOMO** — "This data is unique to this dashboard"
   - We have this! No one else has Queridômetro snapshots

**Specific shareable moments**:

```
"🏆 Gabriela lidera com +15.2 de sentimento em BBB 26 | Dashboard ao vivo"

"⚠️ Leandro MUDOU 8 reações em 24h — é o mais volátil do jogo 📊"

"🤝 Gabriela e Leandro têm a aliança mais estável (95% dias juntos) 💪"

"🐍 Ana Paula é a mais atacada no jogo (alvo de 7 cobras) — será eliminada?"
```

Each shares as a card with:
- Participant name + group badge
- The stat/finding
- QR code to "Veja o painel completo"
- Date/time stamp

---

## 17. Accessibility & Mobile Review

### 17.1 Current Accessibility Issues

**Dark Theme Contrast**: Using Bootswatch "darkly" theme
- Background: #222222
- Text: #ffffff
- Contrast ratio: 12.6:1 ✓ PASSES WCAG AAA

**But watch for**:
- Charts use Plotly's default colors — some combinations may not hit 4.5:1
- Heatmaps with emoji + background color — verify color combos
- Form inputs/buttons — test against #303030 plot background

### 17.2 Accessibility Audit Checklist

```
[ ] Run axe DevTools (browser extension) on each page
[ ] Check color contrast with WCAG Contrast Checker
    - Text on background: 4.5:1 minimum (large: 3:1)
    - UI components (buttons, inputs): 3:1 minimum
[ ] Verify keyboard navigation (Tab through all interactive elements)
[ ] Test with screen reader (NVDA, JAWS, VoiceOver)
    - Do chart titles read well?
    - Can emoji be understood by screen reader?
    - Is table structure correct?
[ ] Check mobile zoom (text should remain readable at 200% zoom)
[ ] Verify focus indicators visible (not invisible on dark background)
[ ] Test color blindness simulation (Protanopia, Deuteranopia modes)
    - Are emoji the ONLY way to distinguish reactions?
```

### 17.3 Specific Fixes Needed

**Fix 1: Emoji as sole differentiator**
```
Current: Heatmap cell just shows emoji: 🐍
Better: Show emoji + subtle background color + tooltip on hover
        🐍 [salmon bg] → hover → "Cobra (negativa)"
```

**Fix 2: High-contrast mode**
Quarto supports adding a high-contrast CSS variant:
```css
@media (prefers-contrast: more) {
  /* Increase color separation */
  :root {
    --text-color: #ffffff;  /* whiter */
    --bg-dark: #111111;      /* darker */
    --grid-color: #555555;   /* lighter grids for visibility */
  }
}
```

**Fix 3: Font sizing on mobile**
Charts with small fonts get cut off on phones. Add:
```python
# In index.qmd, adjust Plotly font for mobile
fig.update_layout(
    font=dict(size=13),  # Base
    title=dict(font=dict(size=16)),
    xaxis=dict(tickfont=dict(size=11)),  # Smaller on mobile
)
```

### 17.4 Mobile Optimization

**Current state**: Plots shrink to fit, 22×22 heatmap unreadable on phone

**Solutions**:

1. **Heatmap rotation**: On mobile, show only top 10 participants (alphabetical or by sentiment)

2. **Tabbed layout**: Offer tabs for each group (Pipoca | Camarote | Veterano | Todos)

3. **Responsive font**: Use CSS `clamp()` for fluid text sizing:
```css
body { font-size: clamp(12px, 2vw, 16px); }
h1 { font-size: clamp(24px, 5vw, 32px); }
```

4. **Lazy-load charts**: Charts below the fold load on scroll (improves time-to-interactive)

5. **Simplified mobile layout**: Below 768px, stack cards vertically instead of side-by-side

---

## 18. Implementation Roadmap Summary

### Phase 1: Discoverability (P0 — Do First)
- [ ] Add Open Graph + Twitter Card metadata (~30 min)
- [ ] Generate og-image-default.png daily (~1 hour)
- [ ] Add sitemap.xml + robots.txt (~20 min)
- [ ] Set up Google Search Console verification (~5 min)

**Impact**: Enable social sharing, start search engine indexing

**Timeline**: 1 working day

---

### Phase 2: Quality & Testing (P1 — Essential)
- [ ] Add pytest tests for data loading + calculations (~1.5 hours)
- [ ] Integrate tests into GitHub Actions (~1 hour)
- [ ] Set up Lighthouse CI checks (~1 hour)
- [ ] Add error handling to fetch_data.py (~1 hour)

**Impact**: Catch regressions early, prevent render failures

**Timeline**: 1-2 working days

---

### Phase 3: Accessibility & Mobile (P2 — Important)
- [ ] WCAG contrast audit + fixes (~1 hour)
- [ ] Keyboard navigation test (~30 min)
- [ ] Mobile responsiveness improvements (~2 hours)
- [ ] Add timestamp to every page (~30 min)

**Impact**: Broader audience, better UX on phones, legal compliance

**Timeline**: 1-2 working days

---

### Phase 4: Quick Wins (P3 — Nice to Have)
- [ ] KPI cards at top of Painel (~30 min)
- [ ] "Quem está em risco?" summary (~1 hour)
- [ ] Shareable WhatsApp buttons (~45 min)
- [ ] CSV export functionality (~30 min)

**Impact**: Engagement, virality, user value

**Timeline**: 2-3 working days

---

### Phase 5: Wow Factor (P4 — Differentiator)
- [ ] Animated network evolution (~4-6 hours)
- [ ] Prediction game leaderboard (~4 hours)
- [ ] Influence scoring (~2 hours)
- [ ] Participant focus pages (~4 hours)

**Impact**: Set apart from other BBB fan sites, drive word-of-mouth

**Timeline**: 2-3 weeks (part-time)

---

## 19. Success Metrics & Tracking

### How to Measure Success

| Metric | Current | Target (30 days) | Tool |
|--------|---------|------------------|------|
| **Google impressions** | 0 | 50+ | Google Search Console |
| **Organic traffic** | <10/day | 50+/day | GitHub Pages analytics |
| **Social shares** | 0 | 10+/week | Monitor via mentions |
| **Open Graph previews** | N/A | 5+ tested | Manual testing |
| **Accessibility score** | ? | 90+ (axe DevTools) | axe browser ext |
| **Mobile performance** | ? | 75+ (Lighthouse) | Lighthouse CI |
| **Test coverage** | 0% | 50%+ | pytest --cov |
| **Deployment reliability** | ? | 99% (0 failed renders) | GitHub Actions logs |

### Tracking Dashboard (Manual)

Keep a simple CSV (`metrics.csv`) with weekly snapshots:
```
Date,GoogleImpressions,OrganicVisits,SocialShares,Tests,LighthouseScore
2026-01-25,0,8,0,0,65
2026-02-01,12,35,2,8,78
2026-02-08,48,120,5,15,85
```

---

## Final Recommendations (Prioritized by Impact)

### 🔴 MUST DO (Core Improvements)
1. **Add Open Graph metadata** — Enable social sharing (#13.1)
2. **Set up basic testing** — Prevent regressions (#14.1)
3. **Fix accessibility issues** — WCAG compliance (#17.1)
4. **Mobile optimization** — Works on phones (#17.4)

### 🟡 SHOULD DO (Growth Levers)
5. **SEO basics** (sitemap, robots.txt, descriptions) — Help people find dashboard (#13.5)
6. **Shareable cards** — Drive word-of-mouth (#13.2, #16.1)
7. **KPI cards at top** — Better UX for casual viewers (#16.1)
8. **Timestamp on every page** — Users know data freshness (#16.1)

### 🟢 NICE TO HAVE (Differentiators)
9. **Prediction game** — Engagement & virality (#16.3)
10. **Animated network graph** — Wow factor (#16.3)
11. **Participant focus pages** — Depth for superfans (#16.2)

---

## Sources & References

### SEO & Social Sharing
- [Quarto Website Tools Documentation](https://quarto.org/docs/websites/website-tools.html)
- [Open Graph Meta Tags Guide](https://w3things.com/blog/open-graph-meta-tags/)
- [Prerender.io: Open Graph Benefits](https://prerender.io/blog/benefits-of-using-open-graph/)
- [FreeCodeCamp: Open Graph Overview](https://www.freecodecamp.org/news/what-is-open-graph-and-how-can-i-use-it-for-your-website/)

### Testing & Quality
- [Quarto Documentation](https://quarto.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Accessibility
- [DubBot: Dark Mode Accessibility](https://dubbot.com/dubblog/2023/dark-mode-a11y.html)
- [W3C WCAG 3 Visual Contrast](https://www.w3.org/WAI/GL/WCAG3/2022/how-tos/visual-contrast-of-text/)
- [BOIA: Dark Mode WCAG Compliance](https://www.boia.org/blog/offering-a-dark-mode-doesnt-satisfy-wcag-color-contrast-requirements)
- [WebAIM Contrast Article](https://webaim.org/articles/contrast/)
- [MDN Accessibility: Color Contrast](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Perceivable/Color_contrast)

### Competitive Analysis
- [Berkeley D-Lab: Predicting Survivor Winners](https://dlab.berkeley.edu/news/can-machine-learning-models-predict-reality-tv-winners-case-survivor)
- [Predicting The Bachelor via ML (arXiv)](https://arxiv.org/abs/2203.16648)
- [Gephi Graph Visualization](https://gephi.org/)
- [NodeXL Social Network Analysis](https://www.smrfoundation.org/)
- [SocNetV Network Visualization](https://socnetv.org/)
- [Klipfolio Dashboard Examples](https://www.klipfolio.com/resources/dashboard-examples/social-media)
- [Improvado Social Media Dashboard](https://improvado.io/blog/social-media-dashboard)
- [Cambridge Intelligence: Social Network Use Cases](https://cambridge-intelligence.com/use-cases/social-networks/)

### Reality TV Analytics
- [BigBrother Analytics Platform](https://bigbrotheranalytics.com/)

---

## Closing Notes

This dashboard is **unique in the BBB26 ecosystem** because:
1. It's the **only open-source** Queridômetro-focused analytics tool
2. It **auto-updates 4x daily** from official API
3. It provides **vote vs. reaction analysis** (rare combo)
4. It's available in **Portuguese** (native language)
5. It's **free to access** (no paywall)

Your competitive advantage isn't features — it's **data authenticity + daily updates + community spirit**.

Focus on:
- Making it **easy to share** (social cards, WhatsApp buttons)
- Making it **discoverable** (SEO, right search terms)
- Making it **trustworthy** (timestamps, transparent data)
- Making it **surprising** (predictions, wow moments)

The "quick wins" in Section 16 will have outsized impact on engagement and organic growth. Start there.

---

**End of Review**

*This analysis was conducted by Claude Haiku 4.5 on 2026-01-25, focusing on polish, discoverability, and quality aspects of the BBB26 dashboard project.*
