export default function VerifyBanner() {
  return (
    <div className="border border-warning/30 bg-warning/5 px-5 py-4">
      <p className="text-sm font-bold text-warning">Always verify before the show</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        Load this file on the target console, check the patch list, and spot-check EQ and dynamics on key channels before soundcheck.
      </p>
    </div>
  );
}
