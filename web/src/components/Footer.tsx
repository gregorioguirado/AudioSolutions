export default function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-5xl items-center justify-between text-xs text-muted">
        <p>
          <span className="font-bold text-accent">★ Showfier</span> © {new Date().getFullYear()}
          <span className="ml-3 text-[10px] text-muted/50">v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
        </p>
        <div className="flex gap-6">
          <a href="#" className="text-muted hover:text-white no-underline">Privacy</a>
          <a href="/legal/terms-of-service" className="text-muted hover:text-white no-underline">Terms</a>
          <a href="/legal/translation-accuracy-disclaimer" className="text-muted hover:text-white no-underline">Disclaimer</a>
          <a href="#" className="text-muted hover:text-white no-underline">Contact</a>
        </div>
      </div>
    </footer>
  );
}
