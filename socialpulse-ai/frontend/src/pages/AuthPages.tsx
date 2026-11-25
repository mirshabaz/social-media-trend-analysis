import { useState, type FormEvent } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { Activity, LockKeyhole, Mail, User } from "lucide-react"
import { useApp } from "../context/AppContext"

export function LoginPage() {
  const { user, login } = useApp()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  if (user) return <Navigate to="/" replace />
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); setError(""); try { await login(email, password); navigate("/") } catch (err) { setError(err instanceof Error ? err.message : "Login failed") } finally { setLoading(false) } }
  return <AuthShell title="Welcome back" subtitle="Sign in to your SOCIALPULSE AI workspace"><form onSubmit={submit} className="space-y-4"><Field icon={<Mail size={15} />} label="Email" type="email" value={email} onChange={setEmail} /><Field icon={<LockKeyhole size={15} />} label="Password" type="password" value={password} onChange={setPassword} />{error && <p className="text-xs text-rose-400">{error}</p>}<button className="sp-btn-primary w-full" type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign In"}</button><p className="text-xs text-center text-[var(--text-secondary)]">No account? <Link className="text-[var(--accent-primary)]" to="/register">Create one</Link></p></form></AuthShell>
}

export function RegisterPage() {
  const { user, register } = useApp()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [organization, setOrganization] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  if (user) return <Navigate to="/" replace />
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); setError(""); try { await register({ full_name: fullName, email, password, organization }); navigate("/") } catch (err) { setError(err instanceof Error ? err.message : "Registration failed") } finally { setLoading(false) } }
  return <AuthShell title="Create your workspace" subtitle="Start analyzing real social media datasets"><form onSubmit={submit} className="space-y-4"><Field icon={<User size={15} />} label="Full name" value={fullName} onChange={setFullName} /><Field icon={<Mail size={15} />} label="Email" type="email" value={email} onChange={setEmail} /><Field icon={<LockKeyhole size={15} />} label="Password" type="password" value={password} onChange={setPassword} /><Field icon={<Activity size={15} />} label="Organization (optional)" value={organization} onChange={setOrganization} />{error && <p className="text-xs text-rose-400">{error}</p>}<button className="sp-btn-primary w-full" type="submit" disabled={loading}>{loading ? "Creating account..." : "Create Account"}</button><p className="text-xs text-center text-[var(--text-secondary)]">Already registered? <Link className="text-[var(--accent-primary)]" to="/login">Sign in</Link></p></form></AuthShell>
}

function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <div className="min-h-screen grid place-items-center bg-[var(--bg-primary)] px-4"><div className="w-full max-w-md sp-card p-6 sm:p-8"><div className="flex items-center gap-3 mb-6"><div className="w-10 h-10 rounded-xl grid place-items-center text-white bg-gradient-to-br from-[#7C5CFC] to-[#00D4FF]"><Activity size={20} /></div><div><strong>SOCIALPULSE AI</strong><p className="text-[10px] text-[var(--text-muted)] m-0">INTELLIGENCE WORKSPACE</p></div></div><h1 className="text-2xl font-bold m-0">{title}</h1><p className="text-sm text-[var(--text-secondary)] mt-2 mb-6">{subtitle}</p>{children}</div></div>
}

function Field({ icon, label, type = "text", value, onChange }: { icon: React.ReactNode; label: string; type?: string; value: string; onChange: (value: string) => void }) {
  return <label className="block text-xs font-semibold text-[var(--text-secondary)]">{label}<div className="relative mt-1.5"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">{icon}</span><input className="sp-input w-full !pl-9" type={type} value={value} onChange={(e) => onChange(e.target.value)} required={label !== "Organization (optional)"} /></div></label>
}
