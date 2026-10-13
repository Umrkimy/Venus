import EmailAccounts from "@/features/email/email-accounts";
import SettingsSection from "@/features/settings/settings-section";

export default function EmailSettingsPage() {
  return (
    <SettingsSection
      title="Email"
      description="Mailboxes Venus can read, sum up and reply from. She writes drafts; only you press Send."
    >
      <EmailAccounts />
    </SettingsSection>
  );
}
