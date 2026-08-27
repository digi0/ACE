import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, X, StickyNote } from "lucide-react";

/**
 * Sticky-note pinboard. The board is the dot-grid "whiteboard"; notes are
 * draggable stickies students can jot on (class notes, reminders, course
 * codes). Persisted per-user on this device (localStorage) — v1.
 */
const COLORS = ["amber", "blue", "pink", "green"];

const uid = () => `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;

export default function StickyBoard({ userId }) {
  const storageKey = `ace_notes_${userId}`;
  const boardRef = useRef(null);
  const dragRef = useRef(null); // {id, dx, dy}

  const [notes, setNotes] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Re-load when the user changes
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      setNotes(saved ? JSON.parse(saved) : []);
    } catch {
      setNotes([]);
    }
  }, [storageKey]);

  // Persist on every change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(notes));
    } catch { /* quota or private-mode failure: the board still works this session */ }
  }, [notes, storageKey]);

  const addNote = () => {
    const i = notes.length;
    setNotes((prev) => [
      ...prev,
      {
        id: uid(),
        text: "",
        color: COLORS[i % COLORS.length],
        // stagger new notes so they don't stack perfectly
        x: 40 + (i % 5) * 60,
        y: 80 + (i % 4) * 48,
        rot: ((i * 7) % 9) - 4, // -4..4 deg
      },
    ]);
  };

  const updateNote = (id, patch) =>
    setNotes((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch } : n)));

  const removeNote = (id) => setNotes((prev) => prev.filter((n) => n.id !== id));

  /* ── Dragging (pointer events; ignores drags that start in the textarea) ── */
  const onPointerDown = (e, n) => {
    if (e.target.closest("textarea, button")) return;
    const board = boardRef.current.getBoundingClientRect();
    dragRef.current = { id: n.id, dx: e.clientX - board.left - n.x, dy: e.clientY - board.top - n.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onPointerMove = useCallback((e) => {
    const d = dragRef.current;
    if (!d) return;
    const board = boardRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(board.width - 200, e.clientX - board.left - d.dx));
    const y = Math.max(0, Math.min(board.height - 120, e.clientY - board.top - d.dy));
    setNotes((prev) => prev.map((n) => (n.id === d.id ? { ...n, x, y } : n)));
  }, []);

  const endDrag = () => { dragRef.current = null; };

  return (
    <div className="board-wrap">
      <div className="board-head">
        <div>
          <h2 className="board-title"><StickyNote size={20} strokeWidth={1.75} /> Notes</h2>
          <p className="board-sub">Your pinboard — jot it down before it's gone. Drag to arrange.</p>
        </div>
        <button className="board-add" onClick={addNote}>
          <Plus size={15} strokeWidth={2.25} /> New note
        </button>
      </div>

      <div
        className="board"
        ref={boardRef}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
      >
        {notes.length === 0 && (
          <div className="board-empty">
            <p>No notes yet.</p>
            <p className="board-empty-hint">Use <strong>New note</strong> to pin your first sticky.</p>
          </div>
        )}
        {notes.map((n) => (
          <div
            key={n.id}
            className={`sticky sticky--${n.color}`}
            style={{ left: n.x, top: n.y, "--rot": `${n.rot}deg` }}
            onPointerDown={(e) => onPointerDown(e, n)}
          >
            <button className="sticky-x" onClick={() => removeNote(n.id)} aria-label="Delete note">
              <X size={12} strokeWidth={2.5} />
            </button>
            <textarea
              className="sticky-text"
              value={n.text}
              placeholder="Write something…"
              maxLength={500}
              onChange={(e) => updateNote(n.id, { text: e.target.value })}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
