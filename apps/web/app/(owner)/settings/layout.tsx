import SettingsNav from "@/features/settings/settings-nav";

// Wraps every /settings/... page: the heading and menu are drawn once,
// and `children` is the page you picked in the menu.
export default function SettingsLayout({ children }: LayoutProps<"/settings">) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 pb-16">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <div className="flex flex-col gap-6 md:flex-row">
          <SettingsNav />
          <div className="min-w-0 flex-1 space-y-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
