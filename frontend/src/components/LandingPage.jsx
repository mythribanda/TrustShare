import React, { useState } from 'react';
import {
  ShieldCheck,
  Folder,
  Files,
  Search,
  Upload,
  Plus,
  LockKeyhole,
  FileText,
  FileSpreadsheet,
  Image as ImageIcon,
  HardDrive,
  Users,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Database,
  Activity,
  Layers,
  Key,
  Shield,
  Server,
  Download,
  ChevronDown,
  Sparkles,
  ExternalLink,
  Cpu
} from 'lucide-react';

export default function LandingPage({ onGetStarted, onSignIn, health }) {
  const [activeFaq, setActiveFaq] = useState(null);
  const [demoTab, setDemoTab] = useState('files');
  const [demoQuery, setDemoQuery] = useState('');

  const sampleFiles = [
    { id: 1, name: 'TrustShare_Architecture_Doc.pdf', type: 'PDF', size: '2.4 MB', hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', folder: 'Architecture', date: '2026-10-14' },
    { id: 2, name: 'Security_Audit_Report_Q3.docx', type: 'DOCX', size: '1.1 MB', hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4', folder: 'Compliance', date: '2026-10-13' },
    { id: 3, name: 'User_Role_Matrix_2026.xlsx', type: 'XLSX', size: '640 KB', hash: 'd57a68d169ccee7e7175f97fbecd86ff215057a594514f0003d1c159a0491a47', folder: 'Compliance', date: '2026-10-12' },
    { id: 4, name: 'Cryptographic_Keys_Overview.png', type: 'PNG', size: '3.8 MB', hash: '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae', folder: 'Media', date: '2026-10-10' },
  ];

  const filteredDemoFiles = sampleFiles.filter(f =>
    f.name.toLowerCase().includes(demoQuery.toLowerCase()) ||
    f.folder.toLowerCase().includes(demoQuery.toLowerCase())
  );

  const faqs = [
    {
      q: 'What is TrustShare Milestone 1?',
      a: 'Milestone 1 is a production-ready architectural foundation for secure enterprise file management. It integrates React + Tailwind, a high-performance FastAPI service, PostgreSQL for relational entities, MongoDB for activity logs, Redis for caching, JWT bearer auth with bcrypt hashing, and strict file validation.'
    },
    {
      q: 'How does TrustShare verify file integrity?',
      a: 'Every file uploaded to TrustShare is streamed through a SHA-256 cryptographic hashing pipeline. The resulting 64-character hash is recorded in both PostgreSQL and MongoDB metadata collections, enabling bit-for-bit file verification.'
    },
    {
      q: 'Can TrustShare run standalone without Docker?',
      a: 'Yes! While Docker Compose provides a one-command multi-service stack (Postgres + Mongo + Redis + FastAPI + Vite), TrustShare includes an intelligent fallback mechanism that runs smoothly with local Python and SQLite when external databases are not running.'
    },
    {
      q: 'What are the supported file types and size limits?',
      a: 'By default, Milestone 1 allows documents (.pdf, .docx, .xlsx, .csv, .txt) and images (.png, .jpg, .jpeg, .webp) up to 10 MiB per file. All files are assigned collision-resistant UUIDs on disk to prevent path traversal and naming collisions.'
    },
    {
      q: 'What is planned for Milestone 2?',
      a: 'Milestone 2 expands on this foundation by adding AES-256 encryption at rest with enterprise key management (KMS), S3/Cloud object storage integrations, time-limited secure share links, multi-factor authentication (MFA/TOTP), and OAuth single sign-on.'
    }
  ];

  return (
    <div className="landing-container bg-[#0b1325] text-slate-100 min-h-screen selection:bg-indigo-500 selection:text-white">
      {/* Top Notification Bar */}
      <div className="bg-gradient-to-r from-indigo-900/60 via-indigo-700/40 to-indigo-900/60 border-b border-indigo-500/20 px-4 py-2.5 text-center text-xs text-indigo-200 flex items-center justify-center gap-2">
        <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-semibold text-white">TrustShare Milestone 1</span> — High-Assurance File Management System
        <span className="hidden sm:inline text-indigo-300">• Multi-DB Architecture Active</span>
      </div>

      {/* Navigation */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0b1325]/85 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div className="font-['Manrope'] text-2xl font-extrabold tracking-tight text-white">
              trust<span className="text-indigo-400 font-medium">share</span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-indigo-400 transition-colors">Features</a>
            <a href="#demo" className="hover:text-indigo-400 transition-colors">Interactive Demo</a>
            <a href="#architecture" className="hover:text-indigo-400 transition-colors">Architecture</a>
            <a href="#security" className="hover:text-indigo-400 transition-colors">Security & RBAC</a>
            <a href="#faq" className="hover:text-indigo-400 transition-colors">FAQ</a>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={onSignIn}
              className="px-4 py-2 text-sm font-medium text-slate-200 hover:text-white transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={onGetStarted}
              className="px-5 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-md shadow-indigo-600/30 hover:shadow-indigo-500/40 transition-all flex items-center gap-2"
            >
              Launch Workspace
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-28 md:pt-28 md:pb-36">
        {/* Ambient Gradient Glows */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-indigo-600/15 blur-[140px] pointer-events-none rounded-full" />
        <div className="absolute top-1/3 right-10 w-[350px] h-[350px] bg-cyan-600/10 blur-[120px] pointer-events-none rounded-full" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-950/60 text-xs font-semibold text-indigo-300 mb-8 backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Zero-Trust Architecture • Role-Based Governance</span>
          </div>

          <h1 className="font-['Manrope'] text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.12]">
            Secure File Management Built on{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-indigo-300 to-sky-400">
              Cryptographic Integrity
            </span>
          </h1>

          <p className="mt-7 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Protect, organize, and inspect your business-critical documents with SHA-256 checksums,
            strict role-based access control, and complete audit event tracking across PostgreSQL, MongoDB, and Redis.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-xl shadow-indigo-600/35 hover:scale-[1.02] active:scale-[0.99] transition-all flex items-center justify-center gap-3"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </button>
            <a
              href="#demo"
              className="w-full sm:w-auto px-7 py-4 rounded-xl text-base font-semibold text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-slate-600 transition-all flex items-center justify-center gap-2"
            >
              View Live Demo
            </a>
          </div>

          {/* Quick Metrics Bar */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-8 border-t border-slate-800/80">
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60">
              <div className="font-['Manrope'] text-2xl font-bold text-indigo-400">SHA-256</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">Cryptographic Digests</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60">
              <div className="font-['Manrope'] text-2xl font-bold text-sky-400">RBAC</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">Admin & User Roles</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60">
              <div className="font-['Manrope'] text-2xl font-bold text-emerald-400">10 MiB</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">Quota & Type Validation</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60">
              <div className="font-['Manrope'] text-2xl font-bold text-purple-400">Multi-DB</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">Postgres • Mongo • Redis</div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Showcase / Demo Sandbox */}
      <section id="demo" className="py-20 bg-slate-900/50 border-y border-slate-800/80 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <div className="text-xs font-bold tracking-widest text-indigo-400 uppercase">Live Workspace Experience</div>
            <h2 className="font-['Manrope'] text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Clean. Fast. Completely in your control.
            </h2>
            <p className="text-slate-400 mt-3 text-sm sm:text-base">
              Test how files are indexed, categorized into folders, and assigned verified SHA-256 cryptographic digests in real time.
            </p>
          </div>

          {/* Interactive Window Preview */}
          <div className="rounded-2xl border border-slate-700/80 bg-[#101a30] shadow-2xl overflow-hidden max-w-5xl mx-auto">
            {/* Window Title Bar */}
            <div className="bg-[#0b1324] px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-xs font-mono text-slate-400">trustshare.local/workspace/all-files</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-500/30 text-[11px] text-emerald-300 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  API {health?.database ? `Online (${health.database})` : 'Online'}
                </span>
                <button
                  onClick={onSignIn}
                  className="text-xs text-indigo-300 hover:text-white flex items-center gap-1"
                >
                  Enter Full App <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Mock Workspace Content */}
            <div className="p-6">
              {/* Toolbar */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search by file name or folder..."
                    value={demoQuery}
                    onChange={(e) => setDemoQuery(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  {demoQuery && (
                    <button
                      onClick={() => setDemoQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white text-xs"
                    >
                      ×
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center rounded-lg bg-slate-900 border border-slate-700 p-1 text-xs font-medium">
                    <button
                      onClick={() => setDemoTab('files')}
                      className={`px-3 py-1 rounded-md transition-colors ${demoTab === 'files' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                      File Inventory ({filteredDemoFiles.length})
                    </button>
                    <button
                      onClick={() => setDemoTab('integrity')}
                      className={`px-3 py-1 rounded-md transition-colors ${demoTab === 'integrity' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                      SHA-256 Hashes
                    </button>
                  </div>
                  <button
                    onClick={onGetStarted}
                    className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload File
                  </button>
                </div>
              </div>

              {/* Table Preview */}
              <div className="overflow-x-auto mt-4">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Document Name</th>
                      <th className="py-3 px-4 font-semibold">Folder</th>
                      <th className="py-3 px-4 font-semibold">Size</th>
                      {demoTab === 'integrity' ? (
                        <th className="py-3 px-4 font-semibold">SHA-256 Digest</th>
                      ) : (
                        <th className="py-3 px-4 font-semibold">Validation</th>
                      )}
                      <th className="py-3 px-4 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredDemoFiles.map((f) => (
                      <tr key={f.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-700/40 text-indigo-400 flex items-center justify-center flex-shrink-0">
                              {f.type === 'PDF' && <FileText className="w-4 h-4" />}
                              {f.type === 'DOCX' && <FileText className="w-4 h-4 text-sky-400" />}
                              {f.type === 'XLSX' && <FileSpreadsheet className="w-4 h-4 text-emerald-400" />}
                              {f.type === 'PNG' && <ImageIcon className="w-4 h-4 text-purple-400" />}
                            </div>
                            <div>
                              <div className="font-semibold text-slate-100">{f.name}</div>
                              <div className="text-[10px] text-slate-400">Added {f.date}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-[11px] text-slate-300">
                            <Folder className="w-3 h-3 text-slate-400" />
                            {f.folder}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">{f.size}</td>
                        {demoTab === 'integrity' ? (
                          <td className="py-3 px-4 font-mono text-[11px] text-indigo-300 max-w-[240px] truncate" title={f.hash}>
                            {f.hash.slice(0, 20)}...{f.hash.slice(-8)}
                          </td>
                        ) : (
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Checksum Verified
                            </span>
                          </td>
                        )}
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={onGetStarted}
                            className="p-1.5 rounded-md hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                            title="Sign in to download"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Sandbox Footer Banner */}
              <div className="mt-6 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/20 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 text-indigo-200">
                  <ShieldCheck className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                  <span>Ready to manage your own documents? Launch a personal workspace in under 30 seconds.</span>
                </div>
                <button
                  onClick={onGetStarted}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg whitespace-nowrap shadow-sm"
                >
                  Create Your Account
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Capabilities / Features */}
      <section id="features" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="text-xs font-bold tracking-widest text-indigo-400 uppercase">Engineered for Trust</div>
          <h2 className="font-['Manrope'] text-3xl sm:text-5xl font-extrabold text-white mt-3">
            Enterprise Security Without the Complexity
          </h2>
          <p className="text-slate-400 mt-4 text-base sm:text-lg">
            Every feature in TrustShare is designed with defensive security, data privacy, and deterministic reliability at its core.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <LockKeyhole className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Bcrypt & JWT Auth</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Passwords are salted and hashed using adaptive bcrypt cost factors. Authenticated sessions issue signed HS256 JWT bearer tokens with configurable expiration windows.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-sky-950/80 border border-sky-500/30 text-sky-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Cryptographic SHA-256</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Files are streamed chunk-by-chunk through a SHA-256 hasher during upload. The immutable digest provides zero-knowledge verification against data tampering or corruption.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-emerald-950/80 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Role-Based Access (RBAC)</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Strict access levels (<code className="text-indigo-300">admin</code>, <code className="text-indigo-300">user</code>, <code className="text-indigo-300">guest</code>). Admin routes for system oversight are secured behind dependency-injected privilege checks.
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-amber-950/80 border border-amber-500/30 text-amber-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Folder className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Folder Taxonomy & Search</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Organize projects into custom folders, filter files instantly, and perform case-insensitive substring searches across your entire workspace index.
            </p>
          </div>

          {/* Card 5 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-purple-950/80 border border-purple-500/30 text-purple-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <HardDrive className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Anti-Traversal Storage</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Stored files are uncoupled from user filenames on disk, assigned UUID-based identifiers, and constrained to an explicit directory vault preventing directory traversal attacks.
            </p>
          </div>

          {/* Card 6 */}
          <div className="p-8 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-indigo-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-rose-950/80 border border-rose-500/30 text-rose-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
            <h3 className="font-['Manrope'] text-xl font-bold text-white mb-2">Audit Logging Pipeline</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Every sensitive action—registration, login, upload, folder creation, file download, and deletion—is logged with timestamps and actor identities into MongoDB.
            </p>
          </div>
        </div>
      </section>

      {/* Architecture Deep Dive */}
      <section id="architecture" className="py-24 bg-slate-900/40 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="text-xs font-bold tracking-widest text-indigo-400 uppercase">Under The Hood</div>
            <h2 className="font-['Manrope'] text-3xl sm:text-5xl font-extrabold text-white mt-3">
              Modern Multi-Store Architecture
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Combining the structural integrity of relational databases with the flexibility of document stores and in-memory caches.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Relational Layer */}
            <div className="p-6 rounded-2xl bg-[#0e172a] border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-blue-950/80 text-blue-400 flex items-center justify-center mb-4">
                  <Database className="w-5 h-5" />
                </div>
                <h4 className="font-['Manrope'] text-lg font-bold text-white">Relational Layer</h4>
                <div className="text-xs text-blue-400 font-mono mt-1">PostgreSQL / SQLite</div>
                <p className="text-slate-400 text-xs mt-3 leading-relaxed">
                  Stores canonical user accounts, role mappings, folder trees, and authoritative file index metadata with foreign key constraints.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
                ACID Transactions • Relational
              </div>
            </div>

            {/* Document Store */}
            <div className="p-6 rounded-2xl bg-[#0e172a] border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-emerald-950/80 text-emerald-400 flex items-center justify-center mb-4">
                  <Layers className="w-5 h-5" />
                </div>
                <h4 className="font-['Manrope'] text-lg font-bold text-white">Document Store</h4>
                <div className="text-xs text-emerald-400 font-mono mt-1">MongoDB 7.0</div>
                <p className="text-slate-400 text-xs mt-3 leading-relaxed">
                  Holds flexible file metadata documents and chronological audit event streams tracking user access and file lifecycle actions.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
                Audit Trail • Event Streaming
              </div>
            </div>

            {/* Cache & Session */}
            <div className="p-6 rounded-2xl bg-[#0e172a] border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-rose-950/80 text-rose-400 flex items-center justify-center mb-4">
                  <Cpu className="w-5 h-5" />
                </div>
                <h4 className="font-['Manrope'] text-lg font-bold text-white">Cache Layer</h4>
                <div className="text-xs text-rose-400 font-mono mt-1">Redis 7.0</div>
                <p className="text-slate-400 text-xs mt-3 leading-relaxed">
                  Accelerates session validations, active token tracking, and provides sub-millisecond lookup latency for rapid authorization.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
                In-Memory • Low Latency
              </div>
            </div>

            {/* API Engine */}
            <div className="p-6 rounded-2xl bg-[#0e172a] border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-indigo-950/80 text-indigo-400 flex items-center justify-center mb-4">
                  <Server className="w-5 h-5" />
                </div>
                <h4 className="font-['Manrope'] text-lg font-bold text-white">API Engine</h4>
                <div className="text-xs text-indigo-400 font-mono mt-1">FastAPI + Uvicorn</div>
                <p className="text-slate-400 text-xs mt-3 leading-relaxed">
                  High-throughput asynchronous Python gateway with automatic OpenAPI documentation, strict Pydantic schemas, and CORS governance.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
                OpenAPI Docs • Asynchronous
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Milestone Roadmap Comparison */}
      <section id="security" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="text-xs font-bold tracking-widest text-indigo-400 uppercase">Product Roadmap</div>
          <h2 className="font-['Manrope'] text-3xl sm:text-5xl font-extrabold text-white mt-3">
            Milestone 1 Scope & Future Evolution
          </h2>
          <p className="text-slate-400 mt-4 text-base sm:text-lg">
            A clear view of currently delivered foundation capabilities versus planned Milestone 2 security features.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Milestone 1 (Current) */}
          <div className="p-8 rounded-2xl bg-indigo-950/30 border-2 border-indigo-500/40 relative">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/30 text-xs font-semibold text-emerald-400 mb-4">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Milestone 1 — Live & Fully Operational
            </div>
            <h3 className="font-['Manrope'] text-2xl font-bold text-white mb-4">Foundation Security</h3>
            <ul className="space-y-3.5 text-sm text-slate-300">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Bcrypt password hashing & HS256 JWT bearer authentication</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>SHA-256 cryptographic file checksumming during upload</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Strict extension whitelist & 10 MiB quota enforcement</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Role-Based Access Control (Admin, User, Guest) & protected routes</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Multi-tier database persistence (PostgreSQL + MongoDB + Redis)</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Full folder hierarchy, instant search, and local file storage</span>
              </li>
            </ul>
          </div>

          {/* Milestone 2 (Roadmap) */}
          <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-950/80 border border-purple-500/30 text-xs font-semibold text-purple-300 mb-4">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              Milestone 2 — In Engineering
            </div>
            <h3 className="font-['Manrope'] text-2xl font-bold text-white mb-4">Advanced Enterprise Layer</h3>
            <ul className="space-y-3.5 text-sm text-slate-400">
              <li className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 text-slate-500">2</div>
                <span>Envelope AES-256-GCM encryption at rest with KMS key rotation</span>
              </li>
              <li className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 text-slate-500">2</div>
                <span>AWS S3 / Google Cloud Storage multi-cloud object backend</span>
              </li>
              <li className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 text-slate-500">2</div>
                <span>Time-expiring secure share links with password and download limits</span>
              </li>
              <li className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 text-slate-500">2</div>
                <span>Hardware token & TOTP Multi-Factor Authentication (MFA)</span>
              </li>
              <li className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 text-slate-500">2</div>
                <span>OAuth 2.0 / SAML Single Sign-On (Google, Microsoft, Okta)</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-24 bg-slate-900/40 border-t border-slate-800/80">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="text-xs font-bold tracking-widest text-indigo-400 uppercase">Answers & Information</div>
            <h2 className="font-['Manrope'] text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden transition-colors"
              >
                <button
                  onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                  className="w-full px-6 py-4 text-left font-semibold text-slate-100 flex items-center justify-between gap-4 text-sm sm:text-base hover:text-indigo-300 transition-colors"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform ${activeFaq === idx ? 'rotate-180 text-indigo-400' : ''}`}
                  />
                </button>
                {activeFaq === idx && (
                  <div className="px-6 pb-5 text-sm text-slate-300 leading-relaxed border-t border-slate-800/60 pt-3">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 relative overflow-hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <div className="p-10 sm:p-14 rounded-3xl bg-gradient-to-b from-indigo-900/60 via-indigo-950/40 to-[#0b1325] border border-indigo-500/30 shadow-2xl relative">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white flex items-center justify-center mx-auto mb-6 shadow-xl shadow-indigo-500/40">
              <ShieldCheck className="w-9 h-9" />
            </div>

            <h2 className="font-['Manrope'] text-3xl sm:text-4xl font-extrabold text-white">
              Ready to take control of your workspace?
            </h2>
            <p className="mt-4 text-slate-300 max-w-xl mx-auto text-sm sm:text-base">
              Set up your account in seconds and experience secure, organized document management built on verified integrity.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={onGetStarted}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/40 transition-all flex items-center justify-center gap-2"
              >
                Create Free Account
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={onSignIn}
                className="w-full sm:w-auto px-6 py-3.5 rounded-xl text-sm font-semibold text-slate-300 hover:text-white bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 transition-all"
              >
                Sign In to Existing Workspace
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-[#080d1a] py-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span className="font-['Manrope'] font-bold text-slate-300 text-sm">
              trust<span className="text-indigo-400">share</span>
            </span>
            <span className="text-slate-600">|</span>
            <span>Milestone 1 Local Foundation</span>
          </div>

          <div className="flex items-center gap-6 text-slate-400">
            <button onClick={onSignIn} className="hover:text-white transition-colors">Sign In</button>
            <button onClick={onGetStarted} className="hover:text-white transition-colors">Register</button>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              API Docs (Swagger)
            </a>
          </div>

          <div>
            © 2026 TrustShare. Built for secure, auditable file collaboration.
          </div>
        </div>
      </footer>
    </div>
  );
}
