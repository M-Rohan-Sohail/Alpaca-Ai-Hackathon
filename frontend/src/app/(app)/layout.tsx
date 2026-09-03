import { AppShell } from "@/components/layout/AppShell";

export default function AppGroupLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}
