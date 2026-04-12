"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function SignupWall({ onClose, onSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkEmail, setCheckEmail] = useState(false);
  const [mode, setMode] = useState<"signup" | "login">("signup");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();

    if (mode === "signup") {
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${window.location.pathname}`,
        },
      });
      setLoading(false);
      if (signUpError) {
        setError(signUpError.message);
        return;
      }
      setCheckEmail(true);
    } else {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      setLoading(false);
      if (signInError) {
        setError(signInError.message);
        return;
      }
      onSuccess();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md border border-border bg-bg p-8">
        <button type="button" onClick={onClose} className="float-right text-muted hover:text-white">×</button>

        {checkEmail ? (
          <div className="text-center">
            <p className="text-xl font-bold text-accent">Check your email</p>
            <p className="mt-3 text-sm text-muted">
              We sent a verification link to <strong className="text-white">{email}</strong>. Click it, then come back here to download.
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
            <h2 className="mt-2 text-xl font-extrabold uppercase tracking-tight">
              {mode === "signup" ? "Sign up to download" : "Log in to download"}
            </h2>
            <p className="mt-1 text-xs text-muted">
              {mode === "signup" ? "First translation is free. No credit card required." : "Welcome back."}
            </p>

            <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
              <div>
                <label htmlFor="wall-email" className="text-xs font-bold uppercase tracking-wider text-muted">Email</label>
                <input id="wall-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
                  placeholder="you@example.com" />
              </div>
              <div>
                <label htmlFor="wall-password" className="text-xs font-bold uppercase tracking-wider text-muted">Password</label>
                <input id="wall-password" type="password" required minLength={mode === "signup" ? 8 : 1}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
                  placeholder={mode === "signup" ? "Min 8 characters" : "Your password"} />
              </div>
              {error && <p className="text-xs text-error">{error}</p>}
              <button type="submit" disabled={loading}
                className="bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50">
                {loading ? "Working..." : mode === "signup" ? "Create account" : "Log in"}
              </button>
            </form>

            <p className="mt-4 text-center text-xs text-muted">
              {mode === "signup" ? (
                <>Already have an account?{" "}<button type="button" onClick={() => setMode("login")} className="text-accent hover:underline">Log in</button></>
              ) : (
                <>Need an account?{" "}<button type="button" onClick={() => setMode("signup")} className="text-accent hover:underline">Sign up</button></>
              )}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
