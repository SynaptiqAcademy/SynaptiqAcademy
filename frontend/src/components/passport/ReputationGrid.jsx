import React from "react";
import ReputationCard from "@/components/reputation/ReputationCard";

/**
 * ReputationGrid — thin wrapper around the existing ReputationCard, which
 * already breaks down Research / Teaching / Collaboration (community) scores,
 * badges, and level progress. Reused as-is rather than rebuilt.
 */
export function ReputationGrid({ reputation, onSyncOpenAlex, syncing }) {
  if (!reputation) return null;
  return (
    <ReputationCard
      reputation={reputation}
      isMe
      onSyncOpenAlex={onSyncOpenAlex}
      syncing={syncing}
    />
  );
}

export default ReputationGrid;
