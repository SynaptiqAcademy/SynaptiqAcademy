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

- Long explanatory paragraphs use the shared editorial treatment: class `lp-prose`, or the existing `lp-lede`. It justifies with hyphenation on wide screens and goes left-aligned below 700px.
- Don't justify headings, labels, buttons, captions or card text.
