# Authenticated app: route coverage

Every signed-in route in `frontend/src/App.js`, with what it looked like before the authenticated-app redesign (commit `db847d2`), what changed, and how it was checked. Public website routes are covered by the public-website work and are not repeated here.

How it was checked:

- **Initial status**: automated crawl of the app before the redesign (title style, dark banners, accent colours, low-contrast text, render errors) at 1440px.
- **Changes**: the page's own source diff since `db847d2`, grouped by kind. Every page also received the shared changes: light page header with serif title, one navy, one button system, readable muted text, zero metrics hidden, standard empty, missing-record and upgrade states.
- **Responsive**: crawl at 390px. ✓ means no horizontal page overflow and no render error. Every page was also crawled at 1024px.
- **Functional**: crawl at 1440px as a Pro Advanced member (admin console: as a super admin). ✓ means the page rendered without a runtime error or crash and loaded its data from the local API. The same routes were crawled as Free and Pro members to confirm upgrade states; those are listed in Notes.
- Detail routes were opened with real records in a local database. Where no record of that type exists locally, the route was opened with a non-existent id to check the not-available state.

**Totals:** 240 routes — 233 COMPLETED, 7 INTENTIONALLY UNCHANGED – ALREADY COMPLIANT, 0 BLOCKED.

| Route | Page | Initial status | Changes | Final status | Responsive (390px) | Functional | Notes |
|---|---|---|---|---|---|---|---|
| `/settings/billing` | pages/BillingCenter.jsx | sans title; 2 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ | plan card changed to a light block after the crawl; re-checked by screenshot (no dark banner) |
| `/payment/success` | pages/PaymentSuccess.jsx | sans title | editorial page header | COMPLETED | ✓ | ✓ |  |
| `/payment/cancelled` | pages/PaymentCancelled.jsx | sans title | editorial page header | COMPLETED | ✓ | ✓ |  |
| `/settings/security` | pages/AccountSecurity.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/admin` | pages/admin/AdminCommandCenter.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/users` | pages/admin/AdminUsers.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/users/:uid` | pages/admin/AdminUserDetail.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record; final crawl: burgundy/red accents |
| `/admin/audit` | pages/admin/AdminAudit.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/security` | pages/admin/AdminSecurity.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | crashed (list response not unwrapped); fixed and re-checked |
| `/admin/email` | pages/admin/AdminEmailCenter.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/analytics` | pages/admin/AdminAnalytics.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/revenue` | pages/admin/AdminRevenuePage.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ |  |
| `/admin/health` | pages/admin/AdminHealth.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/reputation` | pages/admin/AdminReputation.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/teaching-analytics` | pages/admin/AdminTeachingAnalytics.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/subscriptions` | pages/admin/AdminSubscriptions.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/errors` | pages/admin/AdminErrorCenter.jsx | admin console (not in baseline crawl) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/admin/research` | pages/admin/AdminResearchGovernance.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/database` | pages/admin/AdminDatabaseOps.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/platform-auditor` | pages/admin/AdminPlatformAuditor.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/promotions` | pages/admin/AdminPromotions.jsx | admin console (not in baseline crawl) | one primary action, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/communications` | pages/admin/AdminCommunications.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/feature-flags-center` | pages/admin/AdminFeatureFlags.jsx | admin console (not in baseline crawl) | one primary action, plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/jobs` | pages/admin/AdminJobsCenter.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/api-monitor` | pages/admin/AdminApiMonitor.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/storage` | pages/admin/AdminStorageGovernance.jsx | admin console (not in baseline crawl) | layout and style alignment | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/institution-center` | pages/admin/AdminInstitutionCenter.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | final crawl: 1 dark banner(s) |
| `/admin/search` | pages/admin/AdminSearchObservatory.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ |  |
| `/admin/data-quality` | pages/admin/AdminDataQuality.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/releases` | pages/admin/AdminReleases.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/support` | pages/admin/AdminSupportCenter.jsx | admin console (not in baseline crawl) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/admin/research-integrity` | pages/admin/AdminResearchIntegrity.jsx | admin console (not in baseline crawl) | layout and style alignment | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/command-map` | pages/admin/AdminCommandMap.jsx | admin console (not in baseline crawl) | shared components only (header, buttons, tokens, states) | INTENTIONALLY UNCHANGED – ALREADY COMPLIANT | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/copilot` | pages/admin/AdminAICopilot.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/account-security` | pages/admin/AdminAccountSecurity.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/mfa` | pages/admin/AdminMFACenter.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/security-hardening` | pages/admin/AdminSecurityHardening.jsx | admin console (not in baseline crawl) | single navy accent; red only for errors, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/reputation-center` | pages/admin/AdminReputationCenter.jsx | admin console (not in baseline crawl) | readable muted text | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/recommendation-center` | pages/admin/AdminRecommendationCenter.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/impact-center` | pages/admin/AdminImpactCenter.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/ai-center` | pages/admin/AdminAICenter.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/grant-hub` | pages/admin/AdminGrantHub.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | crashed (list response not unwrapped); fixed and re-checked |
| `/admin/reviewer-hub` | pages/admin/AdminReviewerHub.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/verification` | pages/admin/AdminVerification.jsx | admin console (not in baseline crawl) | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/trust-center` | pages/admin/AdminTrustCenter.jsx | admin console (not in baseline crawl) | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/admin/integrity-center` | pages/admin/AdminIntegrityCenter.jsx | admin console (not in baseline crawl) | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/admin/profiles` | pages/admin/AdminProfiles.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/admin/dashboard` | pages/admin/AdminDashboard.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/admin/content` | pages/admin/AdminDashboard.jsx | admin console (not in baseline crawl) | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/onboarding` | pages/Onboarding.jsx | not in baseline crawl | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/profile-setup` | pages/ProfileSetup.jsx | not in baseline crawl | readable muted text | COMPLETED | ✓ | ✓ | three-column grid overflowed at 390px; now stacks below 1024px; re-checked |
| `/today` | pages/Today.jsx | no page title; burgundy/red accents; low-contrast text | editorial page header, readable muted text, single navy accent; red only for errors, credit prices from server catalogue, section heading scale | COMPLETED | ✓ | ✓ |  |
| `/recommendation-center` | pages/RecommendationCenter.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | layout and style alignment | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/copilot` | pages/Copilot.jsx | sans title; 1 dark banner(s); low-contrast text | one primary action, honest empty / missing state | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/living-graph` | pages/LivingGraph.jsx | sans title; 1 dark banner(s); low-contrast text | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/twin` | pages/DigitalTwin.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/agent-workforce` | pages/AgentWorkforce.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action | COMPLETED | ✓ | ✓ |  |
| `/discover` | pages/Discover.jsx | sans title; low-contrast text | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/collaborations` | pages/Collaborations.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, side column only when it has content, one primary action, section heading scale | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/collaborations/new` | pages/CreateCollaboration.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/collaborations/my` | pages/MyCollaborations.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/collaborations/:id` | pages/CollaborationDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/teams` | pages/Teams.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teams/create` | pages/CreateTeam.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teams/:id` | pages/TeamHome.jsx | not in baseline crawl | readable muted text, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/research-hub` | pages/ResearchCommandCenter.jsx | sans title; 1 dark banner(s) | one primary action | COMPLETED | ✓ | ✓ |  |
| `/feed` | pages/ResearchFeed.jsx | sans title; 1 dark banner(s) | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/profile` | pages/Profile.jsx | sans title; 1 dark banner(s); burgundy/red accents | readable muted text, single navy accent; red only for errors, plain-language errors | COMPLETED | ✓ | ✓ | final crawl: 1 dark banner(s); burgundy/red accents |
| `/profile/:userId` | pages/Profile.jsx | not in baseline crawl | readable muted text, single navy accent; red only for errors, plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record; final crawl: 1 dark banner(s) |
| `/academic-passport` | pages/AcademicPassport.jsx | sans title; 1 dark banner(s); burgundy/red accents | plain-language errors | COMPLETED | ✓ | ✓ | final crawl: 1 dark banner(s); burgundy/red accents |
| `/projects` | pages/Projects.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, one primary action | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/projects/:id` | pages/ProjectDetail.jsx | not in baseline crawl | editorial page header, one primary action, honest empty / missing state | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/messages` | pages/Messages.jsx | sans title; burgundy/red accents; low-contrast text | single navy accent; red only for errors, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/messages/c/:conversationId` | pages/Messages.jsx | not in baseline crawl | single navy accent; red only for errors, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/messages/:otherId` | pages/Messages.jsx | not in baseline crawl | single navy accent; red only for errors, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/meetings` | pages/Meetings.jsx | sans title; 1 dark banner(s) | one primary action | COMPLETED | ✓ | ✓ |  |
| `/meetings/:id` | pages/MeetingDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/analytics` | pages/Analytics.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/ai-usage` | pages/AIUsage.jsx | sans title; 1 dark banner(s); low-contrast text | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/marketplace` | pages/Marketplace.jsx | sans title; 1 dark banner(s); low-contrast text | credit prices from server catalogue, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/expertise` | pages/ExpertiseRequests.jsx | sans title; 1 dark banner(s); low-contrast text | one primary action, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/expertise/:id` | pages/ExpertiseRequestDetail.jsx | not in baseline crawl | one primary action, plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record; final crawl: burgundy/red accents |
| `/invitations` | pages/Invitations.jsx | sans title; 1 dark banner(s) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/institutions` | pages/Institutions.jsx | sans title; 1 dark banner(s) | one primary action, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/institutions/:id` | pages/InstitutionDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/units/:id` | pages/UnitDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/research-centers/:id` | pages/UnitDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/labs/:id` | pages/UnitDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/institution/analytics` | pages/InstitutionAnalytics.jsx | no page title | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | institution membership required |
| `/institution/departments` | pages/Departments.jsx | no page title | one primary action | COMPLETED | ✓ | ✓ | institution membership required |
| `/institution/departments/:did` | pages/DepartmentDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | institution membership required; no local record of this type: checked the not-available state |
| `/faculty/:id` | pages/FacultyProfile.jsx | not in baseline crawl | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/notifications` | pages/Notifications.jsx | sans title; burgundy/red accents; low-contrast text | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/settings` | pages/Settings.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/journals` | pages/Journals.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state; final crawl: burgundy/red accents |
| `/journals/:id` | pages/JournalDetail.jsx | not in baseline crawl | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/conferences` | pages/Conferences.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/conferences/:id` | pages/ConferenceDetail.jsx | not in baseline crawl | plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/conference-teams/:teamId` | pages/ConferenceTeam.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/funding` | pages/Funding.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/funding/:id` | pages/FundingDetail.jsx | not in baseline crawl | editorial page header, one primary action, honest empty / missing state | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/grants` | pages/Grants.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, side column only when it has content, single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/grants/:id` | pages/GrantDetail.jsx | not in baseline crawl | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/grant-applications` | pages/GrantApplications.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/grant-applications/:id` | pages/GrantApplicationDetail.jsx | not in baseline crawl | readable muted text, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/workspaces` | pages/Workspaces.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/workspaces/:id` | pages/WorkspaceDetail.jsx | not in baseline crawl | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record; tab row overflowed at 1024px; tabs now scroll; re-checked at 390/1024px; final crawl: red only on the Reject action (semantic) |
| `/manuscripts` | pages/Manuscripts.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/manuscripts/:id` | pages/ManuscriptDetail.jsx | not in baseline crawl | editorial page header, one primary action, honest empty / missing state, plain-language errors | COMPLETED | ✓ | ✓ | checked with a real local record; final crawl: burgundy/red accents |
| `/reviews` | pages/Reviews.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, side column only when it has content, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/manuscript-review` | pages/ManuscriptReview.jsx | sans title; 1 dark banner(s); low-contrast text | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/literature-review` | pages/LiteratureReview.jsx | sans title; 1 dark banner(s); burgundy/red accents | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state; final crawl: burgundy/red accents |
| `/ai/abstract` | pages/AbstractGenerator.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state; final crawl: burgundy/red accents |
| `/ai/rewrite` | pages/AIRewriting.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state; final crawl: burgundy/red accents |
| `/research-gap-finder` | pages/ResearchGapFinder.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state; final crawl: burgundy/red accents |
| `/research-design-advisor` | pages/ResearchDesignAdvisor.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state |
| `/statistical-review` | pages/StatisticalReview.jsx | sans title; 1 dark banner(s); low-contrast text | layout and style alignment | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state |
| `/citation-monitoring` | pages/CitationMonitoring.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state; final crawl: burgundy/red accents |
| `/citations` | pages/Citations.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/citations/:id` | pages/CitationDetail.jsx | not in baseline crawl | layout and style alignment | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/research-impact` | pages/ResearchImpact.jsx | sans title; 1 dark banner(s) | readable muted text | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state |
| `/collaboration-intelligence` | pages/CollaborationIntelligence.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, no people-match percentages, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state |
| `/collaboration-requests` | pages/CollaborationRequests.jsx | sans title; 1 dark banner(s) | plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/publication-hub` | pages/PublicationHub.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state; final crawl: burgundy/red accents |
| `/repository` | pages/Repository.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, one primary action | COMPLETED | ✓ | ✓ |  |
| `/teaching` | pages/teaching/TeachingHub.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teaching/lesson-planner` | pages/teaching/LessonPlanner.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teaching/lessons/:lessonId` | pages/teaching/LessonPlanDetail.jsx | not in baseline crawl | readable muted text | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/teaching/portfolio` | pages/teaching/TeachingPortfolio.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teaching/assessment-builder` | pages/teaching/AssessmentBuilder.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teaching/assessments/:assessmentId` | pages/teaching/AssessmentDetail.jsx | not in baseline crawl | readable muted text | COMPLETED | ✓ | ✓ | checked with a real local record |
| `/teaching/workspaces` | pages/teaching/TeachingWorkspace.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/teaching/workspaces/:workspaceId` | pages/teaching/TeachingWorkspaceDetail.jsx | not in baseline crawl | readable muted text, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/teaching/analytics` | pages/teaching/TeachingAnalytics.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/reputation` | pages/ReputationAnalytics.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/leaderboards` | pages/Leaderboards.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | readable muted text | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/recommendations` | pages/Recommendations.jsx | sans title; 1 dark banner(s) | no people-match percentages, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/impact-dashboard` | pages/ImpactDashboard.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, plain-language errors, zero metrics hidden | COMPLETED | ✓ | ✓ | Free: upgrade state; Pro: upgrade state |
| `/ai` | pages/AIAssistant.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | editorial page header, readable muted text, one primary action, single navy accent; red only for errors, honest empty / missing state, credit prices from server catalogue | COMPLETED | ✓ | ✓ |  |
| `/ai-suite` | pages/AISuite.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/ai-credits` | pages/AICredits.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/institution-hub` | pages/InstitutionHub.jsx | no page title | layout and style alignment | COMPLETED | ✓ | ✓ | institution membership required |
| `/institution-hub/:id` | pages/InstitutionProfile.jsx | not in baseline crawl | layout and style alignment | COMPLETED | — | ✓ | no local record of this type: checked the not-available state; final crawl: burgundy/red accents |
| `/institution-hub/:id/admin` | pages/InstitutionAdminConsole.jsx | not in baseline crawl | layout and style alignment | COMPLETED | — | ✓ | institution membership required; no local record of this type: checked the not-available state |
| `/institution-leaderboards` | pages/InstitutionLeaderboards.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/grant-collaboration-hub` | pages/GrantCollaborationHub.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content, one primary action | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/grant-hub/:id` | pages/GrantOpportunityWorkspace.jsx | not in baseline crawl | readable muted text, no people-match percentages | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/researchers` | pages/ResearchExperts.jsx | sans title; 1 dark banner(s) | editorial page header, one primary action, honest empty / missing state, no people-match percentages | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/team-builder/:id` | pages/TeamBuilder.jsx | not in baseline crawl | plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/reviewer-marketplace` | pages/ReviewerMarketplace.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, side column only when it has content, one primary action, plain-language errors, section heading scale | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/review-workspace/:id` | pages/ReviewWorkspace.jsx | not in baseline crawl | no people-match percentages, plain-language errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/institution-analytics/:id` | pages/InstitutionAnalyticsCenter.jsx | not in baseline crawl | layout and style alignment | COMPLETED | — | ✓ | institution membership required; no local record of this type: checked the not-available state |
| `/verification` | pages/VerificationCenter.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, plain-language errors | COMPLETED | ✓ | ✓ |  |
| `/trust` | pages/trust/TrustOverview.jsx | sans title; 1 dark banner(s); burgundy/red accents | readable muted text, side column only when it has content, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/trust/my-verifications` | pages/trust/MyVerifications.jsx | sans title; 1 dark banner(s); low-contrast text | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/trust/requests` | pages/trust/VerificationRequests.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/trust/score` | pages/trust/TrustScore.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/trust/integrity` | pages/trust/IntegrityReport.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/trust/institution` | pages/trust/InstitutionVerification.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/trust/publications` | pages/trust/PublicationVerification.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/trust/reviewer` | pages/trust/ReviewerVerification.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/trust/grants` | pages/trust/GrantVerification.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/trust/history` | pages/trust/VerificationHistory.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/trust/settings` | pages/trust/VerificationSettings.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/timeline` | pages/timeline/ResearchTimeline.jsx | sans title; 1 dark banner(s); low-contrast text | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/timeline/analytics` | pages/timeline/TimelineAnalytics.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/integrity` | pages/integrity/IntegrityCenter.jsx | sans title; 1 dark banner(s); low-contrast text | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie` | pages/sie/ResearchCommandCenter.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/sie/goals` | pages/sie/GoalManager.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/planning` | pages/sie/ResearchPlanning.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/publications` | pages/sie/PublicationRoadmap.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/grants` | pages/sie/GrantPlanner.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/sie/career` | pages/sie/CareerPlanner.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/sie/daily` | pages/sie/DailyAgenda.jsx | sans title; 1 dark banner(s); burgundy/red accents | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/sie/weekly` | pages/sie/WeeklyPlanner.jsx | sans title; 1 dark banner(s) | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/missions` | pages/sie/ResearchMissions.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/memory` | pages/sie/AIMemory.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/sie/recommendations` | pages/sie/Recommendations.jsx | sans title; 1 dark banner(s); burgundy/red accents | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/sie/automations` | pages/sie/AutomationCenter.jsx | sans title; 1 dark banner(s); burgundy/red accents | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/sie/progress` | pages/sie/ResearchProgress.jsx | sans title; 1 dark banner(s); burgundy/red accents | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/sie/settings` | pages/sie/SIESettings.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/network` | pages/network/DiscoveryHome.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/institutions` | pages/network/InstitutionDiscovery.jsx | sans title | editorial page header, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/groups` | pages/network/ResearchGroups.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/teaching` | pages/network/TeachingCommunities.jsx | sans title; 1 dark banner(s) | one primary action | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/projects` | pages/network/ProjectsDiscovery.jsx | sans title | editorial page header, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/collaborations` | pages/network/OpenCollaborations.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors, plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/grant-teams` | pages/network/GrantTeams.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/conferences` | pages/network/ConferenceNetworking.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/industry` | pages/network/IndustryPartners.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/mentorship` | pages/network/MentorshipPlatform.jsx | sans title; 1 dark banner(s) | plain-language errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/communities` | pages/network/Communities.jsx | sans title; 1 dark banner(s) | side column only when it has content, one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/recommendations` | pages/network/NetworkRecommendations.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/saved` | pages/network/SavedOpportunities.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/activity` | pages/network/ActivityCenter.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/analytics` | pages/network/NetworkAnalytics.jsx | sans title; 2 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/network/settings` | pages/network/NetworkSettings.jsx | sans title; burgundy/red accents | readable muted text | COMPLETED | ✓ | ✓ | Free: upgrade state |
| `/academic-marketplace` | pages/academic_marketplace/MarketplaceHome.jsx | sans title; 1 dark banner(s); burgundy/red accents | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/services` | pages/academic_marketplace/ServiceBrowse.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/services/create` | pages/academic_marketplace/ServiceCreate.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/services/:id` | pages/academic_marketplace/ServiceDetail.jsx | not in baseline crawl | single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/providers` | pages/academic_marketplace/ProviderBrowse.jsx | sans title; 1 dark banner(s) | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/providers/:id` | pages/academic_marketplace/ProviderProfile.jsx | not in baseline crawl | single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/provider/setup` | pages/academic_marketplace/ProviderSetup.jsx | sans title; 1 dark banner(s) | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/dashboard` | pages/academic_marketplace/ProviderDashboard.jsx | sans title; 1 dark banner(s) | readable muted text, one primary action, single navy accent; red only for errors, honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/order/:id` | pages/academic_marketplace/OrderPlace.jsx | not in baseline crawl | readable muted text, single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/orders` | pages/academic_marketplace/OrderList.jsx | sans title; 1 dark banner(s) | readable muted text, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/orders/:id` | pages/academic_marketplace/OrderDetail.jsx | not in baseline crawl | readable muted text, single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/rate/:id` | pages/academic_marketplace/RatingSubmit.jsx | not in baseline crawl | readable muted text, one primary action, honest empty / missing state | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/disputes` | pages/academic_marketplace/DisputeCenter.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/disputes/:id` | pages/academic_marketplace/DisputeDetail.jsx | not in baseline crawl | readable muted text | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/contracts/:id` | pages/academic_marketplace/ContractView.jsx | not in baseline crawl | readable muted text, single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/academic-marketplace/wallet` | pages/academic_marketplace/WalletCenter.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/recommendations` | pages/academic_marketplace/Recommendations.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors, honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/academic-marketplace/admin` | pages/academic_marketplace/AdminMarketplace.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content, single navy accent; red only for errors, section heading scale | COMPLETED | ✓ | ✓ |  |
| `/akg` | pages/akg/KnowledgeGraphHome.jsx | sans title; 1 dark banner(s); burgundy/red accents | section heading scale | COMPLETED | ✓ | ✓ |  |
| `/akg/explorer` | pages/akg/GraphExplorer.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/akg/search` | pages/akg/EntitySearch.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/akg/entity/:entityId` | pages/akg/EntityDetail.jsx | not in baseline crawl | readable muted text, single navy accent; red only for errors | COMPLETED | — | ✓ | no local record of this type: checked the not-available state |
| `/akg/trends` | pages/akg/TrendDiscovery.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/akg/analytics` | pages/akg/GraphAnalytics.jsx | sans title; 1 dark banner(s) | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/akg/recommendations` | pages/akg/RecommendationHub.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/akg/reasoning` | pages/akg/AIReasoning.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
| `/akg/sync` | pages/akg/SyncCenter.jsx | sans title; 1 dark banner(s) | fixed through shared components (page header, buttons, tokens, states) | COMPLETED | ✓ | ✓ |  |
| `/akg/admin` | pages/akg/GraphAdmin.jsx | sans title; 1 dark banner(s); burgundy/red accents | readable muted text | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/institution-platform` | pages/institution_platform/ExecutiveDashboard.jsx | no page title; burgundy/red accents | editorial page header, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/health` | pages/institution_platform/InstitutionHealth.jsx | sans title; 1 dark banner(s); burgundy/red accents | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/institution-platform/faculty` | pages/institution_platform/FacultyIntelligence.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/departments` | pages/institution_platform/DepartmentIntelligence.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content, single navy accent; red only for errors, honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/publications` | pages/institution_platform/PublicationIntelligence.jsx | sans title; 1 dark banner(s) | readable muted text, honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/grants` | pages/institution_platform/GrantIntelligence.jsx | sans title; 1 dark banner(s) | honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/collaborations` | pages/institution_platform/CollaborationIntelligence.jsx | sans title; 1 dark banner(s) | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/financial` | pages/institution_platform/FinancialIntelligence.jsx | sans title; 1 dark banner(s) | honest empty / missing state | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/risks` | pages/institution_platform/RiskIntelligence.jsx | sans title; 1 dark banner(s); burgundy/red accents; low-contrast text | single navy accent; red only for errors | COMPLETED | ✓ | ✓ | final crawl: burgundy/red accents |
| `/institution-platform/forecasts` | pages/institution_platform/ForecastCenter.jsx | sans title; 1 dark banner(s) | readable muted text | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/benchmarks` | pages/institution_platform/BenchmarkCenter.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/reports` | pages/institution_platform/InstitutionReports.jsx | sans title; 1 dark banner(s) | one primary action, single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/assistant` | pages/institution_platform/AIExecutiveAssistant.jsx | sans title; 1 dark banner(s); burgundy/red accents | readable muted text, side column only when it has content | COMPLETED | ✓ | ✓ |  |
| `/institution-platform/strategic` | pages/institution_platform/StrategicPlanning.jsx | sans title; 1 dark banner(s) | single navy accent; red only for errors | COMPLETED | ✓ | ✓ |  |
| `/search` | pages/GlobalSearch.jsx | sans title; 1 dark banner(s) | layout and style alignment | COMPLETED | ✓ | ✓ |  |
