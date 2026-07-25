import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, MessageSquare, MoreHorizontal, RotateCcw, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar } from "@/components/ds/Avatar";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Textarea";
import { Dropdown, DropdownItem } from "@/components/ds/Dropdown";
import { Badge } from "@/components/ds/Badge";
import { EmptyState } from "@/components/ds/EmptyState";
import { TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BRD, EMERALD, RADIUS_MD } from "@/lib/tokens";
import { transition } from "@/lib/motion";

function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

function CommentRow({ comment, replies, currentUserId, onReply, onResolve, onDelete }) {
  const [replying, setReplying] = useState(false);
  const [replyBody, setReplyBody] = useState("");
  const isAuthor = comment.author_id === currentUserId;

  return (
    <div style={{ padding: "12px 0", borderBottom: `1px solid ${BRD}` }}>
      <div className="flex items-start gap-2.5">
        <Avatar name={comment.author_name} size={26} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="flex items-center gap-2">
            <span style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>{comment.author_name}</span>
            <span style={{ fontSize: 11, color: TEXT_MUTED }}>{timeAgo(comment.created_at)}</span>
            {comment.resolved && <Badge color={EMERALD} size="sm">Resolved</Badge>}
          </div>
          <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginTop: 4, whiteSpace: "pre-wrap" }}>
            {comment.content}
          </div>
          <div className="flex items-center gap-3" style={{ marginTop: 6 }}>
            <button
              onClick={() => setReplying((r) => !r)}
              style={{ fontSize: 11, fontWeight: 600, color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              Reply
            </button>
            <button
              onClick={() => onResolve(comment, !comment.resolved)}
              style={{ fontSize: 11, fontWeight: 600, color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: 3 }}
            >
              {comment.resolved ? <><RotateCcw size={10} strokeWidth={2} /> Reopen</> : <><CheckCircle2 size={10} strokeWidth={2} /> Resolve</>}
            </button>
            {isAuthor && (
              <Dropdown
                align="left"
                width={130}
                trigger={
                  <button style={{ color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex" }} aria-label="More comment actions">
                    <MoreHorizontal size={13} strokeWidth={1.75} />
                  </button>
                }
              >
                <DropdownItem icon={Trash2} destructive onClick={() => onDelete(comment)}>Delete</DropdownItem>
              </Dropdown>
            )}
          </div>
          {replying && (
            <div className="flex items-start gap-2" style={{ marginTop: 8 }}>
              <Textarea
                autoFocus
                rows={2}
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                placeholder="Write a reply…"
                wrapperClassName="flex-1"
              />
              <Button
                size="sm"
                onClick={() => { onReply(comment.id, replyBody); setReplyBody(""); setReplying(false); }}
                disabled={!replyBody.trim()}
              >
                Reply
              </Button>
            </div>
          )}
        </div>
      </div>

      {replies.length > 0 && (
        <div style={{ marginLeft: 34, marginTop: 8, paddingLeft: 12, borderLeft: `2px solid ${BRD}` }}>
          {replies.map((r) => (
            <div key={r.id} className="flex items-start gap-2.5" style={{ marginBottom: 10 }}>
              <Avatar name={r.author_name} size={22} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="flex items-center gap-2">
                  <span style={{ fontSize: 12, fontWeight: 700, color: TEXT_PRIMARY }}>{r.author_name}</span>
                  <span style={{ fontSize: 10.5, color: TEXT_MUTED }}>{timeAgo(r.created_at)}</span>
                </div>
                <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 2, whiteSpace: "pre-wrap" }}>{r.content}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * CommentThread — reusable threaded discussion for any commentable entity,
 * backed by the generic /api/comments endpoints (target_type + target_id).
 * Real create/reply/resolve/reopen/delete, all persisted server-side —
 * nothing here is local-only state.
 */
export default function CommentThread({ targetType, targetId, workspaceMembers = [] }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/comments", { params: { target_type: targetType, target_id: targetId } });
      setComments(data?.comments || []);
    } catch (e) {
      setComments([]);
    } finally {
      setLoading(false);
    }
  }, [targetType, targetId]);

  useEffect(() => { if (targetId) load(); }, [targetId, load]);

  const post = async (content, parentCommentId) => {
    if (!content.trim()) return;
    setPosting(true);
    try {
      // Naive @mention resolution against known workspace members — resolves
      // "@Full Name" to that member's user id so they get a real notification.
      const mentions = workspaceMembers
        .filter((m) => content.includes(`@${m.full_name}`))
        .map((m) => m.id);
      await api.post("/comments", {
        target_type: targetType, target_id: targetId, content,
        parent_comment_id: parentCommentId || null, mentions,
      });
      await load();
    } catch (e) {
      toast.error("Failed to post comment");
    } finally {
      setPosting(false);
    }
  };

  const resolve = async (comment, resolved) => {
    setComments((prev) => prev.map((c) => c.id === comment.id ? { ...c, resolved } : c));
    try {
      await api.patch(`/comments/${comment.id}`, { resolved });
    } catch (e) {
      toast.error("Failed to update comment");
      load();
    }
  };

  const remove = async (comment) => {
    setComments((prev) => prev.filter((c) => c.id !== comment.id));
    try {
      await api.delete(`/comments/${comment.id}`);
    } catch (e) {
      toast.error("Failed to delete comment");
      load();
    }
  };

  const topLevel = comments.filter((c) => !c.parent_comment_id);
  const repliesOf = (id) => comments.filter((c) => c.parent_comment_id === id);

  return (
    <div>
      <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
        <MessageSquare size={13} strokeWidth={1.75} style={{ color: TEXT_MUTED }} />
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: TEXT_MUTED }}>
          {comments.length} comment{comments.length === 1 ? "" : "s"}
        </span>
      </div>

      {loading ? (
        <div style={{ fontSize: 12, color: TEXT_MUTED }} role="status">Loading comments…</div>
      ) : topLevel.length === 0 ? (
        <EmptyState icon={<MessageSquare />} title="No comments yet" description="Start the discussion below." size="sm" />
      ) : (
        <div>
          {topLevel.map((c) => (
            <CommentRow
              key={c.id}
              comment={c}
              replies={repliesOf(c.id)}
              currentUserId={user?.id}
              onReply={(parentId, replyBody) => post(replyBody, parentId)}
              onResolve={resolve}
              onDelete={remove}
            />
          ))}
        </div>
      )}

      <div className="flex items-start gap-2" style={{ marginTop: 14 }}>
        <Textarea
          rows={2}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment… (@name to mention)"
          wrapperClassName="flex-1"
        />
        <Button size="sm" onClick={() => { post(body); setBody(""); }} loading={posting} disabled={!body.trim()}>
          Post
        </Button>
      </div>
    </div>
  );
}
