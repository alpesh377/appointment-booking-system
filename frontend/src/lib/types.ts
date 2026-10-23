export type Role = "ADMIN" | "PROVIDER" | "CUSTOMER";

export type AppointmentStatus =
  | "PENDING"
  | "CONFIRMED"
  | "REJECTED"
  | "CANCELLED"
  | "COMPLETED"
  | "EXPIRED"
  | "RESCHEDULED";

export interface User {
  id: string;
  email: string;
  role: Role;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  provider_id?: string;
}

export interface Service {
  id: string;
  provider_id: string;
  name: string;
  category: string;
  duration_minutes: number;
  is_active: boolean;
}

export interface ProviderSummary {
  id: string;
  display_name: string;
  category: string;
  timezone: string;
  is_active: boolean;
  durations: number[];
}

export interface Provider extends ProviderSummary {
  bio: string | null;
  user_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  services: Service[];
}

export interface Appointment {
  id: string;
  status: AppointmentStatus;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  notes: string | null;
  hold_expires_at: string | null;
  rescheduled_from_id: string | null;
  rescheduled_to_id: string | null;
  cancelled_by_role: string | null;
  cancellation_reason: string | null;
  created_at: string;
  provider: { id: string; display_name: string; category: string; timezone: string };
  service: { id: string; name: string; category: string; duration_minutes: number };
  customer: { id: string; full_name: string; email: string };
  events?: AppointmentEvent[];
}

export interface AppointmentEvent {
  id: string;
  from_status: AppointmentStatus | null;
  to_status: AppointmentStatus;
  actor_user_id: string | null;
  actor_role: string;
  reason: string | null;
  created_at: string;
}

export interface CustomerDashboard {
  upcoming: Appointment[];
  past: Appointment[];
  cancelled: Appointment[];
}

export interface ProviderDashboard {
  today: Appointment[];
  upcoming: Appointment[];
  pending: Appointment[];
  awaiting_completion: Appointment[];
  conflicts: Appointment[];
}

export interface AdminStats {
  customers: number;
  providers: number;
  appointments: number;
  by_status: Record<string, number>;
}

export interface AvailabilityWindow {
  id?: string;
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface AvailabilityBreak {
  id?: string;
  weekday: number | null;
  date: string | null;
  start_time: string;
  end_time: string;
}

export interface DateOverride {
  id?: string;
  date: string;
  is_closed: boolean;
  note: string | null;
  windows: { start_time: string; end_time: string }[];
}

export interface AvailabilityState {
  provider_id: string;
  timezone: string;
  windows: AvailabilityWindow[];
  breaks: AvailabilityBreak[];
  overrides: DateOverride[];
}

export interface SlotResponse {
  provider_id: string;
  service_id: string;
  timezone: string;
  slots: string[];
}

export interface AdminAppointments {
  items: Appointment[];
  total: number;
  page: number;
  page_size: number;
}
