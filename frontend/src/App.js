import React, { Suspense, lazy } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "@/components/ErrorBoundary";

import { AuthProvider } from "@/contexts/AuthContext";
import { UnreadProvider } from "@/contexts/UnreadContext";
import ProtectedRoute from "@/components/layout/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";

// Critical path — loaded eagerly (no auth, hit on first visit)
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import VerifyEmailPending from "@/pages/VerifyEmailPending";
import InvitationAccept from "@/pages/InvitationAccept";
import GoogleCallback from "@/pages/GoogleCallback";
import Unsubscribed from "@/pages/Unsubscribed";

import { Toaster } from "@/components/ui/sonner";
import CookieConsentBanner from "@/components/consent/CookieConsentBanner";
import UpgradeModal from "@/components/billing/UpgradeModal";

// All remaining pages loaded on demand — each route only pays for its own JS
const Onboarding = lazy(() => import("@/pages/Onboarding"));
const ProfileSetup  = lazy(() => import("@/pages/ProfileSetup"));
const Teams         = lazy(() => import("@/pages/Teams"));
const CreateTeam    = lazy(() => import("@/pages/CreateTeam"));
const TeamHome      = lazy(() => import("@/pages/TeamHome"));
const ResearchFeed  = lazy(() => import("@/pages/ResearchFeed"));
const ResearchCommandCenter = lazy(() => import("@/pages/ResearchCommandCenter"));
const Discover = lazy(() => import("@/pages/Discover"));
const Today                  = lazy(() => import("@/pages/Today"));
const RecommendationCenter   = lazy(() => import("@/pages/RecommendationCenter"));
const Copilot                = lazy(() => import("@/pages/Copilot"));
const LivingGraph            = lazy(() => import("@/pages/LivingGraph"));
const DigitalTwin            = lazy(() => import("@/pages/DigitalTwin"));
const AgentWorkforce         = lazy(() => import("@/pages/AgentWorkforce"));
const Collaborations = lazy(() => import("@/pages/Collaborations"));
const CollaborationDetail = lazy(() => import("@/pages/CollaborationDetail"));
const CreateCollaboration = lazy(() => import("@/pages/CreateCollaboration"));
const MyCollaborations = lazy(() => import("@/pages/MyCollaborations"));
const Profile = lazy(() => import("@/pages/Profile"));
const Projects = lazy(() => import("@/pages/Projects"));
const ProjectDetail = lazy(() => import("@/pages/ProjectDetail"));
const Messages = lazy(() => import("@/pages/Messages"));
const Meetings = lazy(() => import("@/pages/Meetings"));
const MeetingDetail = lazy(() => import("@/pages/MeetingDetail"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Notifications = lazy(() => import("@/pages/Notifications"));
const Settings = lazy(() => import("@/pages/Settings"));
const AccountSecurity = lazy(() => import("@/pages/AccountSecurity"));
const BillingCenter = lazy(() => import("@/pages/BillingCenter"));

// Phase II
const Journals = lazy(() => import("@/pages/Journals"));
const JournalDetail = lazy(() => import("@/pages/JournalDetail"));
const Conferences = lazy(() => import("@/pages/Conferences"));
const ConferenceDetail = lazy(() => import("@/pages/ConferenceDetail"));
const Funding = lazy(() => import("@/pages/Funding"));
const FundingDetail = lazy(() => import("@/pages/FundingDetail"));
const Grants = lazy(() => import("@/pages/Grants"));
const Workspaces = lazy(() => import("@/pages/Workspaces"));
const WorkspaceDetail = lazy(() => import("@/pages/WorkspaceDetail"));
const Manuscripts = lazy(() => import("@/pages/Manuscripts"));
const ManuscriptDetail = lazy(() => import("@/pages/ManuscriptDetail"));
const PublicationHub = lazy(() => import("@/pages/PublicationHub"));
const Repository = lazy(() => import("@/pages/Repository"));
const Reviews = lazy(() => import("@/pages/Reviews"));
const ManuscriptReview = lazy(() => import("@/pages/ManuscriptReview"));
const LiteratureReview = lazy(() => import("@/pages/LiteratureReview"));
const AbstractGenerator = lazy(() => import("@/pages/AbstractGenerator"));
const AIRewriting = lazy(() => import("@/pages/AIRewriting"));
const ResearchGapFinder = lazy(() => import("@/pages/ResearchGapFinder"));
const ResearchDesignAdvisor = lazy(() => import("@/pages/ResearchDesignAdvisor"));
const StatisticalReview = lazy(() => import("@/pages/StatisticalReview"));
const CitationMonitoring = lazy(() => import("@/pages/CitationMonitoring"));
const CollaborationIntelligence = lazy(() => import("@/pages/CollaborationIntelligence"));
const CollaborationRequests = lazy(() => import("@/pages/CollaborationRequests"));
const Citations = lazy(() => import("@/pages/Citations"));
const CitationDetail = lazy(() => import("@/pages/CitationDetail"));
const ResearchImpact = lazy(() => import("@/pages/ResearchImpact"));
const GrantDetail = lazy(() => import("@/pages/GrantDetail"));
const GrantApplications = lazy(() => import("@/pages/GrantApplications"));
const GrantApplicationDetail = lazy(() => import("@/pages/GrantApplicationDetail"));
const AIUsage = lazy(() => import("@/pages/AIUsage"));
const Marketplace = lazy(() => import("@/pages/Marketplace"));
const ExpertiseRequests = lazy(() => import("@/pages/ExpertiseRequests"));
const ExpertiseRequestDetail = lazy(() => import("@/pages/ExpertiseRequestDetail"));
const Invitations = lazy(() => import("@/pages/Invitations"));
const Institutions = lazy(() => import("@/pages/Institutions"));
const InstitutionDetail = lazy(() => import("@/pages/InstitutionDetail"));
const UnitDetail = lazy(() => import("@/pages/UnitDetail"));
const Departments = lazy(() => import("@/pages/Departments"));
const DepartmentDetail = lazy(() => import("@/pages/DepartmentDetail"));
const InstitutionAnalytics = lazy(() => import("@/pages/InstitutionAnalytics"));

// Marketing & SaaS pages
const InstitutionsLanding = lazy(() => import("@/pages/InstitutionsLanding"));
const Platform = lazy(() => import("@/pages/Platform"));
const ResearchLanding = lazy(() => import("@/pages/ResearchLanding"));
const AIWorkspaceLanding = lazy(() => import("@/pages/AIWorkspaceLanding"));
const Pricing = lazy(() => import("@/pages/Pricing"));
const Contact = lazy(() => import("@/pages/Contact"));
const About             = lazy(() => import("@/pages/About"));
const Resources         = lazy(() => import("@/pages/resources/Resources"));
const WhatsNew          = lazy(() => import("@/pages/resources/WhatsNew"));
const CustomerStories   = lazy(() => import("@/pages/resources/CustomerStories"));
const ResourcesBlog     = lazy(() => import("@/pages/resources/Blog"));
const LegalCenter = lazy(() => import("@/pages/LegalCenter"));
const Terms = lazy(() => import("@/pages/Terms"));
const Privacy = lazy(() => import("@/pages/Privacy"));
const GDPR = lazy(() => import("@/pages/GDPR"));
const Cookies = lazy(() => import("@/pages/Cookies"));
const Security = lazy(() => import("@/pages/Security"));
const AiPolicy        = lazy(() => import("@/pages/AiPolicy"));
const Documentation   = lazy(() => import("@/pages/Documentation"));
const HelpCenter      = lazy(() => import("@/pages/HelpCenter"));
const ApiPortal       = lazy(() => import("@/pages/ApiPortal"));
const Status          = lazy(() => import("@/pages/Status"));

// Teaching Hub — Production
const TeachingHub                = lazy(() => import("@/pages/teaching/TeachingHub"));
const LessonPlanner              = lazy(() => import("@/pages/teaching/LessonPlanner"));
const LessonPlanDetail           = lazy(() => import("@/pages/teaching/LessonPlanDetail"));
const TeachingPortfolio          = lazy(() => import("@/pages/teaching/TeachingPortfolio"));
const AssessmentBuilder          = lazy(() => import("@/pages/teaching/AssessmentBuilder"));
const AssessmentDetail           = lazy(() => import("@/pages/teaching/AssessmentDetail"));
const TeachingWorkspaceList      = lazy(() => import("@/pages/teaching/TeachingWorkspace"));
const TeachingWorkspaceDetail    = lazy(() => import("@/pages/teaching/TeachingWorkspaceDetail"));
const TeachingAnalytics          = lazy(() => import("@/pages/teaching/TeachingAnalytics"));
const AdminTeachingAnalytics     = lazy(() => import("@/pages/admin/AdminTeachingAnalytics"));

// Admin Platform — heavy section, always lazy
const AdminProtectedRoute = lazy(() => import("@/components/admin/AdminProtectedRoute"));
const AdminShell = lazy(() => import("@/components/admin/AdminShell"));
const AdminDashboard = lazy(() => import("@/pages/admin/AdminDashboard"));
const AdminUsers = lazy(() => import("@/pages/admin/AdminUsers"));
const AdminUserDetail = lazy(() => import("@/pages/admin/AdminUserDetail"));
const AdminAudit = lazy(() => import("@/pages/admin/AdminAudit"));
const AdminSecurity = lazy(() => import("@/pages/admin/AdminSecurity"));
const AdminEmailCenter = lazy(() => import("@/pages/admin/AdminEmailCenter"));
const AdminAnalytics = lazy(() => import("@/pages/admin/AdminAnalytics"));
const AdminRevenuePage = lazy(() => import("@/pages/admin/AdminRevenuePage"));
const AdminHealth = lazy(() => import("@/pages/admin/AdminHealth"));
const AdminReputation = lazy(() => import("@/pages/admin/AdminReputation"));
const AdminCommandCenter     = lazy(() => import("@/pages/admin/AdminCommandCenter"));
const AdminSubscriptions     = lazy(() => import("@/pages/admin/AdminSubscriptions"));
const AdminErrorCenter       = lazy(() => import("@/pages/admin/AdminErrorCenter"));
const AdminResearchGovernance = lazy(() => import("@/pages/admin/AdminResearchGovernance"));
const AdminDatabaseOps       = lazy(() => import("@/pages/admin/AdminDatabaseOps"));
const AdminPlatformAuditor   = lazy(() => import("@/pages/admin/AdminPlatformAuditor"));
const AdminPromotions        = lazy(() => import("@/pages/admin/AdminPromotions"));
const AdminCommunications    = lazy(() => import("@/pages/admin/AdminCommunications"));
const AdminFeatureFlags      = lazy(() => import("@/pages/admin/AdminFeatureFlags"));
const AdminJobsCenter        = lazy(() => import("@/pages/admin/AdminJobsCenter"));
const AdminApiMonitor        = lazy(() => import("@/pages/admin/AdminApiMonitor"));
const AdminStorageGovernance = lazy(() => import("@/pages/admin/AdminStorageGovernance"));
const AdminInstitutionCenter = lazy(() => import("@/pages/admin/AdminInstitutionCenter"));
const AdminSearchObservatory = lazy(() => import("@/pages/admin/AdminSearchObservatory"));
const AdminDataQuality       = lazy(() => import("@/pages/admin/AdminDataQuality"));
const AdminReleases          = lazy(() => import("@/pages/admin/AdminReleases"));
const AdminSupportCenter     = lazy(() => import("@/pages/admin/AdminSupportCenter"));
const AdminResearchIntegrity = lazy(() => import("@/pages/admin/AdminResearchIntegrity"));
const AdminCommandMap        = lazy(() => import("@/pages/admin/AdminCommandMap"));
const AdminAICopilot         = lazy(() => import("@/pages/admin/AdminAICopilot"));
const AdminAccountSecurity   = lazy(() => import("@/pages/admin/AdminAccountSecurity"));
const AdminMFACenter         = lazy(() => import("@/pages/admin/AdminMFACenter"));
const AdminSecurityHardening = lazy(() => import("@/pages/admin/AdminSecurityHardening"));
const AdminReputationCenter      = lazy(() => import("@/pages/admin/AdminReputationCenter"));
const AdminRecommendationCenter  = lazy(() => import("@/pages/admin/AdminRecommendationCenter"));
const AdminImpactCenter          = lazy(() => import("@/pages/admin/AdminImpactCenter"));
const AdminAICenter              = lazy(() => import("@/pages/admin/AdminAICenter"));
const AdminGrantHub              = lazy(() => import("@/pages/admin/AdminGrantHub"));
const AdminReviewerHub           = lazy(() => import("@/pages/admin/AdminReviewerHub"));
const AdminVerification          = lazy(() => import("@/pages/admin/AdminVerification"));
const AdminProfiles              = lazy(() => import("@/pages/admin/AdminProfiles"));
const AIAssistant                = lazy(() => import("@/pages/AIAssistant"));
const AISuite                    = lazy(() => import("@/pages/AISuite"));
const AICredits                  = lazy(() => import("@/pages/AICredits"));
const ReputationAnalytics        = lazy(() => import("@/pages/ReputationAnalytics"));
const Leaderboards               = lazy(() => import("@/pages/Leaderboards"));
const Recommendations            = lazy(() => import("@/pages/Recommendations"));
const ImpactDashboard            = lazy(() => import("@/pages/ImpactDashboard"));
const InstitutionHub             = lazy(() => import("@/pages/InstitutionHub"));
const InstitutionProfile         = lazy(() => import("@/pages/InstitutionProfile"));
const InstitutionAdminConsole    = lazy(() => import("@/pages/InstitutionAdminConsole"));
const InstitutionLeaderboards    = lazy(() => import("@/pages/InstitutionLeaderboards"));
const GrantCollaborationHub      = lazy(() => import("@/pages/GrantCollaborationHub"));
const GrantOpportunityWorkspace  = lazy(() => import("@/pages/GrantOpportunityWorkspace"));
const ResearcherProfile          = lazy(() => import("@/pages/ResearcherProfile"));
const Researchers                = lazy(() => import("@/pages/Researchers"));
const ReviewerMarketplace        = lazy(() => import("@/pages/ReviewerMarketplace"));
const ReviewWorkspace            = lazy(() => import("@/pages/ReviewWorkspace"));
const InstitutionAnalyticsCenter = lazy(() => import("@/pages/InstitutionAnalyticsCenter"));
const VerificationCenter         = lazy(() => import("@/pages/VerificationCenter"));
const FacultyProfile             = lazy(() => import("@/pages/FacultyProfile"));
const GlobalSearch               = lazy(() => import("@/pages/GlobalSearch"));
const NotFound                   = lazy(() => import("@/pages/NotFound"));

// Trust & Verification Platform (isolated, /trust/* routes)
const TrustOverview              = lazy(() => import("@/pages/trust/TrustOverview"));
const MyVerifications            = lazy(() => import("@/pages/trust/MyVerifications"));
const VerificationRequests       = lazy(() => import("@/pages/trust/VerificationRequests"));
const AcademicPassport           = lazy(() => import("@/pages/AcademicPassport"));
const TrustScore                 = lazy(() => import("@/pages/trust/TrustScore"));
const IntegrityReport            = lazy(() => import("@/pages/trust/IntegrityReport"));
const InstitutionVerification    = lazy(() => import("@/pages/trust/InstitutionVerification"));
const PublicationVerification    = lazy(() => import("@/pages/trust/PublicationVerification"));
const ReviewerVerification       = lazy(() => import("@/pages/trust/ReviewerVerification"));
const GrantVerification          = lazy(() => import("@/pages/trust/GrantVerification"));
const VerificationHistory        = lazy(() => import("@/pages/trust/VerificationHistory"));
const VerificationSettings       = lazy(() => import("@/pages/trust/VerificationSettings"));
const AdminTrustCenter           = lazy(() => import("@/pages/admin/AdminTrustCenter"));

// Research Timeline & Academic Activity Engine — /timeline/*
const ResearchTimeline           = lazy(() => import("@/pages/timeline/ResearchTimeline"));
const TimelineAnalytics          = lazy(() => import("@/pages/timeline/TimelineAnalytics"));
const PublicTimeline             = lazy(() => import("@/pages/timeline/PublicTimeline"));

// Academic Integrity & Research Verification Engine — /integrity/*
const IntegrityCenter            = lazy(() => import("@/pages/integrity/IntegrityCenter"));
const AdminIntegrityCenter       = lazy(() => import("@/pages/admin/AdminIntegrityCenter"));

// Phase VI — Synaptiq Intelligence Engine — /sie/*
const SIECommandCenter    = lazy(() => import("@/pages/sie/ResearchCommandCenter"));
const SIEGoalManager      = lazy(() => import("@/pages/sie/GoalManager"));
const SIEPlanning         = lazy(() => import("@/pages/sie/ResearchPlanning"));
const SIEPublications     = lazy(() => import("@/pages/sie/PublicationRoadmap"));
const SIEGrantPlanner     = lazy(() => import("@/pages/sie/GrantPlanner"));
const SIECareerPlanner    = lazy(() => import("@/pages/sie/CareerPlanner"));
const SIEDailyAgenda      = lazy(() => import("@/pages/sie/DailyAgenda"));
const SIEWeeklyPlanner    = lazy(() => import("@/pages/sie/WeeklyPlanner"));
const SIEMissions         = lazy(() => import("@/pages/sie/ResearchMissions"));
const SIEMemory           = lazy(() => import("@/pages/sie/AIMemory"));
const SIERecommendations  = lazy(() => import("@/pages/sie/Recommendations"));
const SIEAutomations      = lazy(() => import("@/pages/sie/AutomationCenter"));
const SIEProgress         = lazy(() => import("@/pages/sie/ResearchProgress"));
const SIESettings         = lazy(() => import("@/pages/sie/SIESettings"));

// Phase VII — Academic Collaboration & Discovery Network — /network/*
const NetHome             = lazy(() => import("@/pages/network/DiscoveryHome"));
const NetPeople           = lazy(() => import("@/pages/network/PeopleDiscovery"));
const NetInstitutions     = lazy(() => import("@/pages/network/InstitutionDiscovery"));
const NetGroups           = lazy(() => import("@/pages/network/ResearchGroups"));
const NetTeaching         = lazy(() => import("@/pages/network/TeachingCommunities"));
const NetProjects         = lazy(() => import("@/pages/network/ProjectsDiscovery"));
const NetCollaborations   = lazy(() => import("@/pages/network/OpenCollaborations"));
const NetGrantTeams       = lazy(() => import("@/pages/network/GrantTeams"));
const NetConferences      = lazy(() => import("@/pages/network/ConferenceNetworking"));
const NetIndustry         = lazy(() => import("@/pages/network/IndustryPartners"));
const NetMentorship       = lazy(() => import("@/pages/network/MentorshipPlatform"));
const NetCommunities      = lazy(() => import("@/pages/network/Communities"));
const NetRecommendations  = lazy(() => import("@/pages/network/NetworkRecommendations"));
const NetSaved            = lazy(() => import("@/pages/network/SavedOpportunities"));
const NetActivity         = lazy(() => import("@/pages/network/ActivityCenter"));
const NetAnalytics        = lazy(() => import("@/pages/network/NetworkAnalytics"));
const NetSettings         = lazy(() => import("@/pages/network/NetworkSettings"));

// Phase VIII — Academic Services Ecosystem & Marketplace — /academic-marketplace/*
const MktHome             = lazy(() => import("@/pages/academic_marketplace/MarketplaceHome"));
const MktServices         = lazy(() => import("@/pages/academic_marketplace/ServiceBrowse"));
const MktServiceDetail    = lazy(() => import("@/pages/academic_marketplace/ServiceDetail"));
const MktServiceCreate    = lazy(() => import("@/pages/academic_marketplace/ServiceCreate"));
const MktProviders        = lazy(() => import("@/pages/academic_marketplace/ProviderBrowse"));
const MktProviderProfile  = lazy(() => import("@/pages/academic_marketplace/ProviderProfile"));
const MktProviderSetup    = lazy(() => import("@/pages/academic_marketplace/ProviderSetup"));
const MktProviderDash     = lazy(() => import("@/pages/academic_marketplace/ProviderDashboard"));
const MktOrderPlace       = lazy(() => import("@/pages/academic_marketplace/OrderPlace"));
const MktOrderDetail      = lazy(() => import("@/pages/academic_marketplace/OrderDetail"));
const MktOrderList        = lazy(() => import("@/pages/academic_marketplace/OrderList"));
const MktRating           = lazy(() => import("@/pages/academic_marketplace/RatingSubmit"));
const MktDisputeCenter    = lazy(() => import("@/pages/academic_marketplace/DisputeCenter"));
const MktDisputeDetail    = lazy(() => import("@/pages/academic_marketplace/DisputeDetail"));
const MktContract         = lazy(() => import("@/pages/academic_marketplace/ContractView"));
const MktWallet           = lazy(() => import("@/pages/academic_marketplace/WalletCenter"));
const MktRecommendations  = lazy(() => import("@/pages/academic_marketplace/Recommendations"));
const MktAdmin            = lazy(() => import("@/pages/academic_marketplace/AdminMarketplace"));

// Phase IX — Academic Knowledge Graph & Intelligence Platform — /akg/*
const AkgHome             = lazy(() => import("@/pages/akg/KnowledgeGraphHome"));
const AkgExplorer         = lazy(() => import("@/pages/akg/GraphExplorer"));
const AkgSearch           = lazy(() => import("@/pages/akg/EntitySearch"));
const AkgEntityDetail     = lazy(() => import("@/pages/akg/EntityDetail"));
const AkgTrends           = lazy(() => import("@/pages/akg/TrendDiscovery"));
const AkgAnalytics        = lazy(() => import("@/pages/akg/GraphAnalytics"));
const AkgRecommendations  = lazy(() => import("@/pages/akg/RecommendationHub"));
const AkgReasoning        = lazy(() => import("@/pages/akg/AIReasoning"));
const AkgSync             = lazy(() => import("@/pages/akg/SyncCenter"));
const AkgAdmin            = lazy(() => import("@/pages/akg/GraphAdmin"));

// Phase V — Institution Intelligence Platform — /institution-platform/*
const IIPExecutiveDashboard      = lazy(() => import("@/pages/institution_platform/ExecutiveDashboard"));
const IIPInstitutionHealth       = lazy(() => import("@/pages/institution_platform/InstitutionHealth"));
const IIPFacultyIntelligence     = lazy(() => import("@/pages/institution_platform/FacultyIntelligence"));
const IIPDepartmentIntelligence  = lazy(() => import("@/pages/institution_platform/DepartmentIntelligence"));
const IIPPublicationIntelligence = lazy(() => import("@/pages/institution_platform/PublicationIntelligence"));
const IIPGrantIntelligence       = lazy(() => import("@/pages/institution_platform/GrantIntelligence"));
const IIPCollaborationIntelligence = lazy(() => import("@/pages/institution_platform/CollaborationIntelligence"));
const IIPFinancialIntelligence   = lazy(() => import("@/pages/institution_platform/FinancialIntelligence"));
const IIPRiskIntelligence        = lazy(() => import("@/pages/institution_platform/RiskIntelligence"));
const IIPForecastCenter          = lazy(() => import("@/pages/institution_platform/ForecastCenter"));
const IIPBenchmarkCenter         = lazy(() => import("@/pages/institution_platform/BenchmarkCenter"));
const IIPInstitutionReports      = lazy(() => import("@/pages/institution_platform/InstitutionReports"));
const IIPAIExecutiveAssistant    = lazy(() => import("@/pages/institution_platform/AIExecutiveAssistant"));
const IIPStrategicPlanning       = lazy(() => import("@/pages/institution_platform/StrategicPlanning"));

function Protected({ children }) {
  return (
    <ProtectedRoute requireOnboarded={true}>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
      <UnreadProvider>
        <BrowserRouter>
          <Suspense fallback={null}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/verify-email" element={<VerifyEmail />} />
              <Route path="/verify-email-pending" element={<VerifyEmailPending />} />
              <Route path="/invite" element={<InvitationAccept />} />
              <Route path="/unsubscribed" element={<Unsubscribed />} />
              <Route path="/auth/google/callback" element={<GoogleCallback />} />
              <Route path="/settings/billing" element={<ProtectedRoute><AppShell><BillingCenter /></AppShell></ProtectedRoute>} />
              <Route path="/settings/security" element={<Protected><AccountSecurity /></Protected>} />
              {/* Admin Operating System — separate application, requires is_super_admin */}
              <Route path="/admin" element={<AdminProtectedRoute><AdminShell /></AdminProtectedRoute>}>
                <Route index element={<AdminCommandCenter />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="users/:uid" element={<AdminUserDetail />} />
                <Route path="audit" element={<AdminAudit />} />
                <Route path="security" element={<AdminSecurity />} />
                <Route path="email" element={<AdminEmailCenter />} />
                <Route path="analytics" element={<AdminAnalytics />} />
                <Route path="revenue" element={<AdminRevenuePage />} />
                <Route path="health" element={<AdminHealth />} />
                <Route path="reputation" element={<AdminReputation />} />
                <Route path="teaching-analytics" element={<AdminTeachingAnalytics />} />
                <Route path="subscriptions" element={<AdminSubscriptions />} />
                <Route path="errors" element={<AdminErrorCenter />} />
                <Route path="research" element={<AdminResearchGovernance />} />
                <Route path="database" element={<AdminDatabaseOps />} />
                <Route path="platform-auditor" element={<AdminPlatformAuditor />} />
                <Route path="promotions" element={<AdminPromotions />} />
                <Route path="communications" element={<AdminCommunications />} />
                {/* Phase XI — AOS Expansion */}
                <Route path="feature-flags-center" element={<AdminFeatureFlags />} />
                <Route path="jobs" element={<AdminJobsCenter />} />
                <Route path="api-monitor" element={<AdminApiMonitor />} />
                <Route path="storage" element={<AdminStorageGovernance />} />
                <Route path="institution-center" element={<AdminInstitutionCenter />} />
                <Route path="search" element={<AdminSearchObservatory />} />
                <Route path="data-quality" element={<AdminDataQuality />} />
                <Route path="releases" element={<AdminReleases />} />
                <Route path="support" element={<AdminSupportCenter />} />
                <Route path="research-integrity" element={<AdminResearchIntegrity />} />
                <Route path="command-map" element={<AdminCommandMap />} />
                <Route path="copilot" element={<AdminAICopilot />} />
                <Route path="account-security" element={<AdminAccountSecurity />} />
                <Route path="mfa" element={<AdminMFACenter />} />
                <Route path="security-hardening" element={<AdminSecurityHardening />} />
                {/* Phase XX — Research Reputation Center */}
                <Route path="reputation-center" element={<AdminReputationCenter />} />
                {/* Phase XXI — Recommendation Intelligence Center */}
                <Route path="recommendation-center" element={<AdminRecommendationCenter />} />
                {/* Phase XXII — Research Impact Intelligence Center */}
                <Route path="impact-center" element={<AdminImpactCenter />} />
                {/* Phase XXIII — AI OS Admin Center */}
                <Route path="ai-center" element={<AdminAICenter />} />
                {/* Phase XXV — Grant Collaboration Hub Admin */}
                <Route path="grant-hub" element={<AdminGrantHub />} />
                {/* Phase XXVII — Reviewer Marketplace Admin */}
                <Route path="reviewer-hub" element={<AdminReviewerHub />} />
                {/* Phase XXIX — Verification & Trust Admin */}
                <Route path="verification" element={<AdminVerification />} />
                {/* Trust & Verification Platform Admin */}
                <Route path="trust-center" element={<AdminTrustCenter />} />
                {/* Phase IV — Academic Integrity Engine Admin */}
                <Route path="integrity-center" element={<AdminIntegrityCenter />} />
                {/* Phase XXVI — Public Profiles Admin */}
                <Route path="profiles" element={<AdminProfiles />} />
                {/* Backward-compatible: old /admin root was AdminDashboard — still reachable at /admin/dashboard */}
                <Route path="dashboard" element={<AdminDashboard />} />
                <Route path="content" element={<AdminDashboard />} />
              </Route>
              <Route path="/for-institutions" element={<InstitutionsLanding />} />
              <Route path="/platform" element={<Platform />} />
              <Route path="/research" element={<ResearchLanding />} />
              <Route path="/ai-workspace" element={<AIWorkspaceLanding />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/about" element={<About />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="/resources/whats-new" element={<WhatsNew />} />
              <Route path="/resources/customer-stories" element={<CustomerStories />} />
              <Route path="/resources/blog" element={<ResourcesBlog />} />
              <Route path="/legal" element={<LegalCenter />} />
              <Route path="/terms" element={<Terms />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/gdpr" element={<GDPR />} />
              <Route path="/cookies" element={<Cookies />} />
              <Route path="/security" element={<Security />} />
              <Route path="/ai-policy" element={<AiPolicy />} />
              <Route path="/documentation" element={<Documentation />} />
              <Route path="/help-center" element={<HelpCenter />} />
              <Route path="/developers" element={<ApiPortal />} />
              <Route path="/status" element={<Status />} />
              <Route path="/onboarding" element={<ProtectedRoute requireOnboarded={false}><Onboarding /></ProtectedRoute>} />
              <Route path="/profile-setup" element={<ProtectedRoute requireOnboarded={true}><ProfileSetup /></ProtectedRoute>} />

              <Route path="/today"                  element={<Protected><Today                  /></Protected>} />
              <Route path="/recommendation-center" element={<Protected><RecommendationCenter /></Protected>} />
              <Route path="/copilot"               element={<Protected><Copilot               /></Protected>} />
              <Route path="/living-graph"          element={<Protected><LivingGraph          /></Protected>} />
              <Route path="/twin"                  element={<Protected><DigitalTwin          /></Protected>} />
              <Route path="/agent-workforce"       element={<Protected><AgentWorkforce       /></Protected>} />
              <Route path="/discover" element={<Protected><Discover /></Protected>} />
              <Route path="/collaborations" element={<Protected><Collaborations /></Protected>} />
              <Route path="/collaborations/new" element={<Protected><CreateCollaboration /></Protected>} />
              <Route path="/collaborations/my" element={<Protected><MyCollaborations /></Protected>} />
              <Route path="/collaborations/:id" element={<Protected><CollaborationDetail /></Protected>} />
              {/* Phase 2 — Academic Network & Teams */}
              <Route path="/teams" element={<Protected><Teams /></Protected>} />
              <Route path="/teams/create" element={<Protected><CreateTeam /></Protected>} />
              <Route path="/teams/:id" element={<Protected><TeamHome /></Protected>} />
              <Route path="/research-hub" element={<Protected><ResearchCommandCenter /></Protected>} />
              <Route path="/feed" element={<Protected><ResearchFeed /></Protected>} />
              <Route path="/profile" element={<Protected><Profile /></Protected>} />
              <Route path="/profile/:userId" element={<Protected><Profile /></Protected>} />
              <Route path="/academic-passport" element={<Protected><AcademicPassport /></Protected>} />
              <Route path="/projects" element={<Protected><Projects /></Protected>} />
              <Route path="/projects/:id" element={<Protected><ProjectDetail /></Protected>} />
              <Route path="/messages" element={<Protected><Messages /></Protected>} />
              <Route path="/messages/c/:conversationId" element={<Protected><Messages /></Protected>} />
              <Route path="/messages/:otherId" element={<Protected><Messages /></Protected>} />
              <Route path="/meetings" element={<Protected><Meetings /></Protected>} />
              <Route path="/meetings/:id" element={<Protected><MeetingDetail /></Protected>} />
              <Route path="/analytics" element={<Protected><Analytics /></Protected>} />
              <Route path="/ai-usage" element={<Protected><AIUsage /></Protected>} />
              <Route path="/marketplace" element={<Protected><Marketplace /></Protected>} />
              <Route path="/expertise" element={<Protected><ExpertiseRequests /></Protected>} />
              <Route path="/expertise/:id" element={<Protected><ExpertiseRequestDetail /></Protected>} />
              <Route path="/invitations" element={<Protected><Invitations /></Protected>} />
              <Route path="/institutions" element={<Protected><Institutions /></Protected>} />
              <Route path="/institutions/:id" element={<Protected><InstitutionDetail /></Protected>} />
              <Route path="/units/:id" element={<Protected><UnitDetail /></Protected>} />
              <Route path="/research-centers/:id" element={<Protected><UnitDetail /></Protected>} />
              <Route path="/labs/:id" element={<Protected><UnitDetail /></Protected>} />
              <Route path="/institution/analytics" element={<Protected><InstitutionAnalytics /></Protected>} />
              <Route path="/institution/departments" element={<Protected><Departments /></Protected>} />
              <Route path="/institution/departments/:did" element={<Protected><DepartmentDetail /></Protected>} />
              <Route path="/faculty/:id" element={<Protected><FacultyProfile /></Protected>} />
              <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
              <Route path="/settings" element={<Protected><Settings /></Protected>} />

              {/* Phase II */}
              <Route path="/journals" element={<Protected><Journals /></Protected>} />
              <Route path="/journals/:id" element={<Protected><JournalDetail /></Protected>} />
              <Route path="/conferences" element={<Protected><Conferences /></Protected>} />
              <Route path="/conferences/:id" element={<Protected><ConferenceDetail /></Protected>} />
              <Route path="/funding" element={<Protected><Funding /></Protected>} />
              <Route path="/funding/:id" element={<Protected><FundingDetail /></Protected>} />
              <Route path="/grants" element={<Protected><Grants /></Protected>} />
              <Route path="/grants/:id" element={<Protected><GrantDetail /></Protected>} />
              <Route path="/grant-applications" element={<Protected><GrantApplications /></Protected>} />
              <Route path="/grant-applications/:id" element={<Protected><GrantApplicationDetail /></Protected>} />
              <Route path="/workspaces" element={<Protected><Workspaces /></Protected>} />
              <Route path="/workspaces/:id" element={<Protected><WorkspaceDetail /></Protected>} />
              <Route path="/manuscripts" element={<Protected><Manuscripts /></Protected>} />
              <Route path="/manuscripts/:id" element={<Protected><ManuscriptDetail /></Protected>} />
              <Route path="/reviews" element={<Protected><Reviews /></Protected>} />
              <Route path="/manuscript-review" element={<Protected><ManuscriptReview /></Protected>} />
              <Route path="/literature-review" element={<Protected><LiteratureReview /></Protected>} />
              <Route path="/ai/abstract" element={<Protected><AbstractGenerator /></Protected>} />
              <Route path="/ai/rewrite" element={<Protected><AIRewriting /></Protected>} />
              <Route path="/research-gap-finder" element={<Protected><ResearchGapFinder /></Protected>} />
              <Route path="/research-design-advisor" element={<Protected><ResearchDesignAdvisor /></Protected>} />
              <Route path="/statistical-review" element={<Protected><StatisticalReview /></Protected>} />
              <Route path="/citation-monitoring" element={<Protected><CitationMonitoring /></Protected>} />
              <Route path="/citations" element={<Protected><Citations /></Protected>} />
              <Route path="/citations/:id" element={<Protected><CitationDetail /></Protected>} />
              <Route path="/research-impact" element={<Protected><ResearchImpact /></Protected>} />
              <Route path="/collaboration-intelligence" element={<Protected><CollaborationIntelligence /></Protected>} />
              <Route path="/collaboration-requests" element={<Protected><CollaborationRequests /></Protected>} />
              <Route path="/publication-hub" element={<Protected><PublicationHub /></Protected>} />
              <Route path="/publications" element={<Navigate to="/publication-hub" replace />} />
              <Route path="/repository" element={<Protected><Repository /></Protected>} />

              {/* Teaching Hub — Production */}
              <Route path="/teaching" element={<Protected><TeachingHub /></Protected>} />
              <Route path="/teaching/lesson-planner" element={<Protected><LessonPlanner /></Protected>} />
              <Route path="/teaching/lessons/:lessonId" element={<Protected><LessonPlanDetail /></Protected>} />
              <Route path="/teaching/portfolio" element={<Protected><TeachingPortfolio /></Protected>} />
              <Route path="/teaching/assessment-builder" element={<Protected><AssessmentBuilder /></Protected>} />
              <Route path="/teaching/assessments/:assessmentId" element={<Protected><AssessmentDetail /></Protected>} />
              <Route path="/teaching/workspaces" element={<Protected><TeachingWorkspaceList /></Protected>} />
              <Route path="/teaching/workspaces/:workspaceId" element={<Protected><TeachingWorkspaceDetail /></Protected>} />
              <Route path="/teaching/analytics" element={<Protected><TeachingAnalytics /></Protected>} />

              {/* Phase XX — Research Reputation & Leaderboards */}
              <Route path="/reputation" element={<Protected><ReputationAnalytics /></Protected>} />
              <Route path="/leaderboards" element={<Protected><Leaderboards /></Protected>} />
              {/* Phase XXI — Academic Recommendations */}
              <Route path="/recommendations" element={<Protected><Recommendations /></Protected>} />
              {/* Phase XXII — Research Impact Dashboard */}
              <Route path="/impact-dashboard" element={<Protected><ImpactDashboard /></Protected>} />
              {/* Phase XXIII — Synaptiq AI OS */}
              <Route path="/ai" element={<ProtectedRoute requireOnboarded={true}><AIAssistant /></ProtectedRoute>} />
              {/* Phase 5 — Research AI Suite Gateway & Credit Economy */}
              <Route path="/ai-suite"   element={<Protected><AISuite /></Protected>} />
              <Route path="/ai-credits" element={<Protected><AICredits /></Protected>} />
              {/* Phase XXIV — Institution Hub */}
              <Route path="/institution-hub" element={<Protected><InstitutionHub /></Protected>} />
              <Route path="/institution-hub/:id" element={<Protected><InstitutionProfile /></Protected>} />
              <Route path="/institution-hub/:id/admin" element={<Protected><InstitutionAdminConsole /></Protected>} />
              <Route path="/institution-leaderboards" element={<Protected><InstitutionLeaderboards /></Protected>} />
              {/* Phase XXV — Grant Collaboration Hub */}
              <Route path="/grant-collaboration-hub" element={<Protected><GrantCollaborationHub /></Protected>} />
              <Route path="/grant-hub/:id" element={<Protected><GrantOpportunityWorkspace /></Protected>} />
              {/* Phase XXVI — Public Research Profiles (no auth, standalone) */}
              <Route path="/researcher/:slug" element={<ResearcherProfile />} />
              <Route path="/researchers" element={<Protected><Researchers /></Protected>} />
              {/* Phase XXVII — Reviewer Marketplace */}
              <Route path="/reviewer-marketplace" element={<Protected><ReviewerMarketplace /></Protected>} />
              <Route path="/review-workspace/:id" element={<Protected><ReviewWorkspace /></Protected>} />
              {/* Phase XXVIII — Institution Analytics Center */}
              <Route path="/institution-analytics/:id" element={<Protected><InstitutionAnalyticsCenter /></Protected>} />
              {/* Phase XXIX — Verification & Trust */}
              <Route path="/verification" element={<Protected><VerificationCenter /></Protected>} />

              {/* Trust & Verification Platform — /trust/* */}
              <Route path="/trust" element={<Protected><TrustOverview /></Protected>} />
              <Route path="/trust/my-verifications" element={<Protected><MyVerifications /></Protected>} />
              <Route path="/trust/requests" element={<Protected><VerificationRequests /></Protected>} />
              <Route path="/trust/passport" element={<Navigate to="/academic-passport" replace />} />
              <Route path="/trust/score" element={<Protected><TrustScore /></Protected>} />
              <Route path="/trust/integrity" element={<Protected><IntegrityReport /></Protected>} />
              <Route path="/trust/institution" element={<Protected><InstitutionVerification /></Protected>} />
              <Route path="/trust/publications" element={<Protected><PublicationVerification /></Protected>} />
              <Route path="/trust/reviewer" element={<Protected><ReviewerVerification /></Protected>} />
              <Route path="/trust/grants" element={<Protected><GrantVerification /></Protected>} />
              <Route path="/trust/history" element={<Protected><VerificationHistory /></Protected>} />
              <Route path="/trust/settings" element={<Protected><VerificationSettings /></Protected>} />

              {/* Research Timeline & Academic Activity Engine — /timeline/* */}
              <Route path="/timeline"            element={<Protected><ResearchTimeline /></Protected>} />
              <Route path="/timeline/analytics"  element={<Protected><TimelineAnalytics /></Protected>} />
              <Route path="/timeline/public/:userId" element={<PublicTimeline />} />

              {/* Academic Integrity & Research Verification Engine — /integrity/* */}
              <Route path="/integrity"           element={<Protected><IntegrityCenter /></Protected>} />

              {/* Phase VI — Synaptiq Intelligence Engine — /sie/* */}
              <Route path="/sie"               element={<Protected><SIECommandCenter /></Protected>} />
              <Route path="/sie/goals"         element={<Protected><SIEGoalManager /></Protected>} />
              <Route path="/sie/planning"      element={<Protected><SIEPlanning /></Protected>} />
              <Route path="/sie/publications"  element={<Protected><SIEPublications /></Protected>} />
              <Route path="/sie/grants"        element={<Protected><SIEGrantPlanner /></Protected>} />
              <Route path="/sie/career"        element={<Protected><SIECareerPlanner /></Protected>} />
              <Route path="/sie/daily"         element={<Protected><SIEDailyAgenda /></Protected>} />
              <Route path="/sie/weekly"        element={<Protected><SIEWeeklyPlanner /></Protected>} />
              <Route path="/sie/missions"      element={<Protected><SIEMissions /></Protected>} />
              <Route path="/sie/memory"        element={<Protected><SIEMemory /></Protected>} />
              <Route path="/sie/recommendations" element={<Protected><SIERecommendations /></Protected>} />
              <Route path="/sie/automations"   element={<Protected><SIEAutomations /></Protected>} />
              <Route path="/sie/progress"      element={<Protected><SIEProgress /></Protected>} />
              <Route path="/sie/settings"      element={<Protected><SIESettings /></Protected>} />

              {/* Phase VII — Academic Collaboration & Discovery Network — /network/* */}
              <Route path="/network"                    element={<Protected><NetHome /></Protected>} />
              <Route path="/network/people"             element={<Protected><NetPeople /></Protected>} />
              <Route path="/network/institutions"       element={<Protected><NetInstitutions /></Protected>} />
              <Route path="/network/groups"             element={<Protected><NetGroups /></Protected>} />
              <Route path="/network/teaching"           element={<Protected><NetTeaching /></Protected>} />
              <Route path="/network/projects"           element={<Protected><NetProjects /></Protected>} />
              <Route path="/network/collaborations"     element={<Protected><NetCollaborations /></Protected>} />
              <Route path="/network/grant-teams"        element={<Protected><NetGrantTeams /></Protected>} />
              <Route path="/network/conferences"        element={<Protected><NetConferences /></Protected>} />
              <Route path="/network/industry"           element={<Protected><NetIndustry /></Protected>} />
              <Route path="/network/mentorship"         element={<Protected><NetMentorship /></Protected>} />
              <Route path="/network/communities"        element={<Protected><NetCommunities /></Protected>} />
              <Route path="/network/recommendations"    element={<Protected><NetRecommendations /></Protected>} />
              <Route path="/network/saved"              element={<Protected><NetSaved /></Protected>} />
              <Route path="/network/activity"           element={<Protected><NetActivity /></Protected>} />
              <Route path="/network/analytics"          element={<Protected><NetAnalytics /></Protected>} />
              <Route path="/network/settings"           element={<Protected><NetSettings /></Protected>} />

              {/* Phase VIII — Academic Services Ecosystem & Marketplace — /academic-marketplace/* */}
              <Route path="/academic-marketplace"                          element={<Protected><MktHome /></Protected>} />
              <Route path="/academic-marketplace/services"                 element={<Protected><MktServices /></Protected>} />
              <Route path="/academic-marketplace/services/create"          element={<Protected><MktServiceCreate /></Protected>} />
              <Route path="/academic-marketplace/services/:id"             element={<Protected><MktServiceDetail /></Protected>} />
              <Route path="/academic-marketplace/providers"                element={<Protected><MktProviders /></Protected>} />
              <Route path="/academic-marketplace/providers/:id"            element={<Protected><MktProviderProfile /></Protected>} />
              <Route path="/academic-marketplace/provider/setup"           element={<Protected><MktProviderSetup /></Protected>} />
              <Route path="/academic-marketplace/dashboard"                element={<Protected><MktProviderDash /></Protected>} />
              <Route path="/academic-marketplace/order/:id"                element={<Protected><MktOrderPlace /></Protected>} />
              <Route path="/academic-marketplace/orders"                   element={<Protected><MktOrderList /></Protected>} />
              <Route path="/academic-marketplace/orders/:id"               element={<Protected><MktOrderDetail /></Protected>} />
              <Route path="/academic-marketplace/rate/:id"                 element={<Protected><MktRating /></Protected>} />
              <Route path="/academic-marketplace/disputes"                 element={<Protected><MktDisputeCenter /></Protected>} />
              <Route path="/academic-marketplace/disputes/:id"             element={<Protected><MktDisputeDetail /></Protected>} />
              <Route path="/academic-marketplace/contracts/:id"            element={<Protected><MktContract /></Protected>} />
              <Route path="/academic-marketplace/wallet"                   element={<Protected><MktWallet /></Protected>} />
              <Route path="/academic-marketplace/recommendations"          element={<Protected><MktRecommendations /></Protected>} />
              <Route path="/academic-marketplace/admin"                    element={<Protected><MktAdmin /></Protected>} />

              {/* Phase IX — Academic Knowledge Graph & Intelligence Platform — /akg/* */}
              <Route path="/akg"                    element={<Protected><AkgHome /></Protected>} />
              <Route path="/akg/explorer"           element={<Protected><AkgExplorer /></Protected>} />
              <Route path="/akg/search"             element={<Protected><AkgSearch /></Protected>} />
              <Route path="/akg/entity/:entityId"   element={<Protected><AkgEntityDetail /></Protected>} />
              <Route path="/akg/trends"             element={<Protected><AkgTrends /></Protected>} />
              <Route path="/akg/analytics"          element={<Protected><AkgAnalytics /></Protected>} />
              <Route path="/akg/recommendations"    element={<Protected><AkgRecommendations /></Protected>} />
              <Route path="/akg/reasoning"          element={<Protected><AkgReasoning /></Protected>} />
              <Route path="/akg/sync"               element={<Protected><AkgSync /></Protected>} />
              <Route path="/akg/admin"              element={<Protected><AkgAdmin /></Protected>} />

              {/* Phase V — Institution Intelligence Platform — /institution-platform/* */}
              <Route path="/institution-platform"               element={<Protected><IIPExecutiveDashboard /></Protected>} />
              <Route path="/institution-platform/health"        element={<Protected><IIPInstitutionHealth /></Protected>} />
              <Route path="/institution-platform/faculty"       element={<Protected><IIPFacultyIntelligence /></Protected>} />
              <Route path="/institution-platform/departments"   element={<Protected><IIPDepartmentIntelligence /></Protected>} />
              <Route path="/institution-platform/publications"  element={<Protected><IIPPublicationIntelligence /></Protected>} />
              <Route path="/institution-platform/grants"        element={<Protected><IIPGrantIntelligence /></Protected>} />
              <Route path="/institution-platform/collaborations" element={<Protected><IIPCollaborationIntelligence /></Protected>} />
              <Route path="/institution-platform/financial"     element={<Protected><IIPFinancialIntelligence /></Protected>} />
              <Route path="/institution-platform/risks"         element={<Protected><IIPRiskIntelligence /></Protected>} />
              <Route path="/institution-platform/forecasts"     element={<Protected><IIPForecastCenter /></Protected>} />
              <Route path="/institution-platform/benchmarks"    element={<Protected><IIPBenchmarkCenter /></Protected>} />
              <Route path="/institution-platform/reports"       element={<Protected><IIPInstitutionReports /></Protected>} />
              <Route path="/institution-platform/assistant"     element={<Protected><IIPAIExecutiveAssistant /></Protected>} />
              <Route path="/institution-platform/strategic"     element={<Protected><IIPStrategicPlanning /></Protected>} />

              <Route path="/search"  element={<Protected><GlobalSearch /></Protected>} />
              <Route path="*"       element={<NotFound />} />
            </Routes>
          </Suspense>
          <CookieConsentBanner />
          <UpgradeModal />
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </UnreadProvider>
    </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
