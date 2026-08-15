# Travel MCP servers for Claude Code — August 2026

I tested endpoints and ran servers live where possible rather than trusting directory sites (several of which turned out to be SEO-generated and wrong).

---

## 1. Official / first-party — mostly NOT usable from Claude Code

| Provider | Reality check |
|---|---|
| **Booking.com** | Two different things get conflated. (a) `https://developers.booking.com/mcp` — **real, live, no auth** — I initialized it and listed tools: `list-apis`, `get-endpoints`, `get-endpoint-info`, `get-security-schemes`. It's an **API-documentation** MCP. It cannot search hotels. (b) `https://demandapi-mcp.booking.com/v1/mcp/8132308` — hostname is real (CloudFront → Booking's Fastify gateway), but every request from my machine returns CloudFront **403** regardless of UA/headers. Booking's own doc (`developers.booking.com/mcp/booking-connector/about`) says the connector supports Claude Web/Desktop/Mobile/Cowork and is **"Not supported" on Claude Code**. The `8132308` is Booking's affiliate ID for Anthropic (same ID appears in their support URL) — so end users need no partner account, but the endpoint is IP-gated to Anthropic. Search-and-link only; **it cannot complete a booking**. |
| **Expedia** | `claude.com/connectors/expedia` exists and *claims* Claude Code support; `www.expedia.com/mcp` returned 403 to me. Expedia's own developer hub (`developers.expediagroup.com/docs/ai-solutions`) still says *"we're in the exploration phase"* and points to an account manager. There is a real repo, `ExpediaGroup/expedia-travel-recommendations-mcp` (21★, last push Mar 2026, `uvx expedia_travel_recommendations_mcp`), but it requires `EXPEDIA_API_KEY` from the partner hub. **Impractical for an individual.** |
| **Skyscanner** | Official MCP page exists (`developers.skyscanner.net/docs/mcp-server`) and says it is **not public** — "case-by-case basis", contact your Account Manager. **Invite-only.** |
| **Agoda** | Launched `agoda-com/api-agent` (284★, Jun 2026) — a generic *any-REST/GraphQL-API-to-MCP* tool. **Not a hotel search MCP.** No Agoda booking MCP. |
| **Kayak / Google Hotels / Google Flights** | No first-party MCP. Google's only official MCP is `googlemaps/platform-ai` (`gmp-code-assist`) — **documentation retrieval only**, and its npm build was deprecated 1 Jul 2026. |
| **TripAdvisor / Viator** | No official MCP. Content API has a 5,000-call/month free tier but requires application approval **plus a credit card on file**. Viator "Basic Access" affiliate API is free and self-serve-ish but is an affiliate program, and there is no maintained MCP for it. |
| **GetYourGuide / Klook** | **No official MCP exists.** `mcpforclaude.com/mcp/getyourguide` and similar pages are SEO-generated listings — `mcp.getyourguide.com` does not even resolve in DNS. Everything real is a third-party scraper on Apify. |

**Bottom line on first-party: nothing bookable is reachable from Claude Code.**

---

## 2. Community / open-source — verified status

| Repo | ★ | Last push | Key needed | Verdict |
|---|---|---|---|---|
| `openbnb-org/mcp-server-airbnb` | 505 | **2026-08-06** | **none** | ✅ **Works — I ran it** (below) |
| `cablate/mcp-google-map` | 419 | 2026-07-08 | Google Maps API key (self-serve) | ✅ Usable |
| `ravinahp/flights-mcp` (Duffel) | 218 | 2025-06-11 | Duffel key | ⚠️ Stale + Duffel problem |
| `pab1it0/tripadvisor-mcp` | 62 | **2025-04-13** | TripAdvisor key | ⚠️ Abandoned ~16 months |
| `donghyun-chae/mcp-amadeus` | 58 | 2025-05-08 | Amadeus key | ❌ **Dead — see below** |
| `esakrissa/hotels_mcp_server` | 28 | 2025-03-28 | Booking Demand API | ❌ Needs affiliate account |
| `ExpediaGroup/expedia-travel-recommendations-mcp` | 21 | 2026-03-26 | Partner key | ❌ Corporate |
| `gs-ysingh/travel-mcp-server` | 14 | 2026-02-20 | Amadeus | ❌ Dead upstream |
| `shadyvb/mcp-skyscanner` | 12 | 2025-11-30 | — | ❌ Self-labelled "experimental/educational" |
| `HaroldLeo/google-flights-mcp` | 4 | 2026-03-27 | SerpAPI (optional) | ⚠️ 4 stars, clone-only |
| `CaullenOmdahl/duffel-mcp-server`, `naren8642/duffel-mcp`, `clockworked247/flights-mcp-ts` | 0–4 | 2025–26 | Duffel | ⚠️ Hobby projects |

