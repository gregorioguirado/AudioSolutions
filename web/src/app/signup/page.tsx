import SignupForm from "@/components/SignupForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Create account</h1>
      <p className="mt-2 text-sm text-muted">First translation is free. No credit card required.</p>
      <div className="mt-8">
        <SignupForm />
      </div>
    </main>
  );
}
