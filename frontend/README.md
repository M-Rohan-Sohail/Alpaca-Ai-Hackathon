# Alpaca Terminal — Frontend

Frontend for the **Alpaca AI Hackathon 2026: Agentic Options Trading Terminal**,
built against the Frontend Design & UX Specification. This is a
visualization/interaction layer only — it never computes options math, risk
budgets, P&L, or Alpaca payloads; all of that is expected from the backend.

Stack: Next.js (App Router) + TypeScript + Tailwind CSS v4 + TanStack Query +
Recharts, dark-mode-only "Bloomberg terminal" aesthetic.

## Getting started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — it redirects to `/dashboard`.

## Pages

- `/dashboard` — top-level KPIs, pipeline activity feed, risk utilization, compact active positions
- `/pipeline` — Pipeline Explorer: candidate list + 6-stage vertical stepper (Data Processing → Market/News → Options → Decision Agent → Risk Engine → Execution)
- `/positions` — open positions with expandable multi-leg rows, payoff chart, and manual Force Close (with confirmation modal)
- `/journal` — historical trade ledger with filters (symbol, strategy, status, exit reason)
- `/risk-dashboard` — account-wide risk capacity + most recent Risk Engine decision breakdown

## Backend integration

The real backend is a FastAPI wrapper (not yet built — see Section M of the
spec) that normalizes local batch JSON files into the REST contract below.
Until it exists, `src/app/api/*` contains Next.js route handlers that mock
those exact endpoints (backed by `src/lib/mock/store.ts`) so the app is fully
demoable standalone:

- `GET /api/dashboard`
- `GET /api/pipeline/latest`
- `GET /api/positions`
- `GET /api/journal`
- `POST /api/execute/close`

To point the frontend at a real backend instead, set
`NEXT_PUBLIC_API_BASE_URL` (see `.env.local.example`) — no other frontend
code needs to change, since `src/lib/api/client.ts` and the TanStack Query
hooks in `src/lib/api/hooks.ts` already call these exact paths. You can then
delete `src/app/api/*` and `src/lib/mock/`.

Response shapes are defined in `src/lib/api/types.ts`, mirroring Section F
(API Contract) and Section G (JSON UI Mapping Matrix) of the spec.

## Firebase (pipeline submission)

`/pipeline` has a "Submit a ticker for processing" box. Submitting a symbol
calls `POST /api/pipeline/submit`
([src/app/api/pipeline/submit/route.ts](src/app/api/pipeline/submit/route.ts)),
which:

1. Writes the submission to a Firestore collection (`pipeline_submissions`)
   via the Firebase Admin SDK.
2. Processes it (currently: checks whether the symbol already has a mock
   pipeline result; a real backend would run its own analysis here).
3. Deletes the Firestore document — it's a transient inbox, not a permanent
   store of trading data.

### One-time setup

1. Go to the [Firebase Console](https://console.firebase.google.com/), click
   **Add project**, and follow the prompts (Google Analytics is optional).
2. In the new project, go to **Build > Firestore Database > Create database**
   (any region, start in production mode is fine — no client-side rules are
   needed since only the server touches Firestore).
3. Go to **Project settings (gear icon) > Service accounts > Generate new
   private key**. This downloads a JSON file — keep it secret, never commit
   it.
4. Copy `project_id`, `client_email`, and `private_key` from that JSON into
   your local `.env.local` (copy `.env.local.example` first):
   ```
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   ```
   Keep the `\n` escapes and quotes around `FIREBASE_PRIVATE_KEY` exactly as
   they appear in the downloaded JSON.
5. Restart `npm run dev` after editing `.env.local`.

## Deployment (Vercel)

1. Push this repo to GitHub (or run `npx vercel` directly from this folder —
   it doesn't require GitHub).
2. On [vercel.com](https://vercel.com), **Add New > Project**, import the
   repo (or, via CLI: `npx vercel login` then `npx vercel --prod`).
3. In the Vercel project's **Settings > Environment Variables**, add
   `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, and `FIREBASE_PRIVATE_KEY`
   (same values as `.env.local`; paste the private key including the `\n`
   escapes, in quotes). Add `NEXT_PUBLIC_API_BASE_URL` too if pointing at a
   real backend.
4. Deploy. Vercel gives you a `https://<project>.vercel.app` URL — share that
   with your team.

## Design system

Tokens live in `src/app/globals.css`: dark background (`#09090B`), card
surface (`#18181B`), Inter for text, JetBrains Mono for numbers/tickers/IDs,
and semantic colors for profit/loss/warning/info. Missing data always
renders as `N/A`, never `0` (see `formatCurrency`/`formatPercent` in
`src/lib/utils.ts`).

The Risk Engine is treated as the absolute authority throughout: there is no
"override" or "execute anyway" control anywhere in the client, and a Risk
Engine rejection is always rendered with an explicit red
"REJECTED BY RISK ENGINE" state (see `RiskAssessmentCard`).
