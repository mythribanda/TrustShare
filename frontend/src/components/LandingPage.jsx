import React, { useState } from 'react';
import {
  ShieldCheck,
  LockKeyhole,
  Folder,
  Files,
  Share2,
  KeyRound,
  Activity,
  HardDrive,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Database,
  Eye,
  Clock3,
  ShieldAlert,
  Fingerprint,
  FileLock2
} from 'lucide-react';

const features = [
  {
    icon: FileLock2,
    title: 'Encrypted file storage',
    description: 'Files are encrypted with AES-256-GCM before they are written to the configured storage backend.'
  },
  {
    icon: Share2,
    title: 'Controlled sharing',
    description: 'Create share links with expiry and download limits, revoke links, or share directly with another account.'
  },
  {
    icon: KeyRound,
    title: 'Account protection',
    description: 'Add authenticator-based two-step verification, manage backup codes, and review active sessions.'
  },
  {
    icon: Folder,
    title: 'Organized workspace',
    description: 'Keep files in folders, search your workspace, and manage uploads from one place.'
  },
  {
    icon: Activity,
    title: 'Security visibility',
    description: 'Review available activity and security events, with additional reporting for administrator accounts.'
  },
  {
    icon: LockKeyhole,
    title: 'Private vault',
    description: 'Keep selected files behind a separate vault password and an additional encryption layer.'
  }
];

const faqs = [
  {
    question: 'Does the landing page show my actual files?',
    answer: 'No file names, file counts, checksums, or activity are fabricated on this page. Sign in to see the files and account data returned for your own workspace.'
  },
  {
    question: 'How are files protected?',
    answer: 'The current security branch includes AES-256-GCM file encryption and per-file key metadata. Configure your own master key and storage settings before using it with important data.'
  },
  {
    question: 'Can I share files with other people?',
    answer: 'The app includes expiring and revocable share links and direct sharing features. Access is subject to the configured backend and its authorization checks.'
  },
  {
    question: 'Is the service status shown here live?',
    answer: 'This landing page does not guess whether the API or its dependencies are healthy. Open the application and check the backend health endpoint or application error messages for current status.'
  }
];

function Brand({ compact = false }) {
  return (
    <a href="#top" className="flex items-center gap-3" aria-label="TrustShare home">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-500 text-white shadow-lg shadow-indigo-500/25">
        <ShieldCheck size={23} />
      </span>
      <span className={compact ? 'text-lg font-bold tracking-tight text-white' : 'text-xl font-bold tracking-tight text-white'}>
        Trust<span className="text-indigo-300">Share</span>
      </span>
    </a>
  );
}

