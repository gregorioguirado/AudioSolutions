import UploadFlow from "@/components/UploadFlow";

export default function TranslatePage() {
  return (
    <main className="py-12">
      <div className="mx-auto max-w-2xl px-6 text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Translate your show file</h1>
        <p className="mt-2 text-sm text-muted">
          Upload a Yamaha CL/QL or DiGiCo SD/Quantum file and get a translated version in 30 seconds.
        </p>
      </div>
      <div className="mt-10">
        <UploadFlow />
      </div>
    </main>
  );
}
