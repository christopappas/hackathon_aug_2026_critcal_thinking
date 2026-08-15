import type { AccessProfile } from "../types";

interface Props {
  profile: AccessProfile;
  onChange: (profile: AccessProfile) => void;
}

/**
 * The educator-facing lever from issue #6. It is deliberately set *before* the
 * session starts: accommodations are a standing fact about a student, not
 * something they should have to ask for mid-task in front of a scoring engine.
 */
export function AccessSettings({ profile, onChange }: Props) {
  return (
    <section className="access-settings">
      <h2>Educator settings</h2>
      <label className="access-toggle">
        <input
          type="checkbox"
          checked={profile.dyslexia_support}
          onChange={(event) => onChange({ ...profile, dyslexia_support: event.target.checked })}
        />
        <span>
          <strong>Dyslexia-friendly reading mode</strong>
          <small>
            Larger, wider-spaced text on a softer background, and shorter paragraphs. Scoring
            ignores spelling and message length either way.
          </small>
        </span>
      </label>
    </section>
  );
}
