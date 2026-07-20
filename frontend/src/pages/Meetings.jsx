/**
 * Meetings — Research meetings, doctoral supervision sessions, collaborations
 * and AI meeting summaries. Production feature backed by /api/meetings.
 */
import React, { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  CalendarDays, Clock, ListChecks, Sparkles, Plus, Upload, LayoutList, CalendarRange,
} from "lucide-react";
import { StatCard, StatGrid } from "@/components/ds/StatCard";
import { Button } from "@/components/ds/Button";
import { NavTabs } from "@/components/ds/NavTabs";
import { FilterBar } from "@/components/ds/SearchBar";
import { SkeletonCard, SkeletonTable } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { ResearchLayout } from "@/layouts";
import { TYPE } from "@/lib/tokens";

import { MeetingTimeline } from "@/components/meetings/MeetingTimeline";
import { MeetingCalendar } from "@/components/meetings/MeetingCalendar";
import { MeetingCategoryCard } from "@/components/meetings/MeetingCategoryCard";
import { ActionItemsPanel } from "@/components/meetings/ActionItemsPanel";
import { TodayAgenda } from "@/components/meetings/TodayAgenda";
import { MiniCalendar } from "@/components/meetings/MiniCalendar";
import { QuickNotes } from "@/components/meetings/QuickNotes";
import { PinnedMeetings } from "@/components/meetings/PinnedMeetings";
import { CreateMeetingModal } from "@/components/meetings/CreateMeetingModal";
import { ImportIcsModal } from "@/components/meetings/ImportIcsModal";

import {
  useMeetingsList, useMeetingKpis, useMeetingCategories, useMeetingCalendar,
} from "@/hooks/useMeetings";

const STATUS_FILTERS = [
  { label: "Upcoming", value: "upcoming" },
  { label: "Today", value: "today" },
  { label: "This week", value: "this_week" },
  { label: "This month", value: "this_month" },
  { label: "Past", value: "past" },
];

export default function Meetings() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("timeline"); // timeline | calendar | action-items
  const [statusFilter, setStatusFilter] = useState("upcoming");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [createDefaultType, setCreateDefaultType] = useState(null);
  const [createDefaultDate, setCreateDefaultDate] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(new Date());

  const listFilters = useMemo(() => ({
    status: statusFilter,
    q: search || undefined,
  }), [statusFilter, search]);

  const { data: meetings, loading: meetingsLoading, error: meetingsError, reload: reloadMeetings } = useMeetingsList(listFilters);
  const { data: kpis, loading: kpisLoading, reload: reloadKpis } = useMeetingKpis();
  const { data: categories, loading: categoriesLoading, reload: reloadCategories } = useMeetingCategories();
  const monthKey = `${calendarMonth.getFullYear()}-${String(calendarMonth.getMonth() + 1).padStart(2, "0")}`;
  const { data: calendarData, loading: calendarLoading } = useMeetingCalendar(monthKey);

  const refreshAll = useCallback(() => {
    reloadMeetings();
    reloadKpis();
    reloadCategories();
  }, [reloadMeetings, reloadKpis, reloadCategories]);

  const openCreate = (defaultType, defaultDate) => {
    setCreateDefaultType(defaultType || null);
    setCreateDefaultDate(defaultDate || null);
    setCreateOpen(true);
  };

  const highlightDates = useMemo(() => {
    const src = calendarData?.meetings || meetings || [];
    return src.map((m) => {
      const d = new Date(m.start_at);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    });
  }, [calendarData, meetings]);

  return (
    <ResearchLayout
      title="Meetings"
      subtitle="Manage research meetings, doctoral supervision sessions, collaborations and AI meeting summaries."
      actions={
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant="ghost" onClick={() => setImportOpen(true)}>
            <Upload size={13} /> Import Calendar
          </Button>
          <Button onClick={() => openCreate()}>
            <Plus size={14} /> New Meeting
          </Button>
        </div>
      }
      nav={
        <NavTabs
          tabs={[
            { id: "timeline", label: "Timeline", icon: LayoutList },
            { id: "calendar", label: "Calendar", icon: CalendarRange },
            { id: "action-items", label: "Action Items", icon: ListChecks },
          ]}
          active={tab}
          onChange={setTab}
        />
      }
    >

        {/* KPI row */}
        <StatGrid cols={4} className="mb-6">
          {kpisLoading || !kpis ? (
            Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} rows={1} />)
          ) : (
            <>
              <StatCard
                label="Upcoming Meetings"
                value={kpis.upcoming_meetings}
                sub="Scheduled ahead"
                icon={<CalendarDays />}
                trend={kpis.trends?.upcoming_meetings}
                highlight
              />
              <StatCard
                label="Today's Meetings"
                value={kpis.todays_meetings}
                sub="Happening today"
                icon={<Clock />}
              />
              <StatCard
                label="Pending Action Items"
                value={kpis.pending_action_items}
                sub="Awaiting completion"
                icon={<ListChecks />}
              />
              <StatCard
                label="AI Summaries Generated"
                value={kpis.ai_summaries_generated}
                sub="Across all meetings"
                icon={<Sparkles />}
                trend={kpis.trends?.ai_summaries_generated}
              />
            </>
          )}
        </StatGrid>

        {tab === "action-items" ? (
          <ActionItemsPanel />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 24, alignItems: "flex-start" }}>
            {/* Left column */}
            <div>
              {tab === "timeline" && (
                <>
                  <FilterBar
                    search={{ value: search, onChange: setSearch, placeholder: "Search meetings, participants, projects…" }}
                    filters={STATUS_FILTERS.map((f) => ({ ...f, active: statusFilter === f.value }))}
                    onFilter={setStatusFilter}
                  />
                  <div style={{ marginTop: 18 }}>
                    {meetingsLoading && <SkeletonTable rows={5} />}
                    {!meetingsLoading && meetingsError && (
                      <ErrorState message="Could not load meetings" onRetry={reloadMeetings} />
                    )}
                    {!meetingsLoading && !meetingsError && (
                      <MeetingTimeline meetings={meetings || []} onEdit={(m) => navigate(`/meetings/${m.id}`)} onCreate={() => openCreate()} />
                    )}
                  </div>
                </>
              )}

              {tab === "calendar" && (
                <>
                  {calendarLoading && !calendarData ? (
                    <SkeletonTable rows={6} />
                  ) : (
                    <MeetingCalendar
                      meetings={calendarData?.meetings || []}
                      month={calendarMonth}
                      onMonthChange={setCalendarMonth}
                      onDayClick={(dt) => openCreate(null, dt)}
                    />
                  )}
                </>
              )}
            </div>

            {/* Right rail */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <TodayAgenda meetings={meetings || []} />
              <MiniCalendar highlightDates={highlightDates} onSelectDate={(dt) => openCreate(null, dt)} />
              <PinnedMeetings meetings={meetings || []} />
              <QuickNotes />
            </div>
          </div>
        )}

        {/* Meeting Categories */}
        <div style={{ marginTop: 40 }}>
          <div style={{ ...TYPE.section, marginBottom: 14 }}>Meeting Categories</div>
          {categoriesLoading || !categories ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
              {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} rows={2} />)}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
              {categories.map((cat) => (
                <MeetingCategoryCard key={cat.meeting_type} category={cat} onQuickCreate={openCreate} />
              ))}
            </div>
          )}
        </div>

      <CreateMeetingModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        defaultType={createDefaultType}
        defaultDate={createDefaultDate}
        onCreated={refreshAll}
      />
      <ImportIcsModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={refreshAll}
      />
    </ResearchLayout>
  );
}