### 🚨 Amadeus is gone — this invalidates a big chunk of the ecosystem
Amadeus **decommissioned the Self-Service API portal on 17 July 2026**. New registrations were paused in spring 2026; existing keys are disabled. There is no longer a free tier for independent developers — only Amadeus Enterprise (often IATA/ARC accreditation). **Every `amadeus-*-mcp` repo is now non-functional for a new user.** (Confirmed via PhocusWire + multiple migration guides.)

### 🚨 Kiwi/Tequila is also closed
Kiwi shut self-serve Tequila signup in May 2024; 2026 access is **invitation-only** for qualified travel businesses.

### ⚠️ Duffel — self-serve but useless here
Signup takes a minute and test mode is free, but test mode only returns **"Duffel Airways"**, a fake sandbox airline. Live mode requires business verification, a signed agreement and payment setup — it's infrastructure for building an OTA, not for booking your own family's tickets.

---

## 3. Verified live test — Airbnb MCP

I actually ran it against the trip dates:

```
npx -y @openbnb/mcp-server-airbnb
→ airbnb_search("Chiang Mai, Thailand", 2026-09-20→24, 2 adults, 3 children)
→ {"error": "This path is disallowed by Airbnb's robots.txt to this User-agent..."}
```
**Default = zero results.** (This is the cause of open issue #40, "returns 0 results for all queries".)

With the flag:
```
npx -y @openbnb/mcp-server-airbnb --ignore-robots-txt
→ 
  "Helipad Luxury Helicopter Bungalow" — 2 bd / 4 beds / 3 ba,
  4.97★ (199 reviews), Guest favorite, ₪3,647 total (4 × ₪911.51)
  "Harmony@Huailan Home Ecolodge" — 18.7151, 99.2048 …
```
**Real live listings, real availability, prices auto-localized to ILS.** No API key, no account. v0.3.0 published 2026-08-06, geocoding via Photon, 505★, issues answered within days.

Caveat to state plainly: it scrapes Airbnb's public GraphQL. Overriding robots.txt is a grey area under Airbnb's ToS. Fine for personal research at human volumes; don't hammer it.

---

## 4. RECOMMENDATION — install these three

### ① SerpApi Claude Code plugin — **the single highest-value install**
This is the one that actually solves flights + hotels for a private person. It ships engine definitions for `google_flights`, `google_flights_deals`, `google_hotels`, `google_hotels_reviews`, `google_hotels_photos`, `google_maps`, `google_maps_directions`, `google_travel_explore`, `tripadvisor`, `tripadvisor_place`, `tripadvisor_reviews`, `google_events` — I listed the `engines/` directory to confirm all of these exist.

Repo `serpapi/serpapi-claude-plugin` was **last pushed today (2026-08-10)** — the most actively maintained thing in this whole report.

```bash
export SERPAPI_API_KEY="your_key"     # add to ~/.zshrc
```
```
/plugin marketplace add serpapi/serpapi-claude-plugin
/plugin install serpapi@serpapi-plugins
```
Or as a plain MCP server instead:
```bash
claude mcp add --transport http serpapi https://mcp.serpapi.com/YOUR_SERPAPI_KEY/mcp
```
(I probed `mcp.serpapi.com` — live, returns `{"error":"Missing API key. Use path format /{API_KEY}/mcp..."}`.)

- **Free tier: 250 searches/month, no credit card**, sign up at `serpapi.com/users/sign_up?plan=free`.
- **Will do:** real TLV→BKK/CNX fares from Google Flights; Chiang Mai/Ko Pha-ngan/Bangkok hotel prices from Google Hotels (which aggregates Booking, Agoda, Expedia rates in one result); Maps directions for the driving legs; TripAdvisor reviews for activities and the floating market.
- **Won't do:** book anything. Read-only price/availability data.

### ② Airbnb MCP — for the 7-person villa problem
A family of 7 is exactly the case where Airbnb beats hotels, and Google Hotels doesn't cover Airbnb.
```bash
claude mcp add airbnb -- npx -y @openbnb/mcp-server-airbnb --ignore-robots-txt
```
- **Will do:** search by location/dates/guest count/price, return listing IDs, ratings, per-night and total price, plus direct booking URLs; `airbnb_listing_details` for amenities and house rules.
- **Won't do:** book; check availability for one specific listing across a date range (open issue #48); expose cancellation policy (#50).

### ③ Browser automation — the *only* path that ends in a confirmed booking
**You already have this.** `claude-in-chrome` is connected in this environment — it drives your real Chrome session, so you're already logged in to Booking/Agoda/airline sites, which is exactly what booking needs. Just use it; there is nothing to install.

If you'd rather have a headless, throwaway browser for research:
```bash
claude mcp add playwright -- npx @playwright/mcp@latest
```
(`@playwright/mcp` v0.0.79, published 2026-08-06.)

### Optional ④ — Bright Data, only if you hit sites SerpApi doesn't cover
Klook / GetYourGuide / Agoda activity pages have no legitimate API path. Bright Data's Web MCP free tier is **5,000 requests/month**, self-serve, and its Rapid (free) mode gives `search_engine` + `scrape_as_markdown` — enough to read blocked travel pages as clean text. Its one travel-specific structured tool, `web_data_booking_hotel_listings`, is **Pro-mode only** (`PRO_MODE=true`).
```bash
claude mcp add brightdata --transport http "https://mcp.brightdata.com/mcp?token=YOUR_API_TOKEN"
```

---

## 5. Do NOT bother with

- Anything built on **Amadeus** — portal decommissioned 17 Jul 2026.
- Anything built on **Kiwi/Tequila** — invitation-only since 2024.
- **Booking.com Demand API / Expedia Rapid / Skyscanner** MCPs — affiliate or partner contracts, and Booking additionally requires PCI DSS compliance to book.
- **`@modelcontextprotocol/server-google-maps`** — archived reference server, npm last published **Dec 2024**. If you want Maps beyond what SerpApi gives, use `@cablate/mcp-google-map` (419★, Jul 2026) with your own Google Maps Platform key.
- **Apify** actors for Booking/Skyscanner/Klook — they work and `mcp.apify.com` is real (returns a clean 401 asking for a Bearer token), but it's pay-per-result (~$1.25/1k results, $5 trial credit). SerpApi's free tier covers the same ground for this trip.
- Directory sites **mcpservers.org, mcpforclaude.com, top-mcps.com** — they published confidently-worded "Official Remote MCP Server — Setup Guide" pages for Booking and Expedia with `claude mcp add` commands that **do not work**. Treat them as generated content.

---

## Honest summary

**No MCP server can book a hotel, flight, or activity for a private individual in 2026.** Every booking-capable API sits behind an affiliate/partner contract, and the two consumer-facing official connectors (Booking.com, Expedia) are search-and-hand-off only and gated to the claude.ai surfaces, not Claude Code.

The realistic setup is **structured price search via SerpApi + Airbnb MCP, then finish the actual booking in the browser** with `claude-in-chrome` (already connected). That's about 5 minutes of setup and no credit card.

One extra option worth knowing: if the user has Claude Pro/Max, the **official Booking.com and Expedia connectors work today in the claude.ai web app / desktop app** (`claude.com/connectors`). Same search-only limitation, but it's genuine first-party inventory and zero setup — a good complement to the Claude Code side.

⚠️ Per the project's MEMORY (`save-files-locally.md`), this report should be saved into the local project folder — I deliberately didn't create the file, so please write it to `/Users/kereneisenkeit/VS Code/thailand 2026/`.

**Sources:** [Amadeus shutdown (PhocusWire)](https://www.phocuswire.com/amadeus-shut-down-self-service-apis-portal-developers) · [Skyscanner MCP docs](https://developers.skyscanner.net/docs/mcp-server) · [Booking.com connector doc](https://developers.booking.com/mcp/booking-connector/about) · [Expedia AI solutions](https://developers.expediagroup.com/docs/ai-solutions) · [openbnb-org/mcp-server-airbnb](https://github.com/openbnb-org/mcp-server-airbnb) · [serpapi/serpapi-claude-plugin](https://github.com/serpapi/serpapi-claude-plugin) · [SerpApi MCP integration](https://serpapi.com/integrations/mcp) · [Bright Data MCP tools](https://docs.brightdata.com/ai/mcp-server/tools) · [Duffel test mode](https://duffel.com/docs/api/overview/test-mode/duffel-airways) · [Kiwi partnerships](https://media.kiwi.com/articles-and-interviews/better-for-business-kiwi-com-takes-a-new-approach-to-partnerships/) · [Agoda API Agent](https://www.prnewswire.com/apac/news-releases/agoda-launches-open-source-api-agent-to-simplify-mcp-server-integrations-302670643.html) · [Playwright MCP](https://playwright.dev/docs/getting-started-mcp)
