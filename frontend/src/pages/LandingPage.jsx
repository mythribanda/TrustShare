import {
  ArrowRight,
  Check,
  FileCheck2,
  FolderTree,
  History,
  KeyRound,
  Link2,
  LockKeyhole,
  ShieldCheck,
  UploadCloud,
  UserPlus,
  UsersRound,
} from 'lucide-react';
import { Link } from 'react-router';

import { useAuth } from '../auth/useAuth';
import ProductPreview from '../components/landing/ProductPreview';
import Logo from '../components/Logo';

const GITHUB_URL = 'https://github.com/mythribanda/TrustShare';

// Core security architectural specs
const FACTS = [
  { value: 'AES-256', label: 'envelope encryption per file' },
  { value: 'Zero-Trust', label: 'byte-level content inspection' },
  { value: 'SHA-256', label: 'tamper-evident audit chain' },
  { value: '15 min', label: 'rotating session tokens' },
];

const FEATURES = [
  {
    icon: FileCheck2,
    title: 'Verified Binary Inspection',
    text: 'Every upload is examined by true binary magic bytes, rejecting malicious programs disguised as documents.',
    tone: 'bg-emerald-50 text-emerald-600',
  },
  {
    icon: FolderTree,
    title: 'Hierarchical File Management',
    text: 'Organize assets with nested directories, instant search, fast tag filtering, and reversible trash recovery.',
    tone: 'bg-teal-50 text-teal-600',
  },
  {
    icon: UsersRound,
    title: 'Role-Based Governance (RBAC)',
    text: 'Strict separation of privileges across Admin, User, and Guest roles with zero client-side trust.',
    tone: 'bg-indigo-50 text-indigo-600',
  },
  {
    icon: KeyRound,
    title: 'Multi-Factor TOTP & Backup Keys',
    text: 'Hardware-grade two-step authentication compatible with Google Authenticator and one-time emergency keys.',
    tone: 'bg-amber-50 text-amber-600',
  },
  {
    icon: History,
    title: 'Cryptographic Audit Trail',
    text: 'Complete auditability recording user IDs, client IPs, device fingerprints, and timestamps for every event.',
    tone: 'bg-rose-50 text-rose-600',
  },
  {
    icon: Link2,
    title: 'Encrypted Sharing & Expiring Links',
    text: 'Envelope encryption with per-file AES-256 keys, revocable time-bound links, and optional password gates.',
    tone: 'bg-cyan-50 text-cyan-600',
  },
];

const STEPS = [
  {
    icon: UserPlus,
    title: 'Initialize Workspace',
    text: 'Create your account in seconds, fortified with bcrypt hashing and optional two-factor verification.',
  },
  {
    icon: UploadCloud,
    title: 'Deposit Encrypted Assets',
    text: 'Drag and drop documents. Every payload is verified by magic bytes and enveloped with an isolated key.',
  },
  {
    icon: FolderTree,
    title: 'Collaborate with Precision',
    text: 'Share folders, generate time-expiring download links, set quotas, and inspect real-time audit logs.',
  },
];

const SECURITY = [
  'Adaptive bcrypt hashing ensuring credentials are never exposed or stored in cleartext',
  'Isolated AES-256-GCM data encryption keys generated dynamically per file',
  'Strict server-side capability and permission verification on all routes',
  'Automated session token rotation with instant multi-device revocation',
  'Tamper-evident hash-chained audit logging for regulatory compliance',
  'Isolated secure vaults with secondary secret protection for sensitive files',
];

