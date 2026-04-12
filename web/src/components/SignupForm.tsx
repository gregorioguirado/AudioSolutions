"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    setSuccess(true);
  };

  if (success) {
    return (
      <div className="text-center">
        <p className="text-xl font-bold text-accent">Check your email</p>
        <p className="mt-3 text-sm text-muted">
          We sent a verification link to <strong className="text-white">{email}</strong>.
          Click it to activate your account.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-muted">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-muted">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="Min 8 characters"
        />
      </div>

      {error && <p className="text-xs text-error">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="mt-2 bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create account"}
      </button>

      <p className="text-center text-xs text-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-accent">
          Log in
        </Link>
      </p>
    </form>
  );
}
