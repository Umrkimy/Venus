import CharacterModel, { CharacterPlace } from "@/features/settings/character-model";
import CharacterMoves from "@/features/settings/character-moves";
import CharacterSwitch from "@/features/settings/character-switch";
import SettingsSection from "@/features/settings/settings-section";

export default function CharacterSettingsPage() {
  return (
    <>
      <SettingsSection title="Show Venus" description="Venus behind the chat. On or off for each device.">
        <CharacterSwitch />
      </SettingsSection>
      <SettingsSection
        title="Model"
        description="Which Venus you see, on every device. Switching keeps the others."
      >
        <CharacterModel />
      </SettingsSection>
      <SettingsSection
        title="Place"
        description="Where she stands, on every device. Switching keeps the others."
      >
        <CharacterPlace />
      </SettingsSection>
      <SettingsSection
        title="Moves"
        description="Animations she plays. Moods without one use her built-in moves."
      >
        <CharacterMoves />
      </SettingsSection>
    </>
  );
}
