import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Log in</h1>
      <p className="mt-2 text-sm text-muted">Welcome back.</p>
      <div className="mt-8">
        <LoginForm />
      </div>
    </main>
  );
}
