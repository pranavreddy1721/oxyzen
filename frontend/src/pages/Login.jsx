import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Wind, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function Login() {
  const { login, formatApiError } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 flex flex-col items-center text-center">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Wind className="h-6 w-6" strokeWidth={2} /></span>
        <h1 className="font-heading text-3xl font-black tracking-tight">Welcome back</h1>
        <p className="mt-1 text-muted-foreground">Sign in to access your dashboard and saved locations.</p>
      </div>

      <form onSubmit={submit} className="space-y-4 rounded-xl border border-border bg-card p-6" data-testid="login-form">
        {error && <div className="rounded-lg bg-destructive/10 px-4 py-2.5 text-sm text-destructive" data-testid="login-error">{error}</div>}
        <div>
          <label className="mb-1.5 block text-sm font-medium">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email"
            className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Password</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password"
            className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
        </div>
        <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit">
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={1.5} />} Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        No account? <Link to="/register" className="font-medium text-primary hover:underline">Create one</Link>
      </p>
    </div>
  );
}
