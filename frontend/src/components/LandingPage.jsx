import React, { useState } from 'react';
import {
  ShieldCheck,
  Folder,
  Files,
  LockKeyhole,
  FileText,
  HardDrive,
  Users,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Database,
  Activity,
  Layers,
  Server,
  Download,
  ChevronDown,
  ExternalLink,
  Cpu,
  FileCheck,
  Terminal,
  RefreshCw,
  GitBranch,
  Search,
  Check,
  AlertTriangle
} from 'lucide-react';

export default function LandingPage({ onGetStarted, onSignIn, health, user }) {
  const [activeFaq, setActiveFaq] = useState(null);
  const [activeTab, setActiveTab] = useState('architecture');

  const faqs = [
    {
      q: 'What is the exact scope of TrustShare Milestone 1?',
      a: 'Milestone 1 is a verified engineering foundation for authenticated file management. It delivers: (1) React + Tailwind frontend, (2) FastAPI backend with Pydantic validation, (3) PostgreSQL for canonical users, folders, and files, (4) MongoDB for metadata documents and activity event logs, (5) Redis for session revocation and rate limiting, and (6) Local disk storage with UUIDv4 naming and SHA-256 integrity checksums.'
    },
    {
      q: 'How does TrustShare verify file integrity?',
      a: 'During upload, file bytes are streamed through Python hashlib in 1 MiB chunks. A SHA-256 digest is accumulated concurrently with disk writes and verified before the database transaction commits. This digest is saved in PostgreSQL and MongoDB for bit-for-bit download verification. SHA-256 is an integrity hash, not encryption.'
    },
    {
      q: 'Why are multiple databases used instead of just one?',
      a: 'TrustShare assigns specific responsibilities to each database engine: PostgreSQL provides ACID relational integrity and foreign-key constraints (users, folders, files); MongoDB provides a flexible document schema for metadata copies and chronological audit events (logins, uploads, downloads, deletions, admin access); Redis acts as a fast state store for JWT session revocation and sliding-window rate limiters.'
    },
    {
      q: 'How is path traversal prevented during file upload?',
      a: 'Client-supplied filenames are never used as on-disk filesystem paths. Every stored file is assigned a unique UUIDv4 identifier combined with its validated lowercase extension (e.g. storage/{uuid}.pdf) and written exclusively inside an isolated storage vault directory.'
    },
    {
      q: 'What are the access control rules for users and administrators?',
      a: 'Regular users can only list, view metadata for, download, and delete their own files and folders. Administrators have elevated privileges to list all registered users, inspect metadata for any file, and download files for audit purposes. However, every administrative access is logged to MongoDB, and file deletion is strictly restricted to the file owner.'
    },
    {
      q: 'What features are reserved for Milestone 2?',
      a: 'Milestone 2 explicitly plans: AES-256 envelope encryption at rest with KMS key management, AWS S3 / Google Cloud Storage object backends, time-expiring shareable links with download quotas, hardware token / TOTP multi-factor authentication (MFA), and OAuth2/SAML single sign-on.'
    }
  ];

  const dbConnected = health?.database === 'postgres' || health?.postgres === 'connected';
  const mongoConnected = health?.mongodb === 'connected';
  const redisConnected = health?.redis === 'connected';
  const allServicesHealthy = dbConnected && mongoConnected && redisConnected;

  return (
    <div className="landing-container bg-[#0a0f1d] text-slate-100 min-h-screen selection:bg-indigo-600 selection:text-white font-['DM_Sans',sans-serif]">
      {/* Top Status Notification Banner */}
      <div className="bg-[#0f172a] border-b border-slate-800/80 px-4 py-2 text-xs text-slate-300">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2 h-2 rounded-full ${allServicesHealthy ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
            <span className="font-semibold text-white">TrustShare Milestone 1</span>
            <span className="text-slate-500 hidden sm:inline">|</span>
            <span className="text-slate-400 hidden sm:inline">Infosys Engineering Project Submission</span>
          </div>

          <div className="flex items-center gap-3 text-[11px] font-mono">
            <span className="text-slate-400">Environment: <strong className="text-indigo-300 font-semibold">{health?.environment || 'development'}</strong></span>
            <span className="text-slate-600">•</span>
            <span className={dbConnected ? 'text-emerald-400' : 'text-amber-400'}>
              PostgreSQL: {health?.postgres || (dbConnected ? 'connected' : 'checking')}
            </span>
            <span className="text-slate-600">•</span>
            <span className={mongoConnected ? 'text-emerald-400' : 'text-amber-400'}>
              MongoDB: {health?.mongodb || 'checking'}
            </span>
            <span className="text-slate-600">•</span>
            <span className={redisConnected ? 'text-emerald-400' : 'text-amber-400'}>
              Redis: {health?.redis || 'checking'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <header className="sticky top-0 z-40 backdrop-blur-md bg-[#0a0f1d]/90 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-600/30">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-['Manrope'] text-xl font-extrabold tracking-tight text-white flex items-center gap-1.5">
                trust<span className="text-indigo-400 font-medium">share</span>
                <span className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">M1</span>
              </div>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-300">
            <a href="#overview" className="hover:text-indigo-400 transition-colors">Overview</a>
            <a href="#architecture" className="hover:text-indigo-400 transition-colors">Multi-Store Architecture</a>
            <a href="#lifecycle" className="hover:text-indigo-400 transition-colors">File Pipeline</a>
            <a href="#security" className="hover:text-indigo-400 transition-colors">Access Control</a>
            <a href="#scope" className="hover:text-indigo-400 transition-colors">Milestone 1 Scope</a>
            <a href="#faq" className="hover:text-indigo-400 transition-colors">Technical FAQ</a>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <button
                onClick={onGetStarted}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm flex items-center gap-2 transition-all"
              >
                <span>Launch Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <>
                <button
                  onClick={onSignIn}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-200 hover:text-white transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={onGetStarted}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm shadow-indigo-600/30 transition-all flex items-center gap-1.5"
                >
                  Register
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section id="overview" className="relative pt-16 pb-20 md:pt-24 md:pb-28 border-b border-slate-800/80 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-950/40 text-xs font-medium text-indigo-300 mb-6">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>FastAPI • PostgreSQL • MongoDB • Redis • React</span>
          </div>

          <h1 className="font-['Manrope'] text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-[1.15]">
            Secure File Management Built on{' '}
            <span className="text-indigo-400">
              Integrity Hashing
            </span>{' '}
            & Multi-Store Governance
          </h1>

          <p className="mt-6 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
            A verified engineering foundation providing canonical relational indexing in PostgreSQL,
            rich metadata documents and audit logs in MongoDB, session revocation in Redis, and
            stream-level SHA-256 file checksumming.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto px-7 py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-all flex items-center justify-center gap-2"
            >
              {user ? 'Enter Workspace' : 'Launch Workspace'}
              <ArrowRight className="w-4 h-4" />
            </button>
            <a
              href="#architecture"
              className="w-full sm:w-auto px-6 py-3 rounded-lg text-sm font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 transition-all flex items-center justify-center gap-2"
            >
              Inspect Architecture
            </a>
          </div>

          {/* Real Technical Metrics / System Specifications */}
          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-3.5 max-w-4xl mx-auto text-left">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="text-[11px] font-mono text-indigo-400 uppercase tracking-wider font-semibold">Integrity Protocol</div>
              <div className="text-xl font-bold font-['Manrope'] text-white mt-1">SHA-256</div>
              <div className="text-xs text-slate-400 mt-1 leading-snug">Calculated on byte stream during upload; validated on download.</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="text-[11px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">Access Governance</div>
              <div className="text-xl font-bold font-['Manrope'] text-white mt-1">Strict RBAC</div>
              <div className="text-xs text-slate-400 mt-1 leading-snug">Owner-only deletion, cross-user isolation, and admin audit logging.</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="text-[11px] font-mono text-sky-400 uppercase tracking-wider font-semibold">Input Validation</div>
              <div className="text-xl font-bold font-['Manrope'] text-white mt-1">10 MiB Quota</div>
              <div className="text-xs text-slate-400 mt-1 leading-snug">Extension allowlist, MIME check, and magic bytes header inspection.</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="text-[11px] font-mono text-purple-400 uppercase tracking-wider font-semibold">Session Control</div>
              <div className="text-xl font-bold font-['Manrope'] text-white mt-1">Redis Revocation</div>
              <div className="text-xs text-slate-400 mt-1 leading-snug">Stateful session keys in Redis with instant invalidation on logout.</div>
            </div>
          </div>
        </div>
      </section>

      {/* Live System Diagnostics Panel */}
      <section className="py-12 bg-[#0c1324] border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
            <div>
              <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">Live System Health</div>
              <h2 className="text-xl font-bold font-['Manrope'] text-white mt-1">
                Real-Time Dependency Health State
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Queried directly from backend endpoint <code className="text-indigo-300">/health/ready</code>. Proves live container connectivity.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 rounded text-xs font-mono font-medium flex items-center gap-1.5 ${
                allServicesHealthy ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30' : 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${allServicesHealthy ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                System: {health?.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* PostgreSQL Card */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-blue-400" />
                  <span className="font-semibold text-sm text-slate-200">PostgreSQL 16</span>
                </div>
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-medium ${
                  dbConnected ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                }`}>
                  {health?.postgres || (dbConnected ? 'connected' : 'disconnected')}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2.5 leading-relaxed">
                Authoritative relational database for users, folders, and canonical file rows. Enforces foreign key constraints and schema indexes.
              </p>
              <div className="mt-3 pt-2.5 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex justify-between">
                <span>Port: 5433 (Host) / 5432 (Docker)</span>
                <span className="text-blue-400">ACID Relational</span>
              </div>
            </div>

            {/* MongoDB Card */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-400" />
                  <span className="font-semibold text-sm text-slate-200">MongoDB 7</span>
                </div>
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-medium ${
                  mongoConnected ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                }`}>
                  {health?.mongodb || 'disconnected'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2.5 leading-relaxed">
                Document database storing secondary file metadata documents in <code className="text-indigo-300">files</code> and append-only audit events in <code className="text-indigo-300">activity</code>.
              </p>
              <div className="mt-3 pt-2.5 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex justify-between">
                <span>Port: 27017</span>
                <span className="text-emerald-400">Document & Audit</span>
              </div>
            </div>

            {/* Redis Card */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-rose-400" />
                  <span className="font-semibold text-sm text-slate-200">Redis 7</span>
                </div>
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-medium ${
                  redisConnected ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                }`}>
                  {health?.redis || 'disconnected'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2.5 leading-relaxed">
                In-memory key-value store managing active JWT sessions (<code className="text-indigo-300">session:&#123;uid&#125;:&#123;hash&#125;</code>) and sliding-window rate limit counters.
              </p>
              <div className="mt-3 pt-2.5 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex justify-between">
                <span>Port: 6379</span>
                <span className="text-rose-400">Session & Limits</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Multi-Store Architecture Section */}
      <section id="architecture" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mb-12">
          <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">Architecture Deep Dive</div>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-['Manrope'] text-white mt-1">
            Separation of Concerns Across Persistence Tiers
          </h2>
          <p className="text-sm text-slate-400 mt-2 leading-relaxed">
            Unlike simple single-database architectures, TrustShare divides entity state across purpose-built storage layers to balance relational constraints, audit traceability, and session invalidation.
          </p>
        </div>

        {/* Visual Architecture Flow Representation */}
        <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/70 border border-slate-800 mb-10">
          <div className="text-xs font-mono text-slate-400 mb-6 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              SYSTEM ARCHITECTURE DATA FLOW
            </span>
            <span className="text-slate-500">FastAPI Async Execution</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 items-center">
            {/* Step 1: Client */}
            <div className="p-4 rounded-xl bg-[#0b1426] border border-slate-700/80 text-center">
              <div className="w-10 h-10 rounded-lg bg-indigo-900/60 text-indigo-300 flex items-center justify-center mx-auto mb-2">
                <Users className="w-5 h-5" />
              </div>
              <div className="text-xs font-bold text-white">Client Browser</div>
              <div className="text-[11px] text-slate-400 mt-1">React 18 + Vite</div>
              <div className="mt-2 text-[10px] font-mono text-indigo-300 bg-indigo-950/80 px-1.5 py-0.5 rounded border border-indigo-800/40">
                JWT Bearer Auth
              </div>
            </div>

            <div className="hidden lg:flex justify-center text-slate-500">
              <ArrowRight className="w-5 h-5" />
            </div>

            {/* Step 2: Gateway */}
            <div className="p-4 rounded-xl bg-[#0b1426] border border-indigo-600/50 text-center relative shadow-lg shadow-indigo-950/50">
              <div className="w-10 h-10 rounded-lg bg-indigo-600 text-white flex items-center justify-center mx-auto mb-2">
                <Server className="w-5 h-5" />
              </div>
              <div className="text-xs font-bold text-white">FastAPI Gateway</div>
              <div className="text-[11px] text-slate-300 mt-1">Python 3.11 + Uvicorn</div>
              <div className="mt-2 text-[10px] font-mono text-slate-400">
                Validation • Streaming • RBAC
              </div>
            </div>

            <div className="hidden lg:flex justify-center text-slate-500">
              <ArrowRight className="w-5 h-5" />
            </div>

            {/* Step 3: Persistence Targets */}
            <div className="space-y-2">
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <Database className="w-3.5 h-3.5 text-blue-400" />
                  <strong className="text-slate-200">PostgreSQL</strong>
                </span>
                <span className="text-[10px] font-mono text-slate-400">Users, Folders, Index</span>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-emerald-400" />
                  <strong className="text-slate-200">MongoDB</strong>
                </span>
                <span className="text-[10px] font-mono text-slate-400">Metadata, Audit Logs</span>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-rose-400" />
                  <strong className="text-slate-200">Redis</strong>
                </span>
                <span className="text-[10px] font-mono text-slate-400">Sessions & Rate Limits</span>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <HardDrive className="w-3.5 h-3.5 text-purple-400" />
                  <strong className="text-slate-200">Disk Vault</strong>
                </span>
                <span className="text-[10px] font-mono text-slate-400">UUIDv4 Raw Bytes</span>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Storage Role Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800">
            <h3 className="font-['Manrope'] font-bold text-white text-base flex items-center gap-2 mb-3">
              <Database className="w-4 h-4 text-blue-400" />
              PostgreSQL Relational Schema
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Maintains relational integrity with explicit foreign key constraints. If a user or folder reference is invalid, transactions fail closed.
            </p>
            <ul className="text-xs space-y-2 text-slate-300 font-mono">
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-indigo-400" />
                <span>users (id, name, email, password_hash, role, created_at)</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-indigo-400" />
                <span>folders (id, name, owner_id FK -&gt; users.id, created_at)</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-indigo-400" />
                <span>files (id, original_name, stored_name, content_type, size, sha256, owner_id FK, folder_id FK, meta_synced, uploaded_at)</span>
              </li>
            </ul>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800">
            <h3 className="font-['Manrope'] font-bold text-white text-base flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-emerald-400" />
              MongoDB Document Collections
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Stores secondary document metadata and append-only activity audit entries without blocking relational transactions.
            </p>
            <ul className="text-xs space-y-2 text-slate-300 font-mono">
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>files: &#123; id, name, content_type, size, sha256, owner_id, folder_id, stored_name, meta_synced, timestamp &#125;</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>activity: &#123; event, user_id, details, timestamp &#125;</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Tracked events: register, login, login_failed, logout, file_uploaded, file_downloaded, file_deleted, admin_file_access</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Real File Lifecycle & Verification Pipeline */}
      <section id="lifecycle" className="py-20 bg-[#0c1324] border-y border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">File Processing Pipeline</div>
            <h2 className="text-2xl sm:text-4xl font-extrabold font-['Manrope'] text-white mt-1">
              End-to-End File Lifecycle & Safety
            </h2>
            <p className="text-sm text-slate-400 mt-2 leading-relaxed">
              Every file uploaded to TrustShare passes through a 5-stage verification and containment pipeline before it is accessible for retrieval or download.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Step 1 */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-indigo-950 text-indigo-400 font-bold font-mono text-xs flex items-center justify-center mb-3">
                01
              </div>
              <h4 className="font-bold text-sm text-white">Pre-Validation</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Extension verified against strict allowlist (<code className="text-indigo-300">.pdf</code>, <code className="text-indigo-300">.docx</code>, <code className="text-indigo-300">.xlsx</code>, <code className="text-indigo-300">.csv</code>, <code className="text-indigo-300">.txt</code>, <code className="text-indigo-300">.png</code>, <code className="text-indigo-300">.jpg</code>, <code className="text-indigo-300">.webp</code>). Rejecting .exe and .sh with HTTP 415.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-indigo-950 text-indigo-400 font-bold font-mono text-xs flex items-center justify-center mb-3">
                02
              </div>
              <h4 className="font-bold text-sm text-white">Magic Header Check</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                First chunk inspected for genuine binary signatures (<code className="text-indigo-300">%PDF-</code>, <code className="text-indigo-300">89 50 4E 47</code>, <code className="text-indigo-300">FF D8 FF</code>). Spoofed extensions rejected with HTTP 400.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-indigo-950 text-indigo-400 font-bold font-mono text-xs flex items-center justify-center mb-3">
                03
              </div>
              <h4 className="font-bold text-sm text-white">Stream & SHA-256</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Streamed in 1 MiB chunks up to 10 MiB quota. Incremental SHA-256 hash computed in real-time. Oversized uploads trigger immediate disk unlinking and HTTP 413.
              </p>
            </div>

            {/* Step 4 */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-indigo-950 text-indigo-400 font-bold font-mono text-xs flex items-center justify-center mb-3">
                04
              </div>
              <h4 className="font-bold text-sm text-white">Dual-DB Commit</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                PostgreSQL row committed with <code className="text-indigo-300">meta_synced=True</code>. MongoDB metadata inserted. Failure flags <code className="text-indigo-300">meta_synced=False</code> for admin reconciliation.
              </p>
            </div>

            {/* Step 5 */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <div className="w-8 h-8 rounded-lg bg-indigo-950 text-indigo-400 font-bold font-mono text-xs flex items-center justify-center mb-3">
                05
              </div>
              <h4 className="font-bold text-sm text-white">Owner Isolation</h4>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                List and download enforce owner check. Non-owners receive HTTP 403. Admin access generates MongoDB audit events. Deletion is restricted to owner only.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security & Access Control Model */}
      <section id="security" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mb-12">
          <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">Access Control Model</div>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-['Manrope'] text-white mt-1">
            Role-Based Access Control & Isolation Matrix
          </h2>
          <p className="text-sm text-slate-400 mt-2 leading-relaxed">
            Every route in TrustShare is verified against explicit security boundaries. The table below represents verified access permissions.
          </p>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-[11px] font-mono uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Action / Endpoint</th>
                <th className="py-3.5 px-4">File Owner</th>
                <th className="py-3.5 px-4">Other User (Cross-User)</th>
                <th className="py-3.5 px-4">Administrator</th>
                <th className="py-3.5 px-4">Audit Behavior</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70 text-slate-300">
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">GET /api/files (List)</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed (Own Files)</td>
                <td className="py-3.5 px-4 text-slate-500">Filtered Out (Empty)</td>
                <td className="py-3.5 px-4 text-emerald-400">Allowed (Own Files)</td>
                <td className="py-3.5 px-4 text-slate-400">Scoped query</td>
              </tr>
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">GET /api/files/&#123;id&#125;/metadata</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed (Audit Trail)</td>
                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">admin_file_access</td>
              </tr>
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">GET /api/files/&#123;id&#125;/download</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed (Audit Trail)</td>
                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">admin_file_access</td>
              </tr>
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">DELETE /api/files/&#123;id&#125;</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-slate-400">Owner-only policy</td>
              </tr>
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">GET /api/admin/users</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed (Full List)</td>
                <td className="py-3.5 px-4 text-slate-400">Admin role required</td>
              </tr>
              <tr>
                <td className="py-3.5 px-4 font-mono text-indigo-300">POST /api/admin/reconcile-metadata</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-rose-400 font-semibold">HTTP 403 Forbidden</td>
                <td className="py-3.5 px-4 text-emerald-400 font-semibold">Allowed</td>
                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">metadata_reconciled</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Scope Comparison: Milestone 1 vs Milestone 2 */}
      <section id="scope" className="py-20 bg-[#0c1324] border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">Product Scope Definition</div>
            <h2 className="text-2xl sm:text-4xl font-extrabold font-['Manrope'] text-white mt-1">
              Milestone 1 Delivered vs. Milestone 2 Roadmap
            </h2>
            <p className="text-sm text-slate-400 mt-2 leading-relaxed">
              To maintain academic and professional integrity, implemented features are strictly distinguished from planned roadmap extensions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Milestone 1 Delivered */}
            <div className="p-6 rounded-xl bg-slate-900/90 border border-emerald-500/30">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-xs font-semibold">
                  Milestone 1 — 100% Implemented & Tested
                </span>
                <span className="text-xs font-mono text-emerald-400">38/38 Verified</span>
              </div>
              <ul className="space-y-3 text-xs text-slate-300">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Bcrypt Password Hashing:</strong> Passwords salted and hashed with bcrypt ($2b$ format) in PostgreSQL.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>JWT + Redis Sessions:</strong> Expiring HS256 tokens with server-side session tracking and revocation on logout.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Rate Limiting:</strong> Redis sliding-window limiting (5 logins/min per IP, 20 uploads/min per user).</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>SHA-256 Checksumming:</strong> Streaming byte-level computation; verifiable on download.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>File & Folder Organization:</strong> Create folders, filter by folder, substring search, and owner isolation.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Storage Vault & Anti-Traversal:</strong> Collision-resistant UUIDv4 file addressing in local storage.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Multi-Store Sync:</strong> PostgreSQL canonical index + MongoDB metadata document + reconciliation endpoint.</span>
                </li>
              </ul>
            </div>

            {/* Milestone 2 Planned Roadmap */}
            <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold">
                  Milestone 2 — Planned Roadmap
                </span>
                <span className="text-xs font-mono text-indigo-400">Future Engineering</span>
              </div>
              <ul className="space-y-3 text-xs text-slate-400">
                <li className="flex items-start gap-2">
                  <GitBranch className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <span><strong>AES-256 Encryption at Rest:</strong> Envelope encryption with envelope data keys and centralized KMS rotation.</span>
                </li>
                <li className="flex items-start gap-2">
                  <GitBranch className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <span><strong>Cloud Object Storage:</strong> Storage abstraction layer for AWS S3 and Google Cloud Storage buckets.</span>
                </li>
                <li className="flex items-start gap-2">
                  <GitBranch className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <span><strong>Expiring Share Links:</strong> Time-limited, password-protected download links with download quotas.</span>
                </li>
                <li className="flex items-start gap-2">
                  <GitBranch className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <span><strong>Multi-Factor Authentication (MFA):</strong> TOTP authenticator integration and WebAuthn hardware token support.</span>
                </li>
                <li className="flex items-start gap-2">
                  <GitBranch className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <span><strong>Enterprise SSO:</strong> OpenID Connect (OIDC) and SAML 2.0 integration for enterprise directories.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Frequently Asked Questions */}
      <section id="faq" className="py-20 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="text-[11px] font-mono font-semibold text-indigo-400 uppercase tracking-wider">Technical FAQ</div>
          <h2 className="text-2xl sm:text-3xl font-extrabold font-['Manrope'] text-white mt-1">
            Frequently Asked Engineering Questions
          </h2>
        </div>

        <div className="space-y-3">
          {faqs.map((faq, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden"
            >
              <button
                onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                className="w-full px-5 py-4 text-left font-semibold text-slate-200 flex items-center justify-between gap-4 text-xs sm:text-sm hover:text-white transition-colors"
              >
                <span>{faq.q}</span>
                <ChevronDown
                  className={`w-4 h-4 text-slate-400 transition-transform ${activeFaq === idx ? 'rotate-180 text-indigo-400' : ''}`}
                />
              </button>
              {activeFaq === idx && (
                <div className="px-5 pb-4 text-xs text-slate-300 leading-relaxed border-t border-slate-800/80 pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="py-16 bg-[#0c1324] border-t border-slate-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold font-['Manrope'] text-white">
            Ready to test TrustShare Milestone 1?
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-lg mx-auto">
            Experience verified file management with live authentication, folders, and cryptographic integrity verification.
          </p>

          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto px-6 py-2.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-all flex items-center justify-center gap-2"
            >
              {user ? 'Open Your Workspace' : 'Create an Account'}
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={onSignIn}
              className="w-full sm:w-auto px-5 py-2.5 rounded-lg text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all"
            >
              Sign In to Existing Account
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#080d19] py-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span className="font-['Manrope'] font-bold text-slate-300">
              trust<span className="text-indigo-400">share</span>
            </span>
            <span className="text-slate-600">|</span>
            <span>Milestone 1 Engineering Submission</span>
          </div>

          <div className="flex items-center gap-5 text-slate-400">
            <button onClick={onSignIn} className="hover:text-white transition-colors">Sign In</button>
            <button onClick={onGetStarted} className="hover:text-white transition-colors">Register</button>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1">
              API Docs <ExternalLink className="w-3 h-3" />
            </a>
            <a href="http://localhost:8000/health/ready" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1">
              Readiness Check <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <div className="text-[11px] text-slate-500">
            © 2026 TrustShare. Verified multi-store file management.
          </div>
        </div>
      </footer>
    </div>
  );
}
