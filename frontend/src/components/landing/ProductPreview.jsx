import { BadgeCheck, FolderOpen, Search, ShieldCheck, Trash2, Upload } from 'lucide-react';

import { fileIcon } from '../../utils/format';

const ROWS = [
  { name: 'Security_Audit_Report.pdf', size: '2.8 MB', date: 'Today', category: 'document' },
  { name: 'Financial_Projections_2026.xlsx', size: '940 KB', date: 'Today', category: 'spreadsheet' },
  { name: 'Architecture_Presentation.pptx', size: '6.2 MB', date: 'Yesterday', category: 'presentation' },
  { name: 'Encryption_Key_Diagram.png', size: '1.9 MB', date: '14 Nov', category: 'image' },
];

/** Decorative dashboard mock-up for the landing page hero (HTML, so it's sharp at any size). */
export default function ProductPreview() {
  return (
    <div className="relative" aria-hidden="true">
      <div className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-gradient-to-br from-teal-200/50 via-emerald-100/40 to-cyan-100/50 blur-2xl" />

      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-2xl shadow-teal-950/10">
        {/* window bar */}
        <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/60 px-4 py-3">
          <span className="size-2.5 rounded-full bg-rose-400" />
          <span className="size-2.5 rounded-full bg-amber-400" />
          <span className="size-2.5 rounded-full bg-emerald-400" />
          <div className="ml-3 flex flex-1 items-center gap-2 rounded-full bg-white px-3 py-1 text-xs text-slate-400 shadow-2xs ring-1 ring-slate-200/60">
            <Search className="size-3 text-slate-400" /> Search encrypted files
          </div>
        </div>

        <div className="flex">
          {/* sidebar */}
          <div className="hidden w-38 shrink-0 flex-col gap-1 border-r border-slate-100 bg-slate-50/30 p-3 text-xs sm:flex">
            <span className="flex items-center gap-2 rounded-lg bg-teal-50 px-2.5 py-1.5 font-semibold text-teal-800">
              <FolderOpen className="size-3.5 text-teal-600" /> My Files
            </span>
            <span className="flex items-center gap-2 px-2.5 py-1.5 text-slate-500">
              <Trash2 className="size-3.5" /> Trash
            </span>
            <div className="mt-auto pt-10">
              <div className="h-1.5 rounded-full bg-slate-100">
                <div className="h-1.5 w-2/5 rounded-full bg-teal-500" />
              </div>
              <p className="mt-1 text-[10px] font-medium text-slate-400">410 MB of 2 GB used</p>
            </div>
          </div>

          {/* file list */}
          <div className="flex-1 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-bold text-slate-800">Workspace Files</p>
              <span className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-xs">
                <Upload className="size-3" /> Upload
              </span>
            </div>
            <ul className="divide-y divide-slate-100 text-xs">
              {ROWS.map((row) => {
                const { Icon, color } = fileIcon(row.category);
                return (
                  <li key={row.name} className="flex items-center gap-3 py-2.5">
                    <Icon className={`size-4 shrink-0 ${color}`} />
                    <span className="flex-1 truncate font-medium text-slate-700">{row.name}</span>
                    <span className="hidden w-16 text-right text-slate-400 sm:block">
                      {row.size}
                    </span>
                    <span className="w-16 text-right text-slate-400">{row.date}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>

      {/* floating badges */}
      <div className="absolute -bottom-5 -left-4 flex items-center gap-2.5 rounded-xl border border-slate-200/90 bg-white px-3.5 py-2.5 text-xs shadow-xl sm:-left-8">
        <BadgeCheck className="size-4.5 text-emerald-600" />
        <span>
          <span className="block font-semibold text-slate-800">AES-256-GCM Active</span>
          <span className="block text-[11px] text-slate-400">Unique DEK per file</span>
        </span>
      </div>
      <div className="absolute -top-4 -right-3 flex items-center gap-2 rounded-xl border border-slate-200/90 bg-white px-3.5 py-2.5 text-xs shadow-xl sm:-right-6">
        <ShieldCheck className="size-4.5 text-teal-600" />
        <span className="font-semibold text-slate-800">2-Step Verification Active</span>
      </div>
    </div>
  );
}
