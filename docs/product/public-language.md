# Public language

A short reference for anyone writing public pages. Product truth comes first: describe what exists today, and label anything that doesn't.

## What Synaptiq is

A research and academic collaboration platform. It starts from a research question:
1. what expertise the question needs;
2. who has that expertise, and the evidence why;
3. inviting them;
4. a team and a shared workspace;
5. the outputs: manuscripts, grant applications, the research record.

AI is optional help inside parts of that work. It is not the product.

Professional expertise counts as well as academic: clinical, policy, engineering, data and other practice.

## Canonical names

Use these exact names; the app uses the same ones.

| Name | What it is | Plan |
|---|---|---|
| Academic Passport | A person's research identity: research areas, methods, professional expertise, what they're open to, ORCID record; declared, connected and verified details marked separately | Free |
| Public research page | The public view of a Passport, with only the sections the member turns on | Free |
| Research Need | A research problem written as what it requires: fields, methods, setting | Pro |
| Research network / discovery | Finding members whose Passports fit, with the evidence | Pro |
| Collaboration request | An invitation the recipient accepts or declines | Pro |
| Team Builder | Turns a need into roles and fills them from discovery | Pro |
| Project, workspace | Where the team works | Pro |
| Journal, Conference and Grant discovery | Finding venues and funding | Pro |
| AI Research Assistant | Open questions about your work | Pro |
| Manuscript Copilot | Section-by-section help inside a manuscript | Pro |
| Teaching Hub | Lesson plans, assessments, teaching workspaces | Pro |
| Publication tracking, Research analytics | | Pro |
| Collaboration Intelligence | | Pro Advanced |
| Impact Dashboard, Citation Monitoring | | Pro Advanced |
| AI Credits | The unit for AI actions; each has a fixed cost shown before it runs | Free 0 · Pro 200/month · Pro Advanced 750/month |
| Institutional | Organisation-level: approved membership, departments, directory, admin roles | Custom, Contact Sales |

## Plans

- **Free:** be visible (Passport, public research page, ORCID, can be found by Pro members).
- **Pro:** participate and collaborate.
- **Pro Advanced:** deeper analysis and impact.
- **Institutional:** organisation-level context. It is not "the biggest individual plan", and an individual plan never grants institution access.

Prices and entitlements come from `backend/plans_catalogue.py` and the Pricing page. Online purchase is not open yet; say so wherever a paid plan is offered.

## Calls to action

| Role | Label | Destination |
|---|---|---|
| Primary | **Start Free** | `/register` (shows that sign-ups are paused while that is true) |
| Secondary | Explore the Platform / See how it works | |
| Contextual | Explore Pricing, Contact Sales (`/for-institutions#inquiry`), Explore Research, Explore AI Workspace | |

Avoid: Get Started, Join Now, Try Synaptiq, Start Today.

## Don't write

- **Internal terms:** matcher, router, endpoint, MongoDB, pipeline, feature flag, entitlement keys, Stripe price IDs, `pro_researcher`.
- **Empty claims:** empower, unlock, revolutionise, seamless, supercharge, transform your research, next-generation, cutting-edge, world-class, future of research.
- **Unverified numbers:** counts, testimonials, logos, uptime or response times, article counts.
- **Security and privacy claims** not in `docs/privacy/public-security-claims.md`. Never "completely private", "never leaves Synaptiq" or "GDPR compliant".
- **Reply-time promises** for mailboxes nobody has confirmed. Route people to the contact form, with a `?topic=` where useful.

## Body text

- Text is left-aligned by default, at a comfortable measure (about 42rem for body copy, 35rem for small print).
- Full justification is only for genuinely long-form editorial prose (class `lp-prose`: the About essay; the Security model). It justifies with hyphenation on wide screens and goes left-aligned below 700px.
- Don't justify leads, headings, labels, buttons, captions or card text.
- Most paragraphs are one to three short sentences. If a sentence repeats its heading, cut it.

## Visual system

All public pages render inside `.lp` and use the tokens and primitives in `frontend/src/components/landing/landing.css`. Page stylesheets extend them; they don't define their own colours, buttons or spacing.

| Element | Rule |
|---|---|
| Brand colour | One navy, `--sq-brand-navy` (#0F2847): primary buttons, active and selected states, section numbers, structural rules, arrows, focus rings, the footer and the Sign In panel. Hover is `--sq-brand-navy-deep`. |
| Neutrals | `--ink` headings, `--ink-2` body, `--muted` secondary, `--rule` borders, `--paper` and `--surface` backgrounds. |
| Semantic | `--danger` for errors and missing states only. ORCID keeps its own green. |
| Type | Newsreader (serif) for H1, H2, figure titles and plan names; Plus Jakarta Sans for everything else; monospace only for eyebrows, labels and dates. |
| Buttons | `lp-btn lp-btn--primary` (navy) and `lp-btn lp-btn--ghost` (neutral, bordered): 48px tall, 4px radius, the same shape as the Sign In screens. Tertiary actions are `lp-link` with "→". **Start Free is always the primary button.** |
| Layout | One container: `.lp-wrap` for content, `.mk-wrap` for the header and footer (1180px, 24px / 40px gutters), so they share a left edge. |
| Rhythm | Sections `--section-y` (96px, 64px on phones); heroes `--hero-y` (104px, 56px on phones). |
| Eyebrows | A page's eyebrow (`lp-index lp-eyebrow`) names what the page is; section eyebrows are numbered (`<b>01</b> Name`). |
| Cards | Only for discrete objects (plans, product fragments, specimen people). Use rules and spacing for everything else. |

Each section carries one message. A page gets one H1 and at most two buttons per call to action.
