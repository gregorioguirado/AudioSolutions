import Link from "next/link";

export default function Nav() {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between border-b border-border bg-bg/90 px-6 py-3 backdrop-blur-sm">
      <Link href="/" className="text-sm font-bold uppercase tracking-widest text-accent no-underline">
        ★ Showfier
      </Link>

      <div className="flex items-center gap-6 text-xs uppercase tracking-wider">
        <a href="#how-it-works" className="text-muted hover:text-white no-underline">
          How it works
        </a>
        <a href="#pricing" className="text-muted hover:text-white no-underline">
          Pricing
        </a>
        <a href="#faq" className="text-muted hover:text-white no-underline">
          FAQ
        </a>
        <Link href="/login" className="text-muted hover:text-white no-underline">
          Log in
        </Link>
        <Link
          href="/signup"
          className="bg-accent px-3 py-1.5 font-bold text-black no-underline hover:bg-yellow-300"
        >
          Sign up
        </Link>
      </div>
    </nav>
  );
}
