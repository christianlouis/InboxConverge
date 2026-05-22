import { Mail } from 'lucide-react';

interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <span className="inline-flex items-center gap-2.5 text-slate-950">
      <span className="inline-grid h-8 w-8 place-items-center rounded-md border-2 border-blue-600 bg-white text-blue-600">
        <Mail className="h-5 w-5" aria-hidden="true" />
      </span>
      {!compact && <span className="text-xl font-extrabold tracking-normal">InboxConverge</span>}
    </span>
  );
}
