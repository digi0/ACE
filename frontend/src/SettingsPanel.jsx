import { useEffect, useState } from "react";
import { User, Palette, Database, LogOut, Check, GraduationCap, Trash2, FileX } from "lucide-react";
import { apiFetch } from "./api.js";

/**
 * Settings — profile details, appearance, and data controls.
 *
 * Display name is persisted to the backend users table (PATCH /user/profile);
 * email comes from the login provider and is read-only here.
 */
export default function SettingsPanel({
  user,
  selectedMajor,
  onChangeMajor,
  darkMode,
  setDarkMode,
  chatFont,
  setChatFont,
  onClearChats,
  onRemoveDoc,
  signOut,
}) {
  const [name, setName] = useState(user?.displayName || "");
  const [nameState, setNameState] = useState("idle"); // idle | saving | saved | error
  const [cleared, setCleared] = useState(false);

  // Load the saved profile (backend display_name wins over the provider name)
  useEffect(() => {
    let cancelled = false;
    apiFetch("/user/profile")
      .then((r) => r.json())
      .then((p) => {
        if (!cancelled && p?.display_name) setName(p.display_name);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const saveName = async () => {
    if (nameState === "saving") return;
    setNameState("saving");
    try {
      const res = await apiFetch("/user/profile", {
        method: "PATCH",
        body: JSON.stringify({ display_name: name.trim() }),
      });
      if (!res.ok) throw new Error();
      setNameState("saved");
      setTimeout(() => setNameState("idle"), 1800);
    } catch {
      setNameState("error");
    }
  };

  const clearChats = () => {
    if (!window.confirm("Clear all saved conversations on this device?")) return;
    onClearChats();
    setCleared(true);
    setTimeout(() => setCleared(false), 1800);
  };

  const removeDoc = () => {
    if (!window.confirm("Remove your uploaded document? Your dashboard will reset.")) return;
    onRemoveDoc();
  };

  return (
    <div className="settings">
      <h2 className="settings-title">Settings</h2>

      {/* ── Profile ─────────────────────────────── */}
      <section className="set-card">
        <div className="set-card-head">
          <User size={16} strokeWidth={1.75} />
          <h3>Profile</h3>
        </div>

        <div className="set-row">
          <label className="set-label" htmlFor="set-name">Display name</label>
          <div className="set-inline">
            <input
              id="set-name"
              className="set-input"
              value={name}
              maxLength={120}
              placeholder="Your name"
              onChange={(e) => { setName(e.target.value); setNameState("idle"); }}
            />
            <button className="set-btn" onClick={saveName} disabled={nameState === "saving" || !name.trim()}>
              {nameState === "saving" ? "Saving…" : nameState === "saved" ? <><Check size={14} /> Saved</> : "Save"}
            </button>
          </div>
          {nameState === "error" && <p className="set-error">Couldn't save — try again.</p>}
        </div>

        <div className="set-row">
          <span className="set-label">Email</span>
          <span className="set-static">{user?.email || "—"}</span>
          <span className="set-hint">From your login provider — managed there.</span>
        </div>

        <div className="set-row">
          <span className="set-label">Major</span>
          <div className="set-inline">
            <span className="set-static set-static--grow">
              <GraduationCap size={14} strokeWidth={1.75} /> {selectedMajor || "Not selected"}
            </span>
            <button className="set-btn set-btn--ghost" onClick={onChangeMajor}>Change</button>
          </div>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────── */}
      <section className="set-card">
        <div className="set-card-head">
          <Palette size={16} strokeWidth={1.75} />
          <h3>Appearance</h3>
        </div>

        <div className="set-row">
          <span className="set-label">Theme</span>
          <div className="set-seg">
            <button className={`set-seg-btn${!darkMode ? " set-seg-btn--on" : ""}`} onClick={() => setDarkMode(false)}>Light</button>
            <button className={`set-seg-btn${darkMode ? " set-seg-btn--on" : ""}`} onClick={() => setDarkMode(true)}>Dark</button>
          </div>
        </div>

        <div className="set-row">
          <span className="set-label">Chat text size</span>
          <div className="set-seg">
            {[["sm", "Small"], ["md", "Medium"], ["lg", "Large"]].map(([v, label]) => (
              <button
                key={v}
                className={`set-seg-btn${chatFont === v ? " set-seg-btn--on" : ""}`}
                onClick={() => setChatFont(v)}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="set-hint">Applies to chat messages.</span>
        </div>
      </section>

      {/* ── Data ────────────────────────────────── */}
      <section className="set-card">
        <div className="set-card-head">
          <Database size={16} strokeWidth={1.75} />
          <h3>Data</h3>
        </div>

        <div className="set-row">
          <div className="set-inline">
            <button className="set-btn set-btn--ghost" onClick={clearChats}>
              <Trash2 size={14} /> {cleared ? "Cleared ✓" : "Clear chat history"}
            </button>
            <button className="set-btn set-btn--ghost" onClick={removeDoc}>
              <FileX size={14} /> Remove uploaded document
            </button>
          </div>
          <span className="set-hint">Chat history lives on this device; your document is removed from the server.</span>
        </div>
      </section>

      <button className="set-signout" onClick={signOut}>
        <LogOut size={15} strokeWidth={1.75} /> Sign out
      </button>

      <p className="set-foot">
        ACE is a planning tool — always confirm academic decisions with your adviser.
      </p>
    </div>
  );
}
