import { Vault } from 'lucide-react';

/** variant="light" for dark backgrounds (the auth showcase panel, the admin sidebar). */
export default function Logo({ className = '', variant = 'dark' }) {
  const isLight = variant === 'light';
  const textColor = isLight ? 'text-white' : 'text-slate-950';
  const accentColor = isLight ? 'text-teal-400' : 'text-teal-600';

  return (
    <div className={`flex items-center gap-2.5 font-semibold ${textColor} ${className}`}>
      <span className="keep-colors grid size-8 place-items-center rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 text-white shadow-md ring-1 shadow-teal-600/30 ring-white/25 transition-transform ring-inset hover:scale-105">
        <Vault className="size-[18px]" aria-hidden="true" />
      </span>
      <span className="text-[17px] font-bold tracking-tight">
        Trust<span className={accentColor}>Share</span>
      </span>
    </div>
  );
}
