/**
 * RecentFilesWidget — dashboard widget showing recent files across all the
 * user's workspaces/projects/manuscripts.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../lib/api";
import { FileText, FileSpreadsheet, FilePlus, FileImage, FolderOpen } from "lucide-react";
import { NAVY } from "@/lib/tokens";

const TYPE_ICON = {
  pdf: FileText, docx: FileText, doc: FileText,
  xlsx: FileSpreadsheet, xls: FileSpreadsheet, csv: FileSpreadsheet,
  pptx: FilePlus, ppt: FilePlus, zip: FilePlus,
  png: FileImage, jpg: FileImage, jpeg: FileImage, webp: FileImage, gif: FileImage,
};
const ENT_PATH = { workspace: "workspaces", project: "projects", manuscript: "manuscripts" };

export default function RecentFilesWidget() {
  const [files, setFiles] = useState(null);
  useEffect(() => {
    api.get("/files/recent?limit=8").then(({ data }) => setFiles(data || [])).catch(() => setFiles([]));
  }, []);
  if (files === null || files.length === 0) return null;
  return (
    <div className="border border-slate-200 bg-white p-4" data-testid="recent-files-widget">
      <div className="flex items-center gap-2 mb-3">
        <FolderOpen size={12} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">Recent files</div>
      </div>
      <div className="space-y-2">
        {files.map((f) => {
          const Icon = TYPE_ICON[f.ext] || FileText;
          return (
            <Link
              key={f.id}
              to={`/${ENT_PATH[f.entity_kind]}/${f.entity_id}`}
              className="flex items-center gap-2 text-xs hover:text-[#0F2847]"
              data-testid={`recent-file-${f.id}`}
            >
              <Icon size={11} strokeWidth={1.5} className="text-slate-500 shrink-0" />
              <span className="flex-1 truncate">{f.filename}</span>
              <span className="font-mono text-[10px] text-slate-400 shrink-0">v{f.version}</span>
              <span className="text-[10px] font-mono text-slate-400 capitalize shrink-0">{f.entity_kind}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
