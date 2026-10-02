import AppShell from "@/features/shell/app-shell";

// Every owner page shares the sidebar and the scene behind the content.
// The (owner) folder groups pages without adding "/owner" to the address.
export default function OwnerLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
