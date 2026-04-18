import { formatDistanceToNow } from "date-fns";

interface Props {
  iso: string;
}

export default function Timecode({ iso }: Props) {
  if (!iso) {
    return (
      <span className="flex flex-col items-end leading-tight">
        <span data-testid="timecode-relative" className="text-xs font-bold text-muted">—</span>
      </span>
    );
  }

  const date = new Date(iso);
  const relative = formatDistanceToNow(date, { addSuffix: true });

  const dateFmt = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZoneName: "short",
  });
  const absolute = dateFmt.format(date);

  return (
    <span className="flex flex-col items-end leading-tight whitespace-nowrap">
      <span data-testid="timecode-relative" className="text-xs font-bold text-white">{relative}</span>
      <span data-testid="timecode-absolute" className="mt-0.5 text-[11px] text-muted">{absolute}</span>
    </span>
  );
}