export default function LandingPage({ onGetStarted, onSignIn }) {
  const [activeFaq, setActiveFaq] = useState(0);

  return (
    <main id="top" className="min-h-screen overflow-hidden bg-[#080d19] text-slate-100">
      <div className="border-b border-white/10 bg-white/[0.03]">
        <div className="mx-auto flex max-w-7xl items-center justify-center gap-2 px-4 py-2 text-center text-xs text-slate-300 sm:text-sm">
          <span className="h-2 w-2 rounded-full bg-indigo-400" />
          Secure file storage and sharing, with control in your hands
        </div>
      </div>

      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#080d19]/90 backdrop-blur-xl">
        <div className="mx-auto flex h-[76px] max-w-7xl items-center justify-between gap-5 px-4 sm:px-6 lg:px-8">
          <Brand />
          <nav className="hidden items-center gap-7 text-sm text-slate-300 md:flex">
            <a className="transition hover:text-white" href="#features">Features</a>
            <a className="transition hover:text-white" href="#security">Security</a>
            <a className="transition hover:text-white" href="#faq">FAQ</a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <button onClick={onSignIn} className="rounded-xl px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white sm:px-4">
              Sign in
            </button>
            <button onClick={onGetStarted} className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-3.5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:bg-indigo-400 sm:px-5">
              Get started <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </header>

      <section className="relative">
        <div className="pointer-events-none absolute left-1/2 top-0 h-[460px] w-[780px] -translate-x-1/2 rounded-full bg-indigo-600/15 blur-[130px]" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 pb-20 pt-20 sm:px-6 sm:pb-28 sm:pt-28 lg:grid-cols-[1.04fr_.96fr] lg:px-8 lg:pt-32">
          <div>
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-indigo-300/20 bg-indigo-400/10 px-3.5 py-2 text-xs font-medium text-indigo-200 sm:text-sm">
              <ShieldCheck size={15} /> Privacy-first file collaboration
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold leading-[1.1] tracking-[-0.045em] text-white sm:text-6xl lg:text-[68px]">
              Your files.
              <span className="block bg-gradient-to-r from-indigo-300 via-violet-200 to-sky-300 bg-clip-text text-transparent">Your access.</span>
              Your control.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-slate-300 sm:text-lg">
              Store, organize, and share important files with encryption and access controls designed to help keep your information private.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <button onClick={onGetStarted} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-3.5 text-sm font-semibold text-white shadow-xl shadow-indigo-500/20 transition hover:-translate-y-0.5 hover:bg-indigo-400">
                Create your workspace <ArrowRight size={17} />
              </button>
              <button onClick={onSignIn} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08]">
                Sign in to TrustShare
              </button>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-5 gap-y-3 text-xs text-slate-400 sm:text-sm">
              <span className="inline-flex items-center gap-2"><CheckCircle2 size={15} className="text-emerald-300" /> Encrypted storage</span>
              <span className="inline-flex items-center gap-2"><CheckCircle2 size={15} className="text-emerald-300" /> Expiring share links</span>
              <span className="inline-flex items-center gap-2"><CheckCircle2 size={15} className="text-emerald-300" /> Optional MFA</span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[540px]">
            <div className="absolute -inset-5 rounded-[32px] bg-gradient-to-br from-indigo-500/15 via-violet-500/5 to-sky-500/10 blur-2xl" />
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0d1526] shadow-2xl shadow-black/40">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="grid h-9 w-9 place-items-center rounded-lg bg-indigo-400/15 text-indigo-200"><Files size={18} /></span>
                  <div>
                    <p className="text-sm font-semibold text-white">Your workspace</p>
                    <p className="mt-0.5 text-xs text-slate-400">A private place for your files</p>
                  </div>
                </div>
                <span className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-slate-400">Preview</span>
              </div>
              <div className="p-5 sm:p-6">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                    <span className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-400/10 text-emerald-200"><FileLock2 size={18} /></span>
                    <p className="mt-4 text-sm font-semibold text-white">Encrypted files</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">Protection at rest</p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                    <span className="grid h-9 w-9 place-items-center rounded-lg bg-sky-400/10 text-sky-200"><Share2 size={18} /></span>
                    <p className="mt-4 text-sm font-semibold text-white">Controlled sharing</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">Expiry and revocation</p>
                  </div>
                </div>
                <div className="mt-4 rounded-xl border border-dashed border-white/15 bg-black/10 px-5 py-8 text-center">
                  <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-slate-300"><Folder size={22} /></span>
                  <p className="mt-4 text-sm font-semibold text-white">Your files will appear here</p>
                  <p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-slate-400">This is an illustrative preview, not sample account data. Sign in to view your real workspace.</p>
                  <button onClick={onSignIn} className="mt-5 inline-flex items-center gap-2 rounded-lg border border-indigo-300/25 bg-indigo-400/10 px-4 py-2 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-400/15">
                    Open workspace <ArrowRight size={14} />
                  </button>
                </div>
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] p-3.5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-violet-400/10 text-violet-200"><Fingerprint size={18} /></span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-200">Security controls</p>
                    <p className="mt-1 text-[11px] leading-4 text-slate-400">MFA, session management, and audit visibility</p>
                  </div>
                  <LockKeyhole size={16} className="ml-auto shrink-0 text-slate-500" />
                </div>
              </div>
              <div className="border-t border-white/10 bg-white/[0.025] px-5 py-3 text-[11px] text-slate-500">
                Interface preview only · no fabricated file records or live status claims
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="border-y border-white/[0.08] bg-white/[0.02] py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">Built for everyday security</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Everything important, in one place.</h2>
            <p className="mt-4 text-sm leading-7 text-slate-400 sm:text-base">A straightforward workspace for file management, sharing, and account security.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, description }) => (
              <article key={title} className="group rounded-2xl border border-white/10 bg-[#0c1424] p-6 transition duration-200 hover:-translate-y-1 hover:border-indigo-300/30 hover:bg-[#101a2e] sm:p-7">
                <span className="grid h-11 w-11 place-items-center rounded-xl border border-indigo-300/15 bg-indigo-400/10 text-indigo-200 transition group-hover:bg-indigo-400/15"><Icon size={21} /></span>
                <h3 className="mt-5 text-lg font-semibold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-7 text-slate-400">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="security" className="py-20 sm:py-24">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">Security by design</p>
            <h2 className="mt-4 max-w-xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">Protection should be built in — not bolted on.</h2>
            <p className="mt-5 max-w-xl text-sm leading-7 text-slate-400 sm:text-base">TrustShare brings file encryption, controlled access, and account security tools together. Security still depends on correct configuration, strong secrets, and deployment practices.</p>
            <button onClick={onGetStarted} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-indigo-100">
              Get started <ArrowRight size={16} />
            </button>
          </div>
          <div className="grid gap-3">
            <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-300/10 text-emerald-200"><FileLock2 size={21} /></span>
              <div><h3 className="font-semibold text-white">Authenticated encryption</h3><p className="mt-1 text-sm leading-6 text-slate-400">AES-256-GCM helps protect file confidentiality and detect unauthorized changes to encrypted content.</p></div>
            </div>
            <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-sky-300/10 text-sky-200"><Clock3 size={21} /></span>
              <div><h3 className="font-semibold text-white">Time-limited sharing</h3><p className="mt-1 text-sm leading-6 text-slate-400">Share links can be configured with expiration and download limits, and can be revoked.</p></div>
            </div>
            <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-violet-300/10 text-violet-200"><ShieldAlert size={21} /></span>
              <div><h3 className="font-semibold text-white">Account and audit controls</h3><p className="mt-1 text-sm leading-6 text-slate-400">Authenticator-based MFA, session revocation, and security-event views help users review account activity.</p></div>
            </div>
            <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-amber-300/10 text-amber-200"><HardDrive size={21} /></span>
              <div><h3 className="font-semibold text-white">Storage configuration matters</h3><p className="mt-1 text-sm leading-6 text-slate-400">Use a strong master key and verify the configured storage provider before storing important documents.</p></div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-white/[0.08] bg-white/[0.02] py-20">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[.8fr_1.2fr] lg:items-center lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">Simple workflow</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">From upload to sharing, without the clutter.</h2>
            <p className="mt-4 text-sm leading-7 text-slate-400">Use the workspace to manage your files and account controls in a few clear steps.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-[#0c1424] p-5"><span className="text-xs font-semibold text-indigo-300">01 / STORE</span><h3 className="mt-3 font-semibold text-white">Upload files</h3><p className="mt-2 text-sm leading-6 text-slate-400">Add supported documents to your private workspace.</p></div>
            <div className="rounded-xl border border-white/10 bg-[#0c1424] p-5"><span className="text-xs font-semibold text-indigo-300">02 / ORGANIZE</span><h3 className="mt-3 font-semibold text-white">Keep it tidy</h3><p className="mt-2 text-sm leading-6 text-slate-400">Use folders and search to find what you need.</p></div>
            <div className="rounded-xl border border-white/10 bg-[#0c1424] p-5"><span className="text-xs font-semibold text-indigo-300">03 / SHARE</span><h3 className="mt-3 font-semibold text-white">Control access</h3><p className="mt-2 text-sm leading-6 text-slate-400">Choose a sharing method and review its access settings.</p></div>
          </div>
        </div>
      </section>

      <section id="faq" className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <div className="mb-10 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">Clear answers</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Frequently asked questions</h2>
          </div>
          <div className="space-y-3">
            {faqs.map((faq, index) => (
              <article key={faq.question} className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.025]">
                <button onClick={() => setActiveFaq(activeFaq === index ? -1 : index)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-semibold text-white sm:px-6">
                  {faq.question}
                  <ChevronDown size={17} className={`shrink-0 text-slate-400 transition-transform ${activeFaq === index ? 'rotate-180' : ''}`} />
                </button>
                {activeFaq === index && <p className="border-t border-white/10 px-5 pb-5 pt-4 text-sm leading-7 text-slate-400 sm:px-6">{faq.answer}</p>}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 sm:px-6 sm:pb-24 lg:px-8">
        <div className="relative mx-auto max-w-6xl overflow-hidden rounded-3xl border border-indigo-300/20 bg-gradient-to-br from-indigo-500/20 via-[#111b32] to-[#0d1525] px-6 py-12 text-center sm:px-12 sm:py-16">
          <div className="pointer-events-none absolute left-1/2 top-0 h-64 w-96 -translate-x-1/2 rounded-full bg-indigo-400/10 blur-3xl" />
          <span className="relative mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-indigo-200/20 bg-indigo-300/10 text-indigo-100"><ShieldCheck size={28} /></span>
          <h2 className="relative mt-6 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Make space for the work that matters.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-300 sm:text-base">Create a workspace, keep your files organized, and decide how access is shared.</p>
          <div className="relative mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <button onClick={onGetStarted} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-indigo-400">Create an account <ArrowRight size={16} /></button>
            <button onClick={onSignIn} className="rounded-xl border border-white/15 bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-slate-100 transition hover:bg-white/[0.08]">I already have an account</button>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-black/10">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Brand compact />
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            <a href="#features" className="transition hover:text-slate-300">Features</a>
            <a href="#security" className="transition hover:text-slate-300">Security</a>
            <a href="#faq" className="transition hover:text-slate-300">FAQ</a>
          </div>
          <span>TrustShare · Secure file management and sharing</span>
        </div>
      </footer>
    </main>
  );
}
