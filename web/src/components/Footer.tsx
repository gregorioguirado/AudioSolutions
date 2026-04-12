export default function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-5xl items-center justify-between text-xs text-muted">
        <p>
          <span className="font-bold text-accent">★ Showfier</span> © {new Date().getFullYear()}
        </p>
        <div className="flex gap-6">
          <a href="#" className="text-muted hover:text-white no-underline">Privacy</a>
          <a href="#" className="text-muted hover:text-white no-underline">Terms</a>
          <a href="#" className="text-muted hover:text-white no-underline">Contact</a>
        </div>
      </div>
    </footer>
  );
}
