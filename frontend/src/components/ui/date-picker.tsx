"use client";

import * as React from "react";
import { format, parseISO } from "date-fns";
import { CalendarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export function DatePicker({
  id,
  value,
  onChange,
  placeholder = "dd/mm/yyyy",
  className,
  disabled,
  from,
  to,
  "aria-label": ariaLabel,
}: {
  id?: string;
  /** ISO date (`yyyy-MM-dd`) or an empty string. */
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  /** Earliest selectable day, ISO `yyyy-MM-dd`. Earlier days are disabled. */
  from?: string;
  /** Latest selectable day, ISO `yyyy-MM-dd`. Later days are disabled. */
  to?: string;
  "aria-label"?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const selected = value ? parseISO(value) : undefined;
  const unavailable = React.useMemo(() => {
    const matchers: Array<{ before: Date } | { after: Date }> = [];
    if (from) matchers.push({ before: parseISO(from) });
    if (to) matchers.push({ after: parseISO(to) });
    return matchers;
  }, [from, to]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          disabled={disabled}
          aria-label={ariaLabel}
          className={cn(
            "h-10 justify-start px-3 text-left font-normal",
            !selected && "text-muted-foreground",
            className,
          )}
        >
          <CalendarIcon className="size-4" />
          {selected ? format(selected, "dd/MM/yyyy") : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selected}
          defaultMonth={selected ?? (from ? parseISO(from) : undefined)}
          disabled={unavailable.length > 0 ? unavailable : undefined}
          onSelect={(next) => {
            onChange(next ? format(next, "yyyy-MM-dd") : "");
            setOpen(false);
          }}
          autoFocus
        />
        {selected ? (
          <div className="border-t p-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
            >
              Clear date
            </Button>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}
