import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Wind, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function Register() {
  const { register, formatApiError } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(name, email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 flex flex-col items-center text-center">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Wind className="h-6 w-6" strokeWidth={2} /></span>
        <h1 className="font-heading text-3xl font-black tracking-tight">Create your account</h1>
        <p className="mt-1 text-muted-foreground">Save locations, track exposure and set AQI alerts.</p>
      </div>

      <form onSubmit={submit} className="space-y-4 rounded-xl border border-border bg-card p-6" data-testid="register-form">
        {error && <div className="rounded-lg bg-destructive/10 px-4 py-2.5 text-sm text-destructive" data-testid="register-error">{error}</div>}
        <div>
          <label className="mb-1.5 block text-sm font-medium">Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} data-testid="register-name"
            className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="register-email"
            className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Password</label>
          <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="register-password"
            className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-primary" />
          <p className="mt-1 text-xs text-muted-foreground">At least 6 characters.</p>
        </div>
        <Button type="submit" className="w-full" disabled={loading} data-testid="register-submit">
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={1.5} />} Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account? <Link to="/login" className="font-medium text-primary hover:underline">Sign in</Link>
      </p>
    </div>
  );
}