/** Public home page at "/". Logged-in visitors get a shortcut to their files. */
export default function LandingPage() {
  const { status } = useAuth();
  const loggedIn = status === 'authenticated';

  return (
    <div className="min-h-screen bg-white text-slate-800">
      <Header loggedIn={loggedIn} />

      {/* ---------- hero ---------- */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[38rem] bg-gradient-to-b from-teal-50/80 via-emerald-50/30 to-white" />
        <div className="mx-auto grid max-w-6xl items-center gap-16 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-2 lg:pt-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-teal-200/60 bg-teal-50/80 px-3.5 py-1 text-xs font-semibold text-teal-800 shadow-xs">
              <LockKeyhole className="size-3.5 text-teal-600" aria-hidden="true" />
              High-Assurance Encrypted Storage
            </span>
            <h1 className="mt-6 text-4xl leading-tight font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-[3.25rem]">
              Confidential file sharing.{' '}
              <span className="bg-gradient-to-r from-teal-600 via-emerald-600 to-cyan-600 bg-clip-text text-transparent">
                Cryptographic trust built in.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600">
              TrustShare delivers enterprise-grade file security and seamless collaboration. Every
              asset is validated at the binary level, encrypted with unique AES-256-GCM keys, and
              tracked by an immutable audit trail.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to={loggedIn ? '/dashboard' : '/register'}
                className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white shadow-lg shadow-teal-600/25 transition-all hover:bg-teal-700 hover:shadow-teal-700/30"
              >
                {loggedIn ? 'Enter Workspace' : 'Get Started Free'}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              {!loggedIn && (
                <Link
                  to="/login"
                  className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50"
                >
                  Sign In
                </Link>
              )}
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
              {['Byte-Level Validation', 'Granular RBAC Security', 'Cryptographic Audit Trail'].map(
                (item) => (
                  <li key={item} className="flex items-center gap-2">
                    <Check className="size-4 text-teal-600" aria-hidden="true" />
                    <span>{item}</span>
                  </li>
                ),
              )}
            </ul>
          </div>
          <ProductPreview />
        </div>
      </section>

      {/* ---------- facts ---------- */}
      <section className="border-y border-slate-200/60 bg-slate-50/70">
        <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-10 sm:px-6 lg:grid-cols-4">
          {FACTS.map((fact) => (
            <div key={fact.label}>
              <dt className="text-2xl font-bold tracking-tight text-slate-900">{fact.value}</dt>
              <dd className="mt-1 text-sm text-slate-500">{fact.label}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ---------- features ---------- */}
      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <SectionTitle
          eyebrow="Platform Capabilities"
          title="Engineered for security. Designed for simplicity."
          text="A modern document workspace where compliance, encryption, and ergonomics meet."
        />
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text, tone }) => (
            <article
              key={title}
              className="group rounded-2xl border border-slate-200/80 bg-white p-6 shadow-xs transition duration-200 hover:-translate-y-1 hover:border-teal-200 hover:shadow-xl hover:shadow-teal-900/5"
            >
              <div className="flex items-center justify-between">
                <span className={`grid size-11 place-items-center rounded-xl ${tone}`}>
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-semibold text-teal-700">
                  Active
                </span>
              </div>
              <h3 className="mt-5 font-bold text-slate-900 group-hover:text-teal-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ---------- how it works ---------- */}
      <section id="how-it-works" className="scroll-mt-20 bg-slate-50/70 py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <SectionTitle
            eyebrow="Workflow"
            title="Up and running in three straightforward steps"
            text="Immediate zero-trust document security through your modern web browser."
          />
          <ol className="mt-14 grid gap-8 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <li
                key={title}
                className="relative rounded-2xl border border-slate-200/80 bg-white p-6 shadow-xs"
              >
                <span className="absolute top-6 right-6 text-4xl font-extrabold text-slate-100">
                  0{index + 1}
                </span>
                <span className="grid size-11 place-items-center rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/30">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 font-bold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------- security ---------- */}
      <section id="security" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl bg-slate-950 px-6 py-14 text-white shadow-2xl sm:px-12">
          <div className="pointer-events-none absolute -top-24 -right-24 size-80 rounded-full bg-teal-500/25 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -left-24 size-80 rounded-full bg-emerald-500/20 blur-3xl" />
          <div className="relative grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="grid size-12 place-items-center rounded-xl bg-white/10 text-teal-300 ring-1 ring-white/15">
                <ShieldCheck className="size-6" aria-hidden="true" />
              </span>
              <h2 className="mt-6 text-3xl font-extrabold tracking-tight sm:text-4xl">
                Cryptographic security at the core. Not an afterthought.
              </h2>
              <p className="mt-4 leading-relaxed text-slate-300">
                TrustShare validates identities and fine-grained permissions against the server on
                every request. Client-side controls are only the surface — every boundary is
                verified.
              </p>
            </div>
            <ul className="grid gap-3.5 sm:grid-cols-2">
              {SECURITY.map((item) => (
                <li
                  key={item}
                  className="flex gap-3 rounded-xl bg-white/5 p-4 text-sm text-slate-200 ring-1 ring-white/10"
                >
                  <Check className="mt-0.5 size-4 shrink-0 text-teal-400" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ---------- call to action ---------- */}
      <section className="mx-auto max-w-6xl px-4 pb-24 text-center sm:px-6">
        <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Ready to protect your sensitive files?
        </h2>
        <p className="mt-3 text-lg text-slate-600">
          Create a secure workspace and safeguard your collaboration today.
        </p>
        <Link
          to={loggedIn ? '/dashboard' : '/register'}
          className="mt-8 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-6 py-3.5 font-semibold text-white shadow-lg shadow-teal-600/30 transition hover:bg-teal-700"
        >
          {loggedIn ? 'Open Workspace' : 'Create Free Account'}
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </section>

      <Footer />
    </div>
  );
}

function Header({ loggedIn }) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-8 px-4 sm:px-6">
        <Link to="/" aria-label="TrustShare home">
          <Logo />
        </Link>
        <nav className="hidden gap-6 text-sm font-medium text-slate-600 md:flex">
          <a href="#features" className="transition hover:text-teal-700">
            Features
          </a>
          <a href="#how-it-works" className="transition hover:text-teal-700">
            Workflow
          </a>
          <a href="#security" className="transition hover:text-teal-700">
            Security Architecture
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2.5">
          {loggedIn ? (
            <Link
              to="/files"
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
            >
              Open Workspace
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function SectionTitle({ eyebrow, title, text }) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-xs font-bold tracking-widest text-teal-600 uppercase">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
        {title}
      </h2>
      <p className="mt-4 leading-relaxed text-slate-600">{text}</p>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-200/80 bg-slate-50/50">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:px-6">
        <Logo />
        <p>© 2026 TrustShare · Encrypted File Sharing & Collaboration</p>
        <div className="flex gap-5 font-medium">
          <Link to="/status" className="transition hover:text-teal-700">
            System Status
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-teal-700"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
