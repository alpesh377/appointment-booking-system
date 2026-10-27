import { z } from "zod";

export function isValidTimeZone(name: string): boolean {
  if (!name.trim()) return false;
  try {
    new Intl.DateTimeFormat("en-GB", { timeZone: name });
    return true;
  } catch {
    return false;
  }
}

const timezone = z
  .string()
  .trim()
  .min(1, "Enter an IANA timezone.")
  .refine(isValidTimeZone, "Use an IANA timezone such as Europe/London.");

const optionalPhone = z
  .string()
  .trim()
  .max(50, "Use at most 50 characters.")
  .optional()
  .or(z.literal(""));

const optionalBio = z
  .string()
  .trim()
  .max(2000, "Use at most 2000 characters.")
  .optional()
  .or(z.literal(""));

/**
 * Client-side schemas mirror the FastAPI request models so obvious mistakes are
 * caught before a round trip. The server remains the authority.
 */
export const loginSchema = z.object({
  email: z.string().trim().pipe(z.email("Enter a valid email address.")),
  password: z.string().min(1, "Enter your password."),
});

export const registerSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Enter your name.")
    .max(200, "Use at most 200 characters."),
  email: z.string().trim().pipe(z.email("Enter a valid email address.")),
  phone: optionalPhone,
  password: z
    .string()
    .min(8, "Use at least 8 characters.")
    .max(200, "Use at most 200 characters."),
});

export const profileSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Enter your name.")
    .max(200, "Use at most 200 characters."),
  phone: optionalPhone,
});

export const serviceSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Enter a service name.")
    .max(200, "Use at most 200 characters."),
  category: z
    .string()
    .trim()
    .min(1, "Enter a category.")
    .max(120, "Use at most 120 characters."),
  duration_minutes: z
    .number({ error: "Enter a duration in minutes." })
    .int("Use a whole number of minutes.")
    .min(15, "Use at least 15 minutes.")
    .max(480, "Use at most 480 minutes.")
    .refine((value) => value % 5 === 0, "Use steps of 5 minutes."),
});

export const practiceSchema = z.object({
  display_name: z
    .string()
    .trim()
    .min(1, "Enter your display name.")
    .max(200, "Use at most 200 characters."),
  category: z
    .string()
    .trim()
    .min(1, "Enter a category.")
    .max(120, "Use at most 120 characters."),
  bio: optionalBio,
  timezone,
});

export const providerAccountSchema = z.object({
  email: z.string().trim().pipe(z.email("Enter a valid email address.")),
  password: z
    .string()
    .min(8, "Use at least 8 characters.")
    .max(200, "Use at most 200 characters."),
  full_name: z
    .string()
    .trim()
    .min(1, "Enter the provider's name.")
    .max(200, "Use at most 200 characters."),
  display_name: z
    .string()
    .trim()
    .min(1, "Enter the public display name.")
    .max(200, "Use at most 200 characters."),
  category: z
    .string()
    .trim()
    .min(1, "Enter a category.")
    .max(120, "Use at most 120 characters."),
  bio: optionalBio,
  phone: optionalPhone,
  timezone,
});

export const providerProfileSchema = practiceSchema;

const clock = z
  .string()
  .regex(/^([01]\d|2[0-3]):[0-5]\d$/, "Use a valid 24-hour time such as 09:00.");

const orderedTimes = {
  end_time: clock,
  start_time: clock,
};

function timesAreOrdered(value: { start_time: string; end_time: string }): boolean {
  return value.end_time > value.start_time;
}

export const availabilityWindowSchema = z
  .object({ weekday: z.number().int().min(0).max(6), ...orderedTimes })
  .refine(timesAreOrdered, { message: "End time must be after start time.", path: ["end_time"] });

export const availabilityWindowsSchema = z.object({
  windows: z.array(availabilityWindowSchema),
});

export const availabilityBreakSchema = z
  .object({
    kind: z.enum(["weekday", "date"]),
    weekday: z.number().int().min(0).max(6),
    date: z.string(),
    ...orderedTimes,
  })
  .refine(timesAreOrdered, { message: "End time must be after start time.", path: ["end_time"] })
  .refine((value) => value.kind === "weekday" || value.date !== "", {
    message: "Choose a date for this break.",
    path: ["date"],
  });

export const availabilityBreaksSchema = z.object({
  breaks: z.array(availabilityBreakSchema),
});

export const availabilityOverrideSchema = z
  .object({
    date: z.string().min(1, "Choose a date for this override."),
    is_closed: z.boolean(),
    note: z.string().max(300, "Use at most 300 characters."),
    windows: z.array(z.object(orderedTimes)),
  })
  .superRefine((value, ctx) => {
    if (value.is_closed) return;
    value.windows.forEach((window, index) => {
      if (!timesAreOrdered(window)) {
        ctx.addIssue({
          code: "custom",
          message: "End time must be after start time.",
          path: ["windows", index, "end_time"],
        });
      }
    });
  });

export const availabilityOverridesSchema = z.object({
  overrides: z.array(availabilityOverrideSchema),
});

export const reasonSchema = z.object({
  reason: z.string().trim().max(500, "Use at most 500 characters."),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ProfileValues = z.infer<typeof profileSchema>;
export type ServiceValues = z.infer<typeof serviceSchema>;
export type PracticeValues = z.infer<typeof practiceSchema>;
export type ProviderAccountValues = z.infer<typeof providerAccountSchema>;
export type ProviderProfileValues = z.infer<typeof providerProfileSchema>;
export type ReasonValues = z.infer<typeof reasonSchema>;
