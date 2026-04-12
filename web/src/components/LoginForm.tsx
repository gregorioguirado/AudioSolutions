"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  };

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
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="Your password"
        />
      </div>

      {error && <p className="text-xs text-error">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="mt-2 bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50"
      >
        {loading ? "Logging in..." : "Log in"}
      </button>

      <p className="text-center text-xs text-muted">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-accent">
          Sign up
        </Link>
      </p>
    </form>
  );
}
