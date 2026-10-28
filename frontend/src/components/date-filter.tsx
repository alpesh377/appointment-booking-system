"use client";

import { Label } from "@/components/ui/label";
import { DatePicker } from "@/components/ui/date-picker";

export function DateFilter({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  /** ISO date (`yyyy-MM-dd`) or an empty string. */
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <DatePicker id={id} value={value} onChange={onChange} className="w-full" />
    </div>
  );
}
