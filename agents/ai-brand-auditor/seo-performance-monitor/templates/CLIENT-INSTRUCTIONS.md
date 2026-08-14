# Requesting a Search Console export from a client

Copy the block below into an email. It asks for the one file this toolchain
needs, in the format it expects, without requiring the client to give you
access to anything.

---

**Subject: Quick data pull for the search analysis**

Hi [name],

To run the search analysis I mentioned, I need one export from your Google
Search Console. It takes about a minute and doesn't require giving me access
to any of your accounts.

1. Go to [search.google.com/search-console](https://search.google.com/search-console)
   and select **[their domain]**
2. Click **Performance** in the left sidebar
3. At the top, set the date range to **Last 3 months** (or Last 6 months if
   it's offered — more history means I can show you what's trending down, not
   just where things stand today)
4. Click **Export** in the top-right → **Download CSV**
5. That downloads a ZIP. Send me the whole ZIP — no need to open it.

If you're able to do it twice, a second export set to the *previous* 3 months
lets me show change over time, which is usually where the useful findings are.

Thanks!

---

## What arrives, and what to do with it

The ZIP contains several CSVs. The two that matter:

| File | Contains | Used for |
|---|---|---|
| `Queries.csv` | Search terms people typed | Striking distance, CTR shortfalls, decay |
| `Pages.csv` | URLs that appeared in results | Page-level performance |

The others (`Countries.csv`, `Devices.csv`, `Dates.csv`, `Filters.csv`) are
ignored — harmless to receive.

Run the analysis on `Queries.csv`:

```bash
python3 scripts/analyze_gsc.py Queries.csv --site clientsite.com --out runs/client
```

With a second period:

```bash
python3 scripts/analyze_gsc.py Queries.csv --previous Queries-prev.csv --site clientsite.com --out runs/client
```

## What the columns mean

`Queries-EXAMPLE.csv` in this folder is a realistic sample. Google always
produces these five columns, in this order:

| Column | Meaning | Why it matters |
|---|---|---|
| **Top queries** | What someone typed into Google | The demand itself |
| **Clicks** | Times someone clicked through to the site | Actual traffic earned |
| **Impressions** | Times a page appeared in results | Demand the site is visible for |
| **CTR** | Clicks ÷ Impressions | How compelling the listing is |
| **Position** | Average ranking | Where it sits on the page |

The interesting rows are the mismatches. In the example file:

- `patient scheduling software` — 9,240 impressions, 86 clicks, position 11.7.
  Big demand, ranking just off page one. **Striking distance**: rank 11 → 8
  crosses onto page one and the clicks step up sharply.
- `appointment reminder software` — 5,120 impressions, 0.33% CTR at position
  16.4. Buried; needs ranking work, not a title tweak.
- `acme patient scheduling` — 18.9% CTR at position 1.4. That's branded
  traffic. It looks like a win but reflects people who already knew the name.
  Always separate branded from non-branded before judging performance.

## An honest limitation

Google's standard export gives `Queries.csv` and `Pages.csv` as **separate**
files — queries have no page attached, pages have no query. So:

| Analysis | Works from a standard export? |
|---|---|
| Striking distance | ✅ |
| CTR shortfalls | ✅ |
| Decay (with 2 periods) | ✅ |
| **Cannibalization** | ❌ needs query+page pairs |

Cannibalization detection needs both dimensions on the same row, which the UI
export doesn't produce. It requires the Search Console API, or filtering
page-by-page in the UI and exporting each — rarely worth it. The analyzer
detects this automatically and says so rather than silently skipping.

If a client grants Search Console access directly (Settings → Users and
permissions → Add user, **Full** or **Restricted**), the API route opens up and
cannibalization becomes available.
