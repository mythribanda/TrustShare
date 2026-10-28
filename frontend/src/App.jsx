import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  ShieldCheck,
  Folder,
  Files,
  Search,
  Upload,
  Plus,
  LogOut,
  LockKeyhole,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  Download,
  Trash2,
  HardDrive,
  Users,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  Info,
  X,
  UploadCloud,
  FileCode,
  Check
} from 'lucide-react';
import LandingPage from './components/LandingPage';
import SecurityCenter from './components/SecurityCenter';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API });

const ALLOWED_EXTS = ['.pdf', '.docx', '.xlsx', '.pptx', '.csv', '.txt', '.png', '.jpg', '.jpeg', '.webp'];
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MiB

function sizeText(n) {
  if (n === undefined || n === null) return '0 B';
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1048576).toFixed(1) + ' MB';
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('trustshare_token') || '');
  const [user, setUser] = useState(null);
  const [view, setView] = useState('landing'); // 'landing' | 'auth' | 'dashboard'
  const [mode, setMode] = useState('login'); // 'login' | 'register' | 'reset'
  const [form, setForm] = useState({ name: '', email: '', password: '', otp: '' });
  const [files, setFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);
  const [showSecurityCenter, setShowSecurityCenter] = useState(false);
  const [query, setQuery] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState({});

  // Modals state
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [folderNameInput, setFolderNameInput] = useState('');
  const [folderModalError, setFolderModalError] = useState('');

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFileObj, setUploadFileObj] = useState(null);
  const [uploadFolderId, setUploadFolderId] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadModalError, setUploadModalError] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const [detailsFile, setDetailsFile] = useState(null);
  const [fileMetadata, setFileMetadata] = useState(null);
  const [loadingMetadata, setLoadingMetadata] = useState(false);

  useEffect(() => {
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
      loadMe();
    }
  }, [token]);

  useEffect(() => {
    api
      .get('/health')
      .then((r) => setHealth(r.data))
      .catch(() => {});
  }, []);

  async function loadMe() {
    try {
      const r = await api.get('/api/auth/me');
      setUser(r.data.user);
      setView('dashboard');
      await Promise.all([loadFiles(), loadFolders()]);
    } catch {
      logout();
    }
  }

  async function loadFiles() {
    try {
      const r = await api.get('/api/files', {
        params: { q: query || undefined, folder_id: activeFolder || undefined }
      });
      setFiles(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load files');
    }
  }

  async function loadFolders() {
    try {
      const r = await api.get('/api/folders');
      setFolders(r.data);
    } catch {}
  }

  useEffect(() => {
    if (user && view === 'dashboard') {
      loadFiles();
    }
  }, [query, activeFolder]);

  // ITEM 1 & 2: Logout with backend notification and state clearing
  async function logout() {
    try {
      if (token) {
        await api.post('/api/auth/logout');
      }
    } catch (err) {
      console.warn('Backend logout notification error:', err);
    } finally {
      localStorage.removeItem('trustshare_token');
      delete api.defaults.headers.common.Authorization;
      setToken('');
      setUser(null);
      setFiles([]);
      setFolders([]);
      setNotice('');
      setView('landing');
    }
  }

  // ITEM 3: Auth submission with rate limiting handling
  async function submitAuth(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const path = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const payload = mode === 'register'
        ? { name: form.name.trim(), email: form.email.trim(), password: form.password }
        : { email: form.email.trim(), password: form.password, ...(form.otp.trim() ? { otp: form.otp.trim() } : {}) };
      const r = await api.post(path, payload);
      localStorage.setItem('trustshare_token', r.data.access_token);
      api.defaults.headers.common.Authorization = `Bearer ${r.data.access_token}`;
      setToken(r.data.access_token);
      setUser(r.data.user);
      setView('dashboard');
      setNotice(mode === 'register' ? 'Account created successfully' : 'Welcome back');
    } catch (e) {
      if (e.response?.status === 429) {
        setError(e.response.data?.detail || 'Rate limit exceeded: Too many login attempts. Please wait a minute and try again.');
      } else {
        setError(e.response?.data?.detail || 'Request failed');
      }
    } finally {
      setBusy(false);
    }
  }

  // ITEM 5: Upload validation and submission
  function validateAndSetUploadFile(f) {
    setUploadModalError('');
    if (!f) return;
    const name = f.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTS.some((ext) => name.endsWith(ext));
    if (!hasValidExt) {
      setUploadModalError(`File type not allowed. Supported types: PDF, DOCX, XLSX, CSV, TXT, PNG, JPG, WEBP.`);
      setUploadFileObj(null);
      return;
    }
    if (f.size > MAX_UPLOAD_BYTES) {
      setUploadModalError(`File size (${sizeText(f.size)}) exceeds the strict 10 MiB limit.`);
      setUploadFileObj(null);
      return;
    }
    if (f.size === 0) {
      setUploadModalError('Empty files are not allowed.');
      setUploadFileObj(null);
      return;
    }
    setUploadFileObj(f);
  }

  function openUploadModal() {
    setUploadFileObj(null);
    setUploadFolderId(activeFolder !== null ? String(activeFolder) : '');
    setUploadProgress(0);
    setUploading(false);
    setUploadModalError('');
    setIsDragging(false);
    setIsUploadModalOpen(true);
  }

  async function handleUploadSubmit(e) {
    e.preventDefault();
    if (!uploadFileObj) {
      setUploadModalError('Please select a file to upload.');
      return;
    }
    const data = new FormData();
    data.append('file', uploadFileObj);
    if (uploadFolderId) {
      data.append('folder_id', uploadFolderId);
    }

    setUploading(true);
    setUploadModalError('');
    setUploadProgress(0);

    try {
      await api.post('/api/files/upload', data, {
        onUploadProgress: (p) => {
          const percent = Math.round((p.loaded / (p.total || p.loaded)) * 100);
          setUploadProgress(percent);
        }
      });
      setNotice(`File "${uploadFileObj.name}" uploaded successfully.`);
      setIsUploadModalOpen(false);
      await loadFiles();
    } catch (e) {
      if (e.response?.status === 429) {
        setUploadModalError(e.response.data?.detail || 'Rate limit exceeded: You have reached the maximum of 20 uploads per minute.');
      } else {
        setUploadModalError(e.response?.data?.detail || 'Upload failed. Please check file and server status.');
      }
    } finally {
      setUploading(false);
    }
  }

  // ITEM 6: Folder Modal
  function openFolderModal() {
    setFolderNameInput('');
    setFolderModalError('');
    setIsFolderModalOpen(true);
  }

  async function handleFolderSubmit(e) {
    e.preventDefault();
    const name = folderNameInput.trim();
    if (!name) {
      setFolderModalError('Folder name is required.');
      return;
    }
    try {
      await api.post('/api/folders', { name });
      setNotice(`Folder "${name}" created.`);
      setIsFolderModalOpen(false);
      await loadFolders();
    } catch (e) {
      setFolderModalError(e.response?.data?.detail || 'Could not create folder.');
    }
  }

  // ITEM 4: MongoDB Metadata Modal
  async function openFileDetails(f) {
    setDetailsFile(f);
    setFileMetadata(null);
    setLoadingMetadata(true);
    try {
      const r = await api.get(`/api/files/${f.id}/metadata`);
      setFileMetadata(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not fetch file metadata');
      setDetailsFile(null);
    } finally {
      setLoadingMetadata(false);
    }
  }

  async function deleteFile(f) {
    if (!confirm(`Delete ${f.name}?`)) return;
    try {
      await api.delete(`/api/files/${f.id}`);
      setNotice('File deleted');
      loadFiles();
    } catch (e) {
      setError(e.response?.data?.detail || 'Delete failed');
    }
  }

  async function downloadFile(f) {
    try {
      const r = await api.get(`/api/files/${f.id}/download`, { responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = f.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || 'Download failed');
    }
  }

  const total = useMemo(() => files.reduce((s, f) => s + f.size, 0), [files]);

  // VIEW 1: LANDING PAGE
  if (view === 'landing') {
    return (
      <LandingPage
        health={health}
        onGetStarted={() => {
          if (user) {
            setView('dashboard');
          } else {
            setMode('register');
            setView('auth');
            setError('');
          }
        }}
        onSignIn={() => {
          if (user) {
            setView('dashboard');
          } else {
            setMode('login');
            setView('auth');
            setError('');
          }
        }}
      />
    );
  }

  // VIEW 2: AUTHENTICATION
  if (view === 'auth' || !user) {
    return (
      <div className="auth-shell">
        <div className="auth-art">
          <div className="brand cursor-pointer" onClick={() => setView('landing')}>
            <span className="brand-icon">
              <ShieldCheck />
            </span>
            <span>
              trust<span className="brand-light">share</span>
            </span>
          </div>
          <div className="art-copy">
            <div className="eyebrow">
              <span className="dot" /> YOUR FILES. YOUR CONTROL.
            </div>
            <h1>
              Everything important,
              <br />
              <em>in one secure place.</em>
            </h1>
            <p>A calm, organized workspace for the documents that move your work forward.</p>
            <div className="security-points">
              <span>
                <LockKeyhole size={16} /> Private workspace
              </span>
              <span>
                <CheckCircle2 size={16} /> Access controlled
              </span>
            </div>
          </div>
          <div className="art-footer">
            BUILT FOR THE WAY YOU WORK <span>© 2026 TrustShare</span>
          </div>
        </div>

        <div className="auth-main">
          <div className="auth-card">
            <button
              type="button"
              className="back-link"
              onClick={() => {
                setView('landing');
                setError('');
              }}
            >
              <ChevronLeft size={16} /> Back to Overview
            </button>

            <div className="mobile-brand" onClick={() => setView('landing')}>
              <ShieldCheck /> TrustShare
            </div>
            <div className="auth-kicker">WELCOME TO TRUSTSHARE</div>
            <h2>{mode === 'login' ? 'Welcome back' : 'Create your workspace'}</h2>
            <p className="muted">
              {mode === 'login'
                ? 'Sign in to continue to your secure workspace.'
                : 'Set up an account to keep your files organized.'}
            </p>

            {error && (
              <div className="alert error">
                <AlertCircle size={16} />
                {String(error)}
              </div>
            )}

            <form onSubmit={submitAuth} className="auth-form">
              {mode === 'register' && (
                <label>
                  Full name
                  <input
                    required
                    minLength="2"
                    placeholder="Your name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </label>
              )}
              <label>
                Email address
                <input
                  type="email"
                  required
                  placeholder="you@company.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  required
                  minLength={mode === 'register' ? 8 : 1}
                  placeholder={mode === 'register' ? 'At least 8 characters' : 'Enter your password'}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </label>

              {mode === 'login' && (
                <label>
                  Authenticator or backup code (if enabled)
                  <input
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="Enter 6-digit code"
                    value={form.otp}
                    onChange={(e) => setForm({ ...form, otp: e.target.value })}
                  />
                </label>
              )}

              {mode === 'login' && (
                <button
                  type="button"
                  className="forgot"
                  onClick={() => {
                    setMode('reset');
                    setError('');
                  }}
                >
                  Forgot password?
                </button>
              )}

              {mode === 'reset' ? (
                <div className="alert">
                  Password recovery UI foundation is ready. Email reset delivery is not configured in Milestone 1.
                </div>
              ) : (
                <button className="primary wide" disabled={busy}>
                  {busy ? 'Please wait…' : mode === 'login' ? 'Sign in securely' : 'Create account'}
                  <ArrowRight size={17} />
                </button>
              )}
            </form>

            {mode === 'reset' ? (
              <button className="switch" onClick={() => setMode('login')}>
                Back to sign in
              </button>
            ) : (
              <div className="auth-switch">
                {mode === 'login' ? 'New to TrustShare?' : 'Already have an account?'}
                <button
                  onClick={() => {
                    setMode(mode === 'login' ? 'register' : 'login');
                    setError('');
                  }}
                >
                  {mode === 'login' ? 'Create an account' : 'Sign in'}
                </button>
              </div>
            )}

            <div className="auth-note">
              <LockKeyhole size={14} /> Your password is securely hashed before storage.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // VIEW 3: WORKSPACE DASHBOARD
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand side-brand cursor-pointer" onClick={() => setView('landing')} title="Go to public page">
          <span className="brand-icon">
            <ShieldCheck />
          </span>
          <span>
            trust<span className="brand-light">share</span>
          </span>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <button
          className={`nav-item ${activeFolder === null ? 'selected' : ''}`}
          onClick={() => setActiveFolder(null)}
        >
          <Files size={18} /> All files <span className="nav-count">{files.length}</span>
        </button>
        <button className="nav-item" onClick={() => setShowSecurityCenter(true)}>
          <ShieldCheck size={18} /> Security Center
        </button>

        <div className="folder-head">
          <span>YOUR FOLDERS</span>
          <button title="Create folder" onClick={openFolderModal}>
            <Plus size={16} />
          </button>
        </div>

        <div className="folder-nav">
          {folders.map((f) => (
            <button
              key={f.id}
              className={`nav-item ${activeFolder === f.id ? 'selected' : ''}`}
              onClick={() => setActiveFolder(f.id)}
            >
              <Folder size={17} />
              <span className="folder-name">{f.name}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="storage-card">
            <div className="storage-icon">
              <HardDrive size={17} />
            </div>
            <div className="storage-title">Workspace storage</div>
            <div className="storage-sub">{sizeText(total)} in current view</div>
            <div className="storage-track">
              <span style={{ width: Math.min(100, (total / (10 * 1024 * 1024)) * 100) + '%' }} />
            </div>
            <small>Local development storage</small>
          </div>

          <div className="user-mini">
            <div className="avatar">{user.name?.slice(0, 1).toUpperCase()}</div>
            <div className="user-mini-copy">
              <b>{user.name}</b>
              <span>{user.role}</span>
            </div>
            <button onClick={logout} title="Sign out">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <span>/</span>{' '}
              <b>{activeFolder ? folders.find((f) => f.id === activeFolder)?.name : 'All files'}</b>
            </div>
            <div className="top-sub">A little more order for your workday.</div>
          </div>
          <div className="top-actions">
            <button
              onClick={() => setView('landing')}
              className="secondary preview-landing-btn"
              title="View Public Landing Page"
            >
              <ExternalLink size={13} />
              Public Overview
            </button>
            <div className="secure-label">
              <span className="green-dot" /> Secure session
            </div>
            <div className="avatar top-avatar">{user.name?.slice(0, 1).toUpperCase()}</div>
          </div>
        </header>

        <section className="content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">YOUR DIGITAL WORKSPACE</div>
              <h1>{activeFolder ? folders.find((f) => f.id === activeFolder)?.name : 'Your files, in focus.'}</h1>
              <p className="muted">Keep everything tidy, searchable, and right where you need it.</p>
            </div>
            <button className="primary upload-btn" onClick={openUploadModal}>
              <Upload size={17} />
              Upload file
            </button>
          </div>

          {(notice || error) && (
            <div className={`alert ${error ? 'error' : 'success'}`}>
              <span>{error || notice}</span>
              <button
                onClick={() => {
                  setError('');
                  setNotice('');
                }}
              >
                ×
              </button>
            </div>
          )}

          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-icon purple">
                <Files size={19} />
              </div>
              <div className="stat-label">FILES IN VIEW</div>
              <div className="stat-value">{files.length}</div>
              <div className="stat-foot">Documents and assets</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon blue">
                <Folder size={19} />
              </div>
              <div className="stat-label">YOUR FOLDERS</div>
              <div className="stat-value">{folders.length}</div>
              <div className="stat-foot">Made for your workflow</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon green">
                <HardDrive size={19} />
              </div>
              <div className="stat-label">STORAGE IN VIEW</div>
              <div className="stat-value">{sizeText(total)}</div>
              <div className="stat-foot">Current selection</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon amber">
                <ShieldCheck size={19} />
              </div>
              <div className="stat-label">ACCESS STATUS</div>
              <div className="stat-value status-value">Protected</div>
              <div className="stat-foot">Signed in as {user.role}</div>
            </div>
          </div>

          <div className="file-panel">
            <div className="panel-head">
              <div>
                <h3>File inventory</h3>
                <p className="muted">Your uploaded files, all in one place.</p>
              </div>
              <div className="panel-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    placeholder="Search files…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  {query && <button onClick={() => setQuery('')}>×</button>}
                </div>
                <button className="secondary" onClick={openFolderModal}>
                  <Plus size={16} /> New folder
                </button>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>NAME</th>
                    <th>FILE SIZE</th>
                    <th>DATE ADDED</th>
                    <th>TYPE</th>
                    <th className="right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((f) => (
                    <tr key={f.id}>
                      <td>
                        <div className="file-name-cell">
                          <div className="file-type-icon">
                            {f.content_type?.includes('image') ? (
                              <ImageIcon size={18} />
                            ) : f.name.match(/\.(xlsx|csv)$/i) ? (
                              <FileSpreadsheet size={18} />
                            ) : (
                              <FileText size={18} />
                            )}
                          </div>
                          <div className="file-name-text">
                            <b>{f.name}</b>
                            <span title={`SHA-256: ${f.sha256}`}>
                              {f.sha256 ? `SHA: ${f.sha256.slice(0, 12)}...` : 'Owned by you'}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>{sizeText(f.size)}</td>
                      <td>{f.uploaded_at ? new Date(f.uploaded_at).toLocaleDateString() : '—'}</td>
                      <td>
                        <span className="type-pill">{f.name.split('.').pop().toUpperCase()}</span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            title="Inspect MongoDB Metadata Details"
                            onClick={() => openFileDetails(f)}
                            className="hover:text-emerald-700"
                          >
                            <Info size={16} />
                          </button>
                          <button title="Download" onClick={() => downloadFile(f)}>
                            <Download size={16} />
                          </button>
                          <button title="Delete" onClick={() => deleteFile(f)}>
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!files.length && (
                    <tr>
                      <td colSpan="5">
                        <div className="empty-state">
                          <div className="empty-icon">
                            <Files size={25} />
                          </div>
                          <b>{query ? 'No matching files' : 'Your workspace starts here'}</b>
                          <p>
                            {query
                              ? 'Try another search term.'
                              : 'Upload a document to see it appear in your file inventory.'}
                          </p>
                          {!query && (
                            <button className="secondary" onClick={openUploadModal}>
                              <Upload size={15} /> Upload your first file
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="panel-foot">
              <span>
                Showing <b>{files.length}</b> file{files.length === 1 ? '' : 's'}
              </span>
              <span>
                <span className="green-dot" /> Synced with workspace
              </span>
            </div>
          </div>

          <div className="bottom-note">
            <ShieldCheck size={17} />
            <span>
              <b>Your workspace, thoughtfully protected.</b> Milestone 1 uses authenticated access and local
              development storage. Encryption and cloud sharing are planned for Milestone 2.
            </span>
          </div>

          <div className="service-status">
            Service status{' '}
            {['postgres', 'mongodb', 'redis'].map((k) => (
              <span key={k} className={health[k] === 'connected' ? 'healthy' : 'unknown'}>
                {k}: {health[k] || 'checking'}
              </span>
            ))}
          </div>
        </section>
      </main>

      {/* ITEM 5: UPLOAD MODAL */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                  <UploadCloud size={18} />
                </div>
                <div>
                  <h3 className="font-['Manrope'] font-bold text-slate-800 text-base m-0">Upload Document</h3>
                  <p className="text-xs text-slate-400 m-0">Max 10 MiB • Encrypted verification</p>
                </div>
              </div>
              <button
                onClick={() => !uploading && setIsUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
                disabled={uploading}
              >
                <X size={18} />
              </button>
            </div>

            {uploadModalError && (
              <div className="alert error text-xs">
                <AlertCircle size={15} />
                <span>{uploadModalError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="flex flex-col gap-4">
              {/* Folder Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Target Workspace Folder
                </label>
                <select
                  value={uploadFolderId}
                  onChange={(e) => setUploadFolderId(e.target.value)}
                  disabled={uploading}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-700 bg-slate-50 focus:outline-none focus:border-emerald-600"
                >
                  <option value="">Workspace Root (No Folder)</option>
                  {folders.map((fld) => (
                    <option key={fld.id} value={fld.id}>
                      📁 {fld.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Drag and Drop Zone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!uploading) setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (uploading) return;
                  const f = e.dataTransfer.files?.[0];
                  if (f) validateAndSetUploadFile(f);
                }}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-all flex flex-col items-center justify-center gap-2 cursor-pointer ${
                  isDragging
                    ? 'border-emerald-600 bg-emerald-50/50'
                    : uploadFileObj
                    ? 'border-emerald-300 bg-emerald-50/20'
                    : 'border-slate-200 hover:border-emerald-500 bg-slate-50/50'
                }`}
                onClick={() => {
                  if (!uploading) {
                    const el = document.getElementById('modal-file-input');
                    if (el) el.click();
                  }
                }}
              >
                <input
                  id="modal-file-input"
                  type="file"
                  hidden
                  accept=".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp"
                  disabled={uploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) validateAndSetUploadFile(f);
                  }}
                />

                <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-1">
                  <UploadCloud size={24} />
                </div>
                <div className="text-xs font-semibold text-slate-700">
                  {uploadFileObj ? (
                    <span className="text-emerald-700 font-bold">{uploadFileObj.name}</span>
                  ) : (
                    <span>Click to browse or drag file into this zone</span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400">
                  {uploadFileObj ? (
                    <span>Size: {sizeText(uploadFileObj.size)}</span>
                  ) : (
                    <span>Supported: PDF, DOCX, XLSX, CSV, TXT, PNG, JPG, WEBP (Up to 10MB)</span>
                  )}
                </div>
              </div>

              {/* Progress bar */}
              {uploading && (
                <div className="flex flex-col gap-1.5 pt-1">
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>Uploading file...</span>
                    <span className="font-semibold text-emerald-700">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-emerald-700 h-2.5 rounded-full transition-all duration-200"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={uploading}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !uploadFileObj}
                  className="px-5 py-2 rounded-lg text-xs font-semibold text-white bg-emerald-800 hover:bg-emerald-700 shadow-md shadow-emerald-800/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  {uploading ? 'Uploading...' : 'Confirm Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ITEM 6: FOLDER MODAL */}
      {isFolderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Folder size={18} className="text-emerald-700" />
                <h3 className="font-['Manrope'] font-bold text-slate-800 text-base m-0">Create Folder</h3>
              </div>
              <button
                onClick={() => setIsFolderModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            {folderModalError && (
              <div className="alert error text-xs">
                <AlertCircle size={15} />
                <span>{folderModalError}</span>
              </div>
            )}

            <form onSubmit={handleFolderSubmit} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Folder Name
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  maxLength={120}
                  placeholder="e.g., Contracts, Financials, Audits"
                  value={folderNameInput}
                  onChange={(e) => setFolderNameInput(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 bg-slate-50 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsFolderModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg text-xs font-semibold text-white bg-emerald-800 hover:bg-emerald-700 shadow-md shadow-emerald-800/20"
                >
                  Create Folder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ITEM 4: FILE DETAILS MODAL (MONGODB METADATA) */}
      {detailsFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                  <Info size={18} />
                </div>
                <div>
                  <h3 className="font-['Manrope'] font-bold text-slate-800 text-base m-0">
                    File Metadata Details
                  </h3>
                  <span className="text-[11px] text-slate-400">
                    Stored Metadata Record & Cryptographic Signature
                  </span>
                </div>
              </div>
              <button
                onClick={() => setDetailsFile(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            {loadingMetadata ? (
              <div className="py-8 text-center text-xs text-slate-400">
                Querying metadata from store...
              </div>
            ) : fileMetadata ? (
              <div className="flex flex-col gap-3 text-xs">
                <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <span className="text-slate-500 font-medium">Metadata Store Source:</span>
                  <span
                    className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                      fileMetadata.source === 'mongodb'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {fileMetadata.source === 'mongodb' ? 'MongoDB (Document Store)' : 'Relational PostgreSQL Index'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Original Name</div>
                    <div className="font-semibold text-slate-800 truncate" title={fileMetadata.metadata?.name}>
                      {fileMetadata.metadata?.name}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">File Size</div>
                    <div className="font-semibold text-slate-800">
                      {sizeText(fileMetadata.metadata?.size)} ({fileMetadata.metadata?.size} bytes)
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Content Type</div>
                    <div className="font-semibold text-slate-800">
                      {fileMetadata.metadata?.content_type}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Uploaded At</div>
                    <div className="font-semibold text-slate-800">
                      {fileMetadata.metadata?.uploaded_at
                        ? new Date(fileMetadata.metadata.uploaded_at).toLocaleString()
                        : '—'}
                    </div>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 flex flex-col gap-1">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">SHA-256 Digest</div>
                  <div className="font-mono text-[11px] text-emerald-800 break-all select-all">
                    {fileMetadata.metadata?.sha256}
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 flex flex-col gap-1">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Disk Storage Identifier</div>
                  <div className="font-mono text-[11px] text-slate-600 break-all">
                    {fileMetadata.metadata?.stored_name || '—'}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-400 text-center py-4">No metadata found.</div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setDetailsFile(null)}
                className="px-5 py-2 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      {showSecurityCenter && <SecurityCenter token={token} user={user} onClose={() => setShowSecurityCenter(false)} />}
    </div>
  );
}

export default App;
